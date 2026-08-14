// Unit tests for the paginated catalog state (D-hardening H1 Task 1).
// CatalogPaginationNotifier: page 0 on build, loadMore appends, 429-safe
// (no retry storm, existing items are never emptied). Uses a fake repository
// — no network, no widgets.

import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/catalog_pagination.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

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

/// Serves sequential pages from a fixed catalog of [totalItems] rows.
/// Optionally throws (simulated 429) for the fetch whose [failOnOffset] is
/// hit, up to [failTimes] times.
class FakeWhiskyRepository extends _UnimplementedWhiskyRepository {
  FakeWhiskyRepository({required this.totalItems, this.failOnOffset, this.failTimes = 1});

  final int totalItems;
  final int? failOnOffset;
  int failTimes;
  int fetchCount = 0;

  @override
  Future<List<Whisky>> getWhiskiesPage({required int offset, int limit = 50, String? filter}) async {
    fetchCount++;
    if (failOnOffset != null && offset == failOnOffset && failTimes > 0) {
      failTimes--;
      throw Exception('HTTP 429 Too Many Requests');
    }
    final start = offset < 0 ? 0 : (offset > totalItems ? totalItems : offset);
    final remaining = totalItems - start;
    final count = remaining > limit ? limit : remaining;
    return List.generate(count, (i) => _makeWhisky(start + i));
  }
}

/// Each fetch is held open until [releaseNext] is called — lets tests drive
/// overlapping loadMore calls.
class _GatedWhiskyRepository extends _UnimplementedWhiskyRepository {
  int fetchCount = 0;
  Completer<void>? _pending;

  void releaseNext() => _pending?.complete();

  @override
  Future<List<Whisky>> getWhiskiesPage({required int offset, int limit = 50, String? filter}) async {
    fetchCount++;
    _pending = Completer<void>();
    await _pending!.future;
    return List.generate(limit, (i) => _makeWhisky(offset + i));
  }
}

void main() {
  group('CatalogPaginationNotifier', () {
    test('build fetches page 0 (50 items) and is ready for more', () async {
      final repo = FakeWhiskyRepository(totalItems: 120);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      final page0 = await container.read(catalogPaginationProvider.future);

      expect(repo.fetchCount, 1);
      expect(page0.length, 50);
      expect(page0.first.name, 'Whisky 0');
      expect(page0.last.name, 'Whisky 49');
      expect(notifier.loadState, CatalogLoadState.initial);

      // A full page means hasMore: the next loadMore must fetch and append.
      await notifier.loadMore();
      expect(repo.fetchCount, 2);
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 100);
    });

    test('loadMore appends page 1 (items 50-99) and advances the offset', () async {
      final repo = FakeWhiskyRepository(totalItems: 120);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      await container.read(catalogPaginationProvider.future);

      await notifier.loadMore();

      final items = container.read(catalogPaginationProvider).value!;
      expect(items.length, 100);
      expect(items[50].name, 'Whisky 50');
      expect(items[99].name, 'Whisky 99');

      // Offset advanced to 100: one more loadMore appends the final 20 rows.
      await notifier.loadMore();
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 120);
    });

    test('short page (<50) marks the list exhausted; further loadMore is a no-op', () async {
      final repo = FakeWhiskyRepository(totalItems: 75);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      await container.read(catalogPaginationProvider.future);

      await notifier.loadMore();

      final items = container.read(catalogPaginationProvider).value!;
      expect(items.length, 75);
      expect(notifier.loadState, CatalogLoadState.exhausted);

      final fetchesAfterExhaust = repo.fetchCount;
      await notifier.loadMore();
      await notifier.loadMore();
      expect(repo.fetchCount, fetchesAfterExhaust); // no further fetches
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 75);
    });

    test('429 on loadMore keeps existing items visible and marks temporarilyUnavailable', () async {
      final repo = FakeWhiskyRepository(totalItems: 120, failOnOffset: 50);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      await container.read(catalogPaginationProvider.future);

      await notifier.loadMore();

      final items = container.read(catalogPaginationProvider).value!;
      expect(items.length, 50); // still page 0 — NOT emptied
      expect(items.first.name, 'Whisky 0');
      expect(notifier.loadState, CatalogLoadState.temporarilyUnavailable);
    });

    test('after a 429, loadMore does not re-fire the fetch (no retry storm)', () async {
      final repo = FakeWhiskyRepository(totalItems: 120, failOnOffset: 50);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      await container.read(catalogPaginationProvider.future);

      await notifier.loadMore(); // fails once (fetch #2)
      expect(repo.fetchCount, 2);
      expect(notifier.loadState, CatalogLoadState.temporarilyUnavailable);

      // Repeated loadMore calls must NOT fire more fetches.
      await notifier.loadMore();
      await notifier.loadMore();
      await notifier.loadMore();
      expect(repo.fetchCount, 2); // unchanged — no retry storm
    });

    test('a failed loadMore never empties the existing list', () async {
      final repo = FakeWhiskyRepository(totalItems: 120, failOnOffset: 50);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      await container.read(catalogPaginationProvider.future);

      final before = (container.read(catalogPaginationProvider).value ?? const []).length;
      expect(before, 50);

      await notifier.loadMore(); // fails

      final after = (container.read(catalogPaginationProvider).value ?? const []).length;
      expect(after, before);
      expect(after, 50);
    });

    test('retryLoadMore clears temporarilyUnavailable and retries once on explicit call', () async {
      final repo = FakeWhiskyRepository(totalItems: 120, failOnOffset: 50, failTimes: 1);
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      await container.read(catalogPaginationProvider.future);

      await notifier.loadMore(); // fails once -> temporarilyUnavailable
      expect(notifier.loadState, CatalogLoadState.temporarilyUnavailable);
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 50);

      await notifier.retryLoadMore(); // explicit user action -> succeeds

      expect(repo.fetchCount, 3); // build + failed loadMore + explicit retry
      expect(notifier.loadState, CatalogLoadState.initial);
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 100);
    });

    test('concurrent loadMore calls fetch only once (guard)', () async {
      final repo = _GatedWhiskyRepository();
      final container = ProviderContainer(
        overrides: [whiskyRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(catalogPaginationProvider.notifier);
      final buildFuture = container.read(catalogPaginationProvider.future);
      repo.releaseNext(); // let the build fetch complete
      await buildFuture;
      expect(repo.fetchCount, 1);

      final first = notifier.loadMore();
      final second = notifier.loadMore(); // must be a no-op (loadingMore)
      repo.releaseNext(); // let the in-flight loadMore complete
      await first;
      await second;

      expect(repo.fetchCount, 2); // build + ONE loadMore — no double fetch
      expect((container.read(catalogPaginationProvider).value ?? const []).length, 100);
    });
  });
}
