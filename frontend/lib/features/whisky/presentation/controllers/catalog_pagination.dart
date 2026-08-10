import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/models/whisky.dart';
import 'whisky_providers.dart';

/// Load state of the paginated catalog, tracked separately from AsyncValue so
/// a mid-scroll 429 never wipes the already-loaded rows.
enum CatalogLoadState { initial, loadingMore, exhausted, temporarilyUnavailable }

/// Paginated catalog state (D-hardening H1 Task 1).
///
/// Builds with page 0 ([pageSize] rows) and appends subsequent pages on
/// [loadMore]. A short page (< [pageSize]) marks the list exhausted.
/// Any error during [loadMore] marks the catalog [CatalogLoadState
/// .temporarilyUnavailable] WITHOUT clearing already-loaded items and WITHOUT
/// auto-retrying (429-safe: no retry storm — only an explicit
/// [retryLoadMore] re-fires a fetch).
class CatalogPaginationNotifier extends AsyncNotifier<List<Whisky>> {
  static const int pageSize = 50;

  int _offset = 0;
  bool _hasMore = true;
  CatalogLoadState loadState = CatalogLoadState.initial;

  @override
  Future<List<Whisky>> build() async {
    // Reconnect the paginated catalog to the selected chips: watching this
    // provider makes build() re-run (fresh offset 0, fresh state) whenever
    // the user taps a filter chip, so the filtered pages replace — never
    // merge with — the previously loaded unfiltered ones.
    final selectedFilters = ref.watch(selectedFiltersProvider);
    final repo = ref.read(whiskyRepositoryProvider);
    final filter = selectedFilters.isEmpty ? null : selectedFilters.join(',');
    final page = await repo.getWhiskiesPage(offset: 0, limit: pageSize, filter: filter);
    _offset = page.length;
    _hasMore = page.length == pageSize;
    loadState =
        _hasMore ? CatalogLoadState.initial : CatalogLoadState.exhausted;
    return page;
  }

  /// Appends the next page to the existing list. No-op when the list is
  /// exhausted, a fetch is already in flight, or the catalog is marked
  /// temporarilyUnavailable after a 429/error — an explicit user action
  /// ([retryLoadMore]) is required to re-fire.
  Future<void> loadMore() async {
    if (!_hasMore ||
        loadState == CatalogLoadState.loadingMore ||
        loadState == CatalogLoadState.temporarilyUnavailable) {
      return;
    }
    loadState = CatalogLoadState.loadingMore;
    try {
      final repo = ref.read(whiskyRepositoryProvider);
      final page = await repo.getWhiskiesPage(offset: _offset, limit: pageSize);
      final current = state.value ?? const <Whisky>[];
      state = AsyncData([...current, ...page]);
      _offset += page.length;
      _hasMore = page.length == pageSize;
      loadState =
          _hasMore ? CatalogLoadState.initial : CatalogLoadState.exhausted;
    } catch (_) {
      // 429 / any error: keep the loaded rows visible, never auto-retry.
      loadState = CatalogLoadState.temporarilyUnavailable;
    }
  }

  /// Explicit user-initiated retry after a 429/error: clears the
  /// temporarilyUnavailable marker and re-fires ONE page fetch.
  Future<void> retryLoadMore() async {
    if (loadState != CatalogLoadState.temporarilyUnavailable) return;
    loadState = CatalogLoadState.initial;
    await loadMore();
  }
}

/// Paginated catalog provider: page 0 on first read, pages appended on demand.
final catalogPaginationProvider =
    AsyncNotifierProvider<CatalogPaginationNotifier, List<Whisky>>(
  CatalogPaginationNotifier.new,
);
