// WP-PT-02 EventTaxonomy wiring — seam-verified slice.
//
// This test file enforces the PR-ENG-03.2 "not_fabricated" discipline:
// it does NOT assert that a fabricated call site exists. Instead it proves,
// by exercising the real widget tree, which of the 5 canonical growth events
// (custom_flavor_expand, value_moment, retention_signal, share, conversion)
// actually fire at a REAL user-action seam — and which do NOT.
//
// Seam-verification result (grep + widget-tree evidence, see task report):
//   * custom_flavor_expand — NO seam. FlavorRadarChart is static
//     (radarTouchData enabled:false), the only usage is
//     detail_screen.dart:702, and there is no tap/expand/fullscreen action.
//   * share               — NO seam. No share affordance exists anywhere in
//     lib/ (no Icons.share / share_plus / ShareSheet).
//   * value_moment        — NO seam. No emitter, no call site.
//   * retention_signal    — NO seam. No emitter, no call site.
//   * conversion          — NO seam. No emitter, no call site.
//
// G6 boundary: analytics_service.dart is NOT modified by this work. The
// fail-closed NOT_CONFIGURED path and the absence of any live GA4 provider /
// measurement ID are preserved (asserted below as a guard).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:malt_radar/core/analytics/analytics_service.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/flavor/presentation/widgets/flavor_radar_chart.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/whisky/presentation/screens/detail_screen.dart';

/// Recording spy: every typed emitter funnels through [dispatchEvent], so
/// overriding it captures the exact set of event names a widget tree fires.
/// The returned status is also recorded so the G6 boundary (no live dispatch)
/// can be asserted.
class RecordingAnalyticsService extends AnalyticsService {
  final List<String> dispatchedEvents = [];
  final List<TelemetryEventStatus> statuses = [];

  @override
  TelemetryValidationResult dispatchEvent({
    required String eventName,
    required Map<String, dynamic> payload,
    required String sessionId,
    String envId = 'malt-radar-prod-1',
  }) {
    dispatchedEvents.add(eventName);
    final result = super.dispatchEvent(
      eventName: eventName,
      payload: payload,
      sessionId: sessionId,
      envId: envId,
    );
    statuses.add(result.status);
    return result;
  }
}

/// A whisky carrying a real (axis-shaped) flavor profile so the DetailScreen
/// renders the FlavorRadarChart section — the only candidate seam for
/// custom_flavor_expand.
Whisky _whiskyWithFlavorProfile() => Whisky(
      id: 1,
      externalId: 'W-SEAM-VERIFY',
      name: 'Seam Verify Whisky',
      tastingNotes: const [],
      companionSuggestions: const [],
      personalScore: 0,
      personalNotes: '',
      isFavorite: false,
      flavorProfile:
          '{"fruity":5,"sweet":6,"spicy":3,"smoky_peaty":2,"oak_cask":4,'
          '"malty_cereal":5,"floral_herbal":3}',
    );

/// Every repository method returns a safe default. Only the calls the
/// DetailScreen actually makes with `backendId != null` are exercised:
/// getEvidence ([]), getSimilarWhiskies ([]). The rest are never reached.
class _FakeWhiskyRepository implements WhiskyRepository {
  @override
  Future<Whisky?> getWhiskyByBackendId(String backendId) async => null;

  @override
  Future<List<Map<String, dynamic>>> getEvidence(String backendId) async =>
      const [];

  @override
  Future<List<Whisky>> getSimilarWhiskies(String backendId,
          {int limit = 5}) async =>
      const [];

  @override
  Future<List<Whisky>> searchBackend(String query) async => const [];

  @override
  Future<List<Whisky>> getWhiskiesPage(
          {required int offset, int limit = 50, String? filter}) async =>
      const [];

  @override
  Stream<List<Whisky>> watchLocalWhiskies({
    String query = '',
    bool favoritesOnly = false,
    List<String> filters = const [],
  }) =>
      const Stream.empty();

  @override
  Future<List<Whisky>> getAllWhiskies(
          {int limit = 100, int offset = 0, String? filter}) async =>
      const [];

  @override
  Future<Whisky?> getWhiskyById(int id) async => null;

  @override
  Future<Whisky?> getWhiskyByExternalId(String externalId) async => null;

  @override
  Future<int> addWhiskyToLibrary(Whisky whisky) async => 0;

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) async => const [];

  @override
  Future<void> fetchAndUpdateDetails(int id, String externalId) async {}

  @override
  Future<void> addManualPrice({
    required int whiskyId,
    required double price,
    required String currency,
    required String country,
    required String sourceName,
    required String sourceUrl,
  }) async {}

  @override
  Future<List<Map<String, dynamic>>> getWhiskyPrices(
          int localId, String? externalId) async =>
      const [];

  @override
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore) async {}

  @override
  Future<Map<String, dynamic>> getReferenceWhisky() async => {};

  @override
  Future<void> updatePersonalNotes(int id, String notes) async {}

  @override
  Future<void> updatePersonalScore(int id, int score) async {}

  @override
  Future<void> toggleFavorite(int id) async {}

  @override
  Future<void> clearCache() async {}

  @override
  Future<void> clearReferenceWhisky() async {}
}

Future<void> _pumpDetailScreen(
    WidgetTester tester, RecordingAnalyticsService spy) async {
  final container = ProviderContainer(overrides: [
    whiskyRepositoryProvider.overrideWithValue(_FakeWhiskyRepository()),
    backendWhiskyDetailProvider.overrideWith((ref, id) => Stream.value(null)),
    whiskyDetailProvider
        .overrideWith((ref, id) => Stream.value(_whiskyWithFlavorProfile())),
    referenceSettingsStreamProvider
        .overrideWith((ref) => Stream.value(<String, dynamic>{})),
    referenceWhiskyModelProvider.overrideWith((ref) => Stream.value(null)),
    trProvider.overrideWithValue((String key, [List<dynamic>? args]) => key),
    analyticsServiceProvider.overrideWithValue(spy),
  ]);
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        home: DetailScreen(whiskyId: 1, backendId: 'W-SEAM-VERIFY'),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
      'control: DetailScreen mount dispatches view_item (spy observes real seams)',
      (tester) async {
    final spy = RecordingAnalyticsService();
    await _pumpDetailScreen(tester, spy);

    // The already-wired view_item fires on mount, proving the spy observes
    // real dispatch — so the negative assertions below are not vacuous.
    expect(spy.dispatchedEvents, contains('view_item'));

    // G6 boundary guard: even a wired event never reaches a live provider.
    expect(spy.statuses, isNot(contains(TelemetryEventStatus.dispatched)));
  });

  testWidgets(
      'custom_flavor_expand NOT fired: FlavorRadarChart has no tap/expand seam',
      (tester) async {
    final spy = RecordingAnalyticsService();
    await _pumpDetailScreen(tester, spy);

    // The radar renders (flavor profile present), so the candidate seam is
    // actually exercised — but it is static: no gesture, touch disabled.
    expect(find.byType(FlavorRadarChart), findsOneWidget);
    await tester.ensureVisible(find.byType(FlavorRadarChart));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FlavorRadarChart), warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(spy.dispatchedEvents, isNot(contains('custom_flavor_expand')));
  });

  testWidgets('share NOT fired: no share affordance exists in DetailScreen',
      (tester) async {
    final spy = RecordingAnalyticsService();
    await _pumpDetailScreen(tester, spy);

    // No share icon/button anywhere on the detail screen.
    expect(find.byIcon(Icons.share), findsNothing);
    expect(find.byIcon(Icons.ios_share), findsNothing);

    expect(spy.dispatchedEvents, isNot(contains('share')));
  });

  testWidgets(
      'value_moment / retention_signal / conversion NOT fired: no emitters or seams',
      (tester) async {
    final spy = RecordingAnalyticsService();
    await _pumpDetailScreen(tester, spy);

    // None of these three has a typed emitter nor a call site in lib/ — they
    // can only remain unwired. Assert the honest negative.
    expect(spy.dispatchedEvents, isNot(contains('value_moment')));
    expect(spy.dispatchedEvents, isNot(contains('retention_signal')));
    expect(spy.dispatchedEvents, isNot(contains('conversion')));
  });
}
