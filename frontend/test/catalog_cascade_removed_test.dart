import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/catalog_pagination.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

/// Fake repo: pages of 50 until [failAfterPages] pages, then throws (429).
class FakePageRepo implements WhiskyRepository {
  int fetchCount = 0;
  final int failAfterPages; // throw from this page index onward
  final int totalPages;

  FakePageRepo({this.failAfterPages = 999, this.totalPages = 100});

  @override
  Future<List<Whisky>> getWhiskiesPage(
      {required int offset, int limit = 50, String? filter}) async {
    fetchCount++;
    final pageIndex = offset ~/ limit;
    if (pageIndex >= failAfterPages) {
      throw Exception('429 Too Many Requests');
    }
    if (pageIndex >= totalPages) return const [];
    return List.generate(
      limit,
      (i) => Whisky(
        id: offset + i + 1,
        name: 'Whisky ${offset + i + 1}',
        externalId: 'W${offset + i + 1}',
        tastingNotes: const [],
        companionSuggestions: const [],
        personalScore: 0,
        personalNotes: '',
        isFavorite: false,
      ),
    );
  }

  @override
  Future<List<Whisky>> getAllWhiskies(
          {int limit = 100, int offset = 0, String? filter}) async =>
      const [];

  @override
  Future<List<Whisky>> searchBackend(String query) async => const [];

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) async => const [];

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
  Future<Whisky?> getWhiskyById(int id) async => null;

  @override
  Future<Whisky?> getWhiskyByExternalId(String externalId) async => null;

  @override
  Future<int> addWhiskyToLibrary(Whisky whisky) async => 0;

  @override
  Future<void> fetchAndUpdateDetails(int id, String externalId) async {}

  @override
  Future<void> toggleFavorite(int id) async {}

  @override
  Future<void> updatePersonalNotes(int id, String notes) async {}

  @override
  Future<void> updatePersonalScore(int id, int score) async {}

  @override
  Future<List<Map<String, dynamic>>> getWhiskyPrices(
          int localId, String? externalId) async =>
      const [];

  @override
  Future<void> addManualPrice(
      {required int whiskyId,
      required double price,
      required String currency,
      required String country,
      required String sourceName,
      required String sourceUrl}) async {}

  @override
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore) async {}

  @override
  Future<Map<String, dynamic>> getReferenceWhisky() async => const {};

  @override
  Future<void> clearCache() async {}

  @override
  Future<void> clearReferenceWhisky() async {}

  @override
  Stream<List<Whisky>> watchLocalWhiskies(
          {String query = '',
          bool favoritesOnly = false,
          List<String> filters = const []}) =>
      const Stream.empty();
}

void main() {
  test('cascade removed: fail on page 2 keeps loaded items, no empty state',
      () async {
    final repo = FakePageRepo(failAfterPages: 2);
    final container = ProviderContainer(overrides: [
      whiskyRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);

    final notifier = container.read(catalogPaginationProvider.notifier);
    // build loads page 0
    final initial = await container.read(catalogPaginationProvider.future);
    expect(initial.length, 50);
    expect(notifier.loadState, CatalogLoadState.initial);

    // loadMore page 1 OK
    await notifier.loadMore();
    expect(container.read(catalogPaginationProvider).value?.length, 100);

    // page 2 throws (429) — items stay, no cascade, no empty
    await notifier.loadMore();
    final after = container.read(catalogPaginationProvider).value;
    expect(after?.length, 100, reason: 'existing items must remain visible');
    expect(notifier.loadState, CatalogLoadState.temporarilyUnavailable);

    // loadMore again = no-op (no retry storm)
    final countBefore = repo.fetchCount;
    await notifier.loadMore();
    expect(repo.fetchCount, countBefore,
        reason: 'no retry storm after 429');
  });

  test('loadMore exhausts at short page and stops fetching', () async {
    final repo = FakePageRepo(totalPages: 2); // 2 pages of 50 = 100 rows
    final container = ProviderContainer(overrides: [
      whiskyRepositoryProvider.overrideWithValue(repo),
    ]);
    addTearDown(container.dispose);

    final notifier = container.read(catalogPaginationProvider.notifier);
    await container.read(catalogPaginationProvider.future); // page 0
    await notifier.loadMore(); // page 1 (last full page)
    final before = repo.fetchCount;
    await notifier.loadMore(); // page 2 -> empty -> exhausted
    expect(repo.fetchCount, before + 1);
    expect(container.read(catalogPaginationProvider).value?.length, 100);
    expect(notifier.loadState, CatalogLoadState.exhausted);
    await notifier.loadMore(); // no-op
    expect(repo.fetchCount, before + 1, reason: 'exhausted = no more fetches');
  });
}
