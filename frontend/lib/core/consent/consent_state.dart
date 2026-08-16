import 'package:flutter/foundation.dart';

/// Per-category Consent Mode v2 decision tracked by the CMP.
///
/// `undecided` is the pre-choice state (the JS bootstrap defaults everything to
/// `denied` until the user explicitly picks). `granted` / `denied` are the
/// recorded user choices.
enum ConsentChoice { undecided, granted, denied }

/// The CMP's consent decision, broken into the two Consent Mode v2 buckets the
/// bootstrap exposes:
///   * [analytics]  → `analytics_storage`
///   * [marketing]  → `ad_storage` + `ad_user_data` + `ad_personalization`
@immutable
class ConsentState {
  final ConsentChoice analytics;
  final ConsentChoice marketing;

  const ConsentState({
    this.analytics = ConsentChoice.undecided,
    this.marketing = ConsentChoice.undecided,
  });

  /// True once the user has made an explicit choice on both buckets.
  bool get hasDecided =>
      analytics != ConsentChoice.undecided &&
      marketing != ConsentChoice.undecided;

  bool get isAnalyticsGranted => analytics == ConsentChoice.granted;
  bool get isMarketingGranted => marketing == ConsentChoice.granted;

  static const ConsentState undecided = ConsentState();

  /// Stable key-value encoding persisted in `UserSettings` under `'consent'`.
  String encode() => '${analytics.name}|${marketing.name}';

  /// Rehydrates a persisted value, falling back to [undecided] on any malformed
  /// or missing input (fail-closed: never assume consent was granted).
  static ConsentState decode(String? value) {
    if (value == null) return undecided;
    final parts = value.split('|');
    if (parts.length != 2) return undecided;
    return ConsentState(
      analytics: _parseChoice(parts[0]),
      marketing: _parseChoice(parts[1]),
    );
  }

  static ConsentChoice _parseChoice(String name) {
    for (final c in ConsentChoice.values) {
      if (c.name == name) return c;
    }
    return ConsentChoice.undecided;
  }
}

/// The exact Consent Mode v2 payload the CMP hands to `window.updateGoogleConsent`.
///
/// `analytics_storage` is driven by the analytics choice; `ad_storage`,
/// `ad_user_data` and `ad_personalization` are all driven by the marketing
/// (ads) choice. Kept as a pure function so tests can assert the payload shape
/// without a browser.
Map<String, String> consentModePayload({
  required bool analyticsGranted,
  required bool marketingGranted,
}) {
  String v(bool granted) => granted ? 'granted' : 'denied';
  return {
    'analytics_storage': v(analyticsGranted),
    'ad_storage': v(marketingGranted),
    'ad_user_data': v(marketingGranted),
    'ad_personalization': v(marketingGranted),
  };
}
