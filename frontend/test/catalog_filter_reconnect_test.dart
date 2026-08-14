// Regression: catalog pagination must be re-connected to selected filters.
//
// 24ad7eb introduced server-side filtering (selectedFilters -> getAllWhiskies
// filter: -> backend SQL). H1 (88a4596/ce20e03) rewired the catalog to
// CatalogPaginationNotifier but DROPPED the watch on selectedFiltersProvider —
// chips updated state that nobody consumed, so getWhiskiesPage was always
// called filter-less. This test pins the contract:
//
//   selectedFilters change
//     -> pagination provider rebuilds (build() re-runs)
//     -> getWhiskiesPage(filter: selectedFilters.join(',')) called with offset 0
//     -> previously loaded pages never leak into the new filtered state

import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/catalog_pagination.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

Whisky _makeWhisky(int id, [String prefix = 'Whisky']) =>
    Whisky(
      id: id,
      externalId: '$prefix$id',
      name: '$prefix $id',
      tastingNotes: const [],
      companionSuggestions: const [],
      personalScore: 0,
      personalNotes: '',
      isFavorite: false,
    );

/// Every WhiskyRepository member throws; concrete fakes override only the
/// members under test.
class _UnimplementedWhiskyRepository implements WhiskyRepository {
  @override
  Stream<List<Whisky>> watchLocalWhiskies({
    String query = '',
    bool favoritesOnly = false,
    List<String> filters = const [],
  }) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> getAllWhiskies({int limit = 100, int offset = 0, String? filter}) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> getWhiskiesPage({required int offset, int limit = 50, String? filter}) =>
      throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyByBackendId(String backendId) => throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getEvidence(String backendId) => throw UnimplementedError();

  @override
  Future<List<Whisky>> getSimilarWhiskies(String backendId, {int limit = 5}) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> searchBackend(String query) => throw UnimplementedError();

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) => throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyById(int id) => throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyByExternalId(String externalId) => throw UnimplementedError();

  @override
  Future<int> addWhiskyToLibrary(Whisky whisky) => throw UnimplementedError();

  @override
  Future<void> fetchAndUpdateDetails(int id, String externalId) => throw UnimplementedError();

  @override
  Future<void> toggleFavorite(int id) => throw UnimplementedError();

  @override
  Future<void> updatePersonalNotes(int id, String notes) => throw UnimplementedError();

  @override
  Future<void> updatePersonalScore(int id, int score) => throw UnimplementedError();

  @override
  Future<List<Map<String, dynamic>>> getWhiskyPrices(int localId, String? externalId) =>
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
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore) => throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> getReferenceWhisky() => throw UnimplementedError();

  @override
  Future<void> clearCache() => throw UnimplementedError();

  @override
  Future<void> clearReferenceWhisky() => throw UnimplementedError();
}

/// Filter-aware fake: records the filter each page was fetched with and
/// names rows by filter so leaking pages are detectable. "peated" rows are
/// named 'Peated N', "sherry" rows 'Sherry N', no filter 'Whisky N'.
class FilterAwareFakeRepo extends _UnimplementedWhiskyRepository {
  final List<String?> filterCalls = [];
  final List<int> offsetCalls = [];
  int totalItems;

  FilterAwareFakeRepo({this.totalItems = 120});

  String get _prefix {
    if (filterCalls.isEmpty || filterCalls.last == null) return 'Whisky';
    final f = filterCalls.last!.toLowerCase();
    if (f.contains('peated')) return 'Peated';
    if (f.contains('sherry')) return 'Sherry';
    return 'Whisky';
  }

  @override
  Future<List<Whisky>> getWhiskiesPage({required int offset, int limit = 50, String? filter}) async {
    filterCalls.add(filter);
    offsetCalls.add(offset);
    final start = offset < 0 ? 0 : (offset > totalItems ? totalItems : offset);
    final remaining = totalItems - start;
    final count = remaining > limit ? limit : remaining;
    return List.generate(count, (i) => _makeWhisky(start + i, _prefix));
  }
}

void main() {
  group('catalog filter reconnect', () {
    test('build reads selected filters and passes them to getWhiskiesPage', () async {
      final repo = FilterAwareFakeRepo();
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      // Start with a filter selected BEFORE the first build.
      container.read(selectedFiltersProvider.notifier).state = ['Peated'];
      final page0 = await container.read(catalogPaginationProvider.future);

      expect(repo.filterCalls, isNotEmpty);
      // The page must have been fetched WITH the joined filter.
      expect(repo.filterCalls.first, 'Peated');
      // Rows are the filtered (Peated) world, not the unfiltered one.
      expect(page0.first.name, 'Peated 0');
    });

    test('changing filters rebuilds the provider and resets to offset 0', () async {
      final repo = FilterAwareFakeRepo();
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      // No filter -> build -> unfiltered page 0.
      await container.read(catalogPaginationProvider.future);
      expect(repo.filterCalls.first, isNull);
      expect(repo.offsetCalls.first, 0);

      // Load a second page so there is accumulated state to leak from.
      await container.read(catalogPaginationProvider.notifier).loadMore();
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 100);

      // User taps a chip: filter changes.
      container.read(selectedFiltersProvider.notifier).state = ['Sherry'];
      // Wait for the provider to rebuild with the new dependency.
      final filtered = await container.read(catalogPaginationProvider.future);

      // The rebuild must have fetched with the NEW filter at offset 0.
      expect(repo.filterCalls.last, 'Sherry');
      expect(repo.offsetCalls.last, 0);

      // The new state is the filtered page 0 ONLY — old unfiltered pages
      // (Whisky 0..99) must not leak into it.
      expect(filtered.length, 50, reason: 'rebuild must start fresh at page 0');
      expect(filtered.first.name, 'Sherry 0');
      expect(filtered.where((w) => w.name.startsWith('Whisky')), isEmpty,
          reason: 'no unfiltered rows may leak into the filtered state');
    });

    test('multiple chips join with comma before the fetch', () async {
      final repo = FilterAwareFakeRepo();
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      container.read(selectedFiltersProvider.notifier).state = ['Peated', 'Sherry'];
      await container.read(catalogPaginationProvider.future);

      expect(repo.filterCalls.first, 'Peated,Sherry');
    });
  });
}
