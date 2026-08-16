// Widget tests for the Consent Management Platform (CMP) — WP-PT-01 Phase 3.
//
// Covers the mandatory acceptance criteria:
//   (a) consent granted via the banner,
//   (b) consent denied via the banner,
//   (c) window.updateGoogleConsent invoked with the correct payload on each
//       decision (analytics_storage + ad_storage granted/denied),
//   (d) AnalyticsService reads the resulting consent state (denied blocks all
//       events except sign_up_start / sign_up_complete).
//
// G6 boundary: no live telemetry is dispatched anywhere here — the bridge is
// a recording fake and the AnalyticsService fails closed as NOT_CONFIGURED.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';

import 'package:malt_radar/core/analytics/analytics_service.dart';
import 'package:malt_radar/core/consent/consent_bridge.dart';
import 'package:malt_radar/core/consent/consent_controller.dart';
import 'package:malt_radar/core/consent/consent_state.dart';
import 'package:malt_radar/core/consent/cmp_banner.dart';
import 'package:malt_radar/core/consent/cmp_preferences_dialog.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

/// Records every `updateGoogleConsent` invocation so tests can assert the exact
/// payload handed to the Consent Mode v2 bootstrap without a browser.
class RecordingBridge implements ConsentBridge {
  final List<({bool analytics, bool marketing})> calls = [];

  @override
  bool updateGoogleConsent({
    required bool analyticsGranted,
    required bool marketingGranted,
  }) {
    calls.add((analytics: analyticsGranted, marketing: marketingGranted));
    return true;
  }
}

void main() {
  late AppDatabase db;
  late RecordingBridge bridge;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    bridge = RecordingBridge();
  });

  tearDown(() async {
    await db.close();
  });

  Future<void> pumpBanner(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appDatabaseProvider.overrideWithValue(db),
          consentBridgeProvider.overrideWithValue(bridge),
        ],
        child: const MaterialApp(
          home: Scaffold(body: CmpBanner()),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
      '(a)+(c) banner Accept all grants consent, hides the banner, and calls '
      'updateGoogleConsent(analytics:granted, ad:granted)', (tester) async {
    await pumpBanner(tester);

    expect(find.text('Accept all'), findsOneWidget);

    await tester.tap(find.text('Accept all'));
    await tester.pumpAndSettle();

    // Banner collapses once a decision is recorded.
    expect(find.text('Accept all'), findsNothing);
    expect(find.text('Reject all'), findsNothing);

    // Bridge payload: analytics + marketing both granted.
    expect(bridge.calls, hasLength(1));
    expect(bridge.calls.single, (analytics: true, marketing: true));
    expect(
      consentModePayload(analyticsGranted: true, marketingGranted: true),
      {
        'analytics_storage': 'granted',
        'ad_storage': 'granted',
        'ad_user_data': 'granted',
        'ad_personalization': 'granted',
      },
    );
  });

  testWidgets(
      '(b)+(c) banner Reject all denies consent, hides the banner, and calls '
      'updateGoogleConsent(analytics:denied, ad:denied)', (tester) async {
    await pumpBanner(tester);

    await tester.tap(find.text('Reject all'));
    await tester.pumpAndSettle();

    expect(find.text('Reject all'), findsNothing);
    expect(find.text('Accept all'), findsNothing);

    // Bridge payload: analytics + marketing both denied.
    expect(bridge.calls, hasLength(1));
    expect(bridge.calls.single, (analytics: false, marketing: false));
    expect(
      consentModePayload(analyticsGranted: false, marketingGranted: false),
      {
        'analytics_storage': 'denied',
        'ad_storage': 'denied',
        'ad_user_data': 'denied',
        'ad_personalization': 'denied',
      },
    );
  });

  test('(c) mixed decision maps analytics_storage and ad_storage independently',
      () {
    final payload = consentModePayload(
      analyticsGranted: true,
      marketingGranted: false,
    );
    expect(payload['analytics_storage'], 'granted');
    expect(payload['ad_storage'], 'denied');
    expect(payload['ad_user_data'], 'denied');
    expect(payload['ad_personalization'], 'denied');
  });

  testWidgets('preferences dialog saves a granular decision', (tester) async {
    await pumpBanner(tester);

    await tester.tap(find.text('Preferences'));
    await tester.pumpAndSettle();
    expect(find.byType(CmpPreferencesDialog), findsOneWidget);

    // Toggle analytics on (marketing stays off), then save.
    await tester.tap(find.byType(Switch).first);
    await tester.pump();
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(bridge.calls, hasLength(1));
    expect(bridge.calls.single, (analytics: true, marketing: false));
  });

  testWidgets(
      '(d) AnalyticsService reads the resulting consent state (denied blocks all events except sign_up)',
      (tester) async {
    await pumpBanner(tester);

    final container =
        ProviderScope.containerOf(tester.element(find.byType(CmpBanner)));

    // Undecided -> analytics_storage denied.
    final denied = container.read(analyticsServiceProvider);
    final blocked = denied.trackPageView(
      urlPath: '/',
      pageTitle: 'Explore',
      sessionId: 's1',
    );
    expect(blocked.status, TelemetryEventStatus.blocked);
    expect(blocked.errorCode, 'CONSENT_DENIED');

    // sign_up_start / sign_up_complete are exempt from the consent gate
    // (analytics_service.dart:128-135).
    final signUp = denied.trackSignUpStart(
      entryPoint: 'auth',
      authProvider: 'email',
      sessionId: 's1',
    );
    expect(signUp.status, isNot(TelemetryEventStatus.blocked));
    expect(signUp.errorCode, isNot('CONSENT_DENIED'));

    // Grant consent via the banner; the provider recomputes the gate.
    await tester.tap(find.text('Accept all'));
    await tester.pumpAndSettle();

    final granted = container.read(analyticsServiceProvider);
    final after = granted.trackPageView(
      urlPath: '/',
      pageTitle: 'Explore',
      sessionId: 's2',
    );
    expect(after.status, isNot(TelemetryEventStatus.blocked));
    expect(after.errorCode, isNot('CONSENT_DENIED'));
    // G6 boundary: still no live GA4 provider -> NOT_CONFIGURED.
    expect(after.status, TelemetryEventStatus.notConfigured);
  });
}
