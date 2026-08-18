import 'dart:convert';
import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/consent/consent_controller.dart';

/// Provider-neutral Flutter AnalyticsService for Malt Radar.
/// Enforces closed-schema taxonomy, Consent Mode v2 gating, PII filtering,
/// environment verification, and deterministic deduplication.
/// 
/// Real GA4 network dispatches are strictly NOT AUTHORIZED / NOT CONFIGURED.

/// Builds an [AnalyticsService] whose Consent Mode v2 gate reflects the live
/// CMP decision ([consentControllerProvider]). When consent changes the
/// provider recomputes, so consumers always read the current gate state.
final analyticsServiceProvider = Provider<AnalyticsService>((ref) {
  final consent = ref.watch(consentControllerProvider);
  return AnalyticsService(
    consentState: TelemetryConsentState(
      analyticsStorage: consent.isAnalyticsGranted ? 'granted' : 'denied',
      adStorage: consent.isMarketingGranted ? 'granted' : 'denied',
      adUserData: consent.isMarketingGranted ? 'granted' : 'denied',
      adPersonalization: consent.isMarketingGranted ? 'granted' : 'denied',
    ),
  );
});

/// Anonymous session ID generated once per app lifetime.
/// Format: "session_`<timestamp>`_`<random>`". Used for deduplication and
/// anonymous funnel counting. Never persisted; rotated on fresh start.
final sessionIdProvider = Provider<String>((ref) {
  final ts = DateTime.now().millisecondsSinceEpoch;
  final rnd = Random().nextInt(99999999);
  return 'session_${ts}_$rnd';
});

enum TelemetryEventStatus { dispatched, blocked, failed, hold, deduplicated, notConfigured }

class TelemetryValidationResult {
  final bool valid;
  final TelemetryEventStatus status;
  final String? errorCode;
  final String? message;
  final String? eventId;

  const TelemetryValidationResult({
    required this.valid,
    required this.status,
    this.errorCode,
    this.message,
    this.eventId,
  });
}

class TelemetryConsentState {
  final String analyticsStorage; // 'granted' | 'denied'
  final String adStorage;
  final String adUserData;
  final String adPersonalization;

  const TelemetryConsentState({
    this.analyticsStorage = 'denied',
    this.adStorage = 'denied',
    this.adUserData = 'denied',
    this.adPersonalization = 'denied',
  });

  bool get isAnalyticsGranted => analyticsStorage == 'granted';
}

class AnalyticsService {
  final String allowedEnvironmentId;
  final TelemetryConsentState _consentState;
  final Set<String> _seenEventIds = {};

  AnalyticsService({
    this.allowedEnvironmentId = 'malt-radar-prod-1',
    TelemetryConsentState consentState = const TelemetryConsentState(analyticsStorage: 'denied'),
  }) : _consentState = consentState;

  static const Set<String> _canonicalEvents = {
    'page_view',
    'search',
    'view_item',
    'custom_flavor_expand',
    'value_moment',
    'sign_up_start',
    'sign_up_complete',
    'retention_signal',
    'share',
    'conversion',
  };

  static const Set<String> _forbiddenPiiKeys = {
    'email',
    'password',
    'name',
    'full_name',
    'phone',
    'ip',
    'raw_ip',
    'secret',
    'token',
    'access_token',
    'oauth_token',
    'session_secret',
  };

  /// Recursively scan dictionary/map payload for prohibited PII keys
  bool _containsPiiKeys(dynamic data) {
    if (data is Map) {
      for (var entry in data.entries) {
        if (entry.key is String) {
          final keyLower = (entry.key as String).toLowerCase();
          if (_forbiddenPiiKeys.contains(keyLower)) {
            return true;
          }
        }
        if (_containsPiiKeys(entry.value)) {
          return true;
        }
      }
    } else if (data is List) {
      for (var item in data) {
        if (_containsPiiKeys(item)) {
          return true;
        }
      }
    }
    return false;
  }

  TelemetryValidationResult dispatchEvent({
    required String eventName,
    required Map<String, dynamic> payload,
    required String sessionId,
    String envId = 'malt-radar-prod-1',
  }) {
    // 1. Consent Gate Check (all events require consent)
    if (!_consentState.isAnalyticsGranted) {
      return const TelemetryValidationResult(
        valid: false,
        status: TelemetryEventStatus.blocked,
        errorCode: 'CONSENT_DENIED',
        message: 'Dispatch blocked: analytics_storage consent is denied',
      );
    }

    // 2. Canonical Taxonomy Check
    if (!_canonicalEvents.contains(eventName)) {
      return TelemetryValidationResult(
        valid: false,
        status: TelemetryEventStatus.blocked,
        errorCode: 'UNKNOWN_EVENT',
        message: 'Event $eventName is not in canonical 10-event taxonomy',
      );
    }

    // 3. Recursive PII Filter Scan
    if (_containsPiiKeys(payload)) {
      return const TelemetryValidationResult(
        valid: false,
        status: TelemetryEventStatus.blocked,
        errorCode: 'PII_PROHIBITED',
        message: 'Payload contains prohibited PII or credential keys',
      );
    }

    // 4. Environment Verification Check
    if (envId != allowedEnvironmentId) {
      return TelemetryValidationResult(
        valid: false,
        status: TelemetryEventStatus.blocked,
        errorCode: 'ENVIRONMENT_MISMATCH',
        message: 'Environment $envId does not match $allowedEnvironmentId',
      );
    }

    // 5. Deduplication Key Check
    final dedupeKey = '$eventName:$sessionId:${jsonEncode(payload)}';
    if (_seenEventIds.contains(dedupeKey)) {
      return TelemetryValidationResult(
        valid: true,
        status: TelemetryEventStatus.deduplicated,
        errorCode: 'DEDUPLICATED',
        message: 'Event deduplicated locally',
        eventId: dedupeKey,
      );
    }
    _seenEventIds.add(dedupeKey);

    // 6. No live GA4 provider connected -> fail-closed as NOT_CONFIGURED
    return TelemetryValidationResult(
      valid: false,
      status: TelemetryEventStatus.notConfigured,
      errorCode: 'NOT_CONFIGURED',
      message: 'No live authorized GA4 provider is attached (GA4 = NOT AUTHORIZED)',
      eventId: dedupeKey,
    );
  }

  // Typed Emitters
  TelemetryValidationResult trackPageView({required String urlPath, required String pageTitle, required String sessionId}) {
    return dispatchEvent(
      eventName: 'page_view',
      payload: {'url_path': urlPath, 'page_title': pageTitle},
      sessionId: sessionId,
    );
  }

  TelemetryValidationResult trackSearch({required String queryText, required int resultsCount, required String sessionId}) {
    return dispatchEvent(
      eventName: 'search',
      payload: {'query_text': queryText, 'results_count': resultsCount},
      sessionId: sessionId,
    );
  }

  TelemetryValidationResult trackViewItem({required String whiskyId, required String whiskyName, required String sessionId}) {
    return dispatchEvent(
      eventName: 'view_item',
      payload: {'whisky_id': whiskyId, 'whisky_name': whiskyName},
      sessionId: sessionId,
    );
  }

  TelemetryValidationResult trackCustomFlavorExpand({required String whiskyId, required String axisName, required String sessionId}) {
    return dispatchEvent(
      eventName: 'custom_flavor_expand',
      payload: {'whisky_id': whiskyId, 'axis_name': axisName, 'interaction_type': 'axis_tap'},
      sessionId: sessionId,
    );
  }

  TelemetryValidationResult trackSignUpStart({required String entryPoint, required String authProvider, required String sessionId}) {
    return dispatchEvent(
      eventName: 'sign_up_start',
      payload: {'entry_point': entryPoint, 'auth_provider': authProvider},
      sessionId: sessionId,
    );
  }

  TelemetryValidationResult trackSignUpComplete({
    required String userId,
    required String authProvider,
    required String sessionId,
    String? referralSource,
  }) {
    return dispatchEvent(
      eventName: 'sign_up_complete',
      payload: {
        'user_id': userId,
        'auth_provider': authProvider,
        'age_verified': true,
        'referral_source': referralSource ?? 'none',
      },
      sessionId: sessionId,
    );
  }

  TelemetryValidationResult trackShare({required String whiskyId, required String shareChannel, required String anonRefId, required String sessionId}) {
    return dispatchEvent(
      eventName: 'share',
      payload: {'whisky_id': whiskyId, 'share_channel': shareChannel, 'anon_ref_id': anonRefId},
      sessionId: sessionId,
    );
  }
}
