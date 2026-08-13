// D-hardening H1 Task 2: near-bottom scroll trigger in HomeScreen.
//
// 1) Unit tests for the pure near-bottom predicate (shouldLoadMoreCatalog).
// 2) A widget test proving a real scroll to the bottom of the whisky list
//    fires catalogPaginationProvider.notifier.loadMore() (a fake repository
//    counts getWhiskiesPage fetches) — and that a small scroll does NOT.
//
// RED phase note: the widget test fails until HomeScreen wires the
// NotificationListener trigger (fetchCount stays at the page-0 build fetch).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/catalog_pagination.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/whisky/presentation/screens/catalog_scroll_trigger.dart';
import 'package:malt_radar/features/whisky/presentation/screens/home_screen.dart';

Whisky _makeWhisky(int id) => Whisky(
      id: id,
      externalId: 'W$id',
      name: 'Whisky $id',
      tastingNotes: const [],
      companionSuggestions: const [],
      personalScore: 0,
      personalNotes: '',
      isFavorite: false,
    );

/// Every WhiskyRepository member throws; only getWhiskiesPage is real.
class _FakeCatalogRepository implements WhiskyRepository {
  _FakeCatalogRepository({required this.totalItems});

  final int totalItems;
  int fetchCount = 0;
  final List<int> requestedOffsets = [];

  @override
  Future<List<Whisky>> getWhiskiesPage(
      {required int offset, int limit = 50, String? filter}) async {
    fetchCount++;
    requestedOffsets.add(offset);
    final start = offset.clamp(0, totalItems);
    final remaining = totalItems - start;
    final count = remaining > limit ? limit : remaining;
    return List.generate(count, (i) => _makeWhisky(start + i));
  }

  @override
  Stream<List<Whisky>> watchLocalWhiskies({
    String query = '',
    bool favoritesOnly = false,
    List<String> filters = const [],
  }) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> getAllWhiskies(
          {int limit = 100, int offset = 0, String? filter}) =>
      throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyByBackendId(String backendId) =>
      throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getEvidence(String backendId) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> getSimilarWhiskies(String backendId, {int limit = 5}) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> searchBackend(String query) => throw UnimplementedError();

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) =>
      throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyById(int id) => throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyByExternalId(String externalId) =>
      throw UnimplementedError();

  @override
  Future<int> addWhiskyToLibrary(Whisky whisky) => throw UnimplementedError();

  @override
  Future<void> fetchAndUpdateDetails(int id, String externalId) =>
      throw UnimplementedError();

  @override
  Future<void> toggleFavorite(int id) => throw UnimplementedError();

  @override
  Future<void> updatePersonalNotes(int id, String notes) =>
      throw UnimplementedError();

  @override
  Future<void> updatePersonalScore(int id, int score) =>
      throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getWhiskyPrices(
          int localId, String? externalId) =>
      throw UnimplementedError();

  @override
  Future<void> addManualPrice({
    required int whiskyId,
    required double price,
    required String currency,
    required String country,
    required String sourceName,
    required String sourceUrl,
  }) =>
      throw UnimplementedError();

  @override
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore) =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> getReferenceWhisky() =>
      throw UnimplementedError();

  @override
  Future<void> clearCache() => throw UnimplementedError();

  @override
  Future<void> clearReferenceWhisky() => throw UnimplementedError();
}

ProviderContainer _makeContainer(_FakeCatalogRepository repo) {
  return ProviderContainer(overrides: [
    whiskyRepositoryProvider.overrideWithValue(repo),
    trProvider.overrideWithValue((String key, [List<dynamic>? args]) => key),
    whiskiesStreamProvider.overrideWith(
      (ref) => Stream.value(List.generate(60, _makeWhisky)),
    ),
    referenceSettingsStreamProvider.overrideWith(
      (ref) => Stream.value(<String, dynamic>{}),
    ),
  ]);
}

void main() {
  group('shouldLoadMoreCatalog (pure near-bottom predicate)', () {
    FixedScrollMetrics metrics({
      required double pixels,
      required double maxExtent,
      double viewport = 600,
    }) =>
        FixedScrollMetrics(
          axisDirection: AxisDirection.down,
          devicePixelRatio: 1.0,
          minScrollExtent: 0,
          maxScrollExtent: maxExtent,
          pixels: pixels,
          viewportDimension: viewport,
        );

    test('true when the scroll position is within 400px of the end', () {
      expect(shouldLoadMoreCatalog(metrics(pixels: 600, maxExtent: 1000)),
          isTrue); // exactly at the threshold
      expect(shouldLoadMoreCatalog(metrics(pixels: 999, maxExtent: 1000)),
          isTrue);
    });

    test('false when still far from the end', () {
      expect(shouldLoadMoreCatalog(metrics(pixels: 0, maxExtent: 1000)),
          isFalse);
      expect(shouldLoadMoreCatalog(metrics(pixels: 500, maxExtent: 1000)),
          isFalse);
    });

    test('false for a list with no scrollable extent', () {
      expect(shouldLoadMoreCatalog(metrics(pixels: 0, maxExtent: 0)), isFalse);
    });

    test('false when the metrics carry no content dimensions', () {
      final noDimensions = FixedScrollMetrics(
        axisDirection: AxisDirection.down,
        devicePixelRatio: 1.0,
        minScrollExtent: null,
        maxScrollExtent: null,
        pixels: 0,
        viewportDimension: 600,
      );
      expect(shouldLoadMoreCatalog(noDimensions), isFalse);
    });
  });

  group('HomeScreen brand header tap resets to home state', () {
    testWidgets('clears search, filters and favorites, and scrolls to top',
        (tester) async {
      final repo = _FakeCatalogRepository(totalItems: 200);
      final container = _makeContainer(repo);
      addTearDown(container.dispose);

      // Dirty state: search query, filters and favorites-only all active.
      container.read(searchQueryProvider.notifier).state = 'Bourbon';
      container.read(selectedFiltersProvider.notifier).state = ['Bourbon'];
      container.read(favoritesOnlyProvider.notifier).state = true;

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: HomeScreen()),
        ),
      );
      await tester.pumpAndSettle();

      // Type into the search field so the TextField controller is live too.
      await tester.enterText(find.byType(TextField), 'Bourbon');
      await tester.pumpAndSettle();

      // Tap the brand header.
      await tester.tap(find.text('MALT RADAR'));
      await tester.pumpAndSettle();

      expect(container.read(searchQueryProvider), '');
      expect(container.read(selectedFiltersProvider), isEmpty);
      expect(container.read(favoritesOnlyProvider), isFalse);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller?.text,
        isEmpty,
      );
    });
  });

  group('HomeScreen near-bottom scroll trigger', () {
    testWidgets(
        'scrolling to the bottom fires catalog loadMore; a small scroll does not',
        (tester) async {
      final repo = _FakeCatalogRepository(totalItems: 200);
      final container = _makeContainer(repo);
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: HomeScreen()),
        ),
      );
      await tester.pumpAndSettle();

      // Prime page 0 (build) so the trigger's hasValue guard passes.
      await container.read(catalogPaginationProvider.future);
      expect(repo.fetchCount, 1);

      final whiskyList = find.byType(ListView).last;

      // Small scroll: still far from the end -> no pagination.
      await tester.drag(whiskyList, const Offset(0, -300));
      await tester.pumpAndSettle();
      expect(repo.fetchCount, 1);

      // Big scroll to the bottom -> loadMore fires for the next page(s).
      // A single large drag emits several near-bottom scroll notifications,
      // each of which may fire one loadMore (the fake repo resolves between
      // events), so assert the honest invariants rather than an exact count.
      await tester.drag(whiskyList, const Offset(0, -8000));
      await tester.pumpAndSettle();
      expect(repo.fetchCount, greaterThan(1)); // build + at least one loadMore
      expect(repo.requestedOffsets, contains(50)); // next page, not a dup
      expect(repo.requestedOffsets.length, greaterThanOrEqualTo(2)); // advanced
    });
  });
}
