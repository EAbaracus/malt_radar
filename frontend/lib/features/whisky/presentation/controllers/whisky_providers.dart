import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/data/auth_repository.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import '../../data/repositories/db_whisky_repository_impl.dart';
import '../../domain/models/whisky.dart';
import '../../domain/repositories/whisky_repository.dart';
import 'catalog_pagination.dart';

// Provider for the local Drift database
final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(() => db.close());
  return db;
});

// Provider for the backend (/api/db) API client. The bearer token is synced
// from the auth session so gated /api/db reads succeed (anti-scrape).
// The token is restored on login/start and cleared on logout (keeps the shared
// client ready for catalog reads whenever a session exists).
final dbWhiskyApiClientProvider = Provider<DbWhiskyApiClient>((ref) {
  final client = DbWhiskyApiClient();
  // Lazy token source: any request that finds no in-memory token loads it from
  // the persisted session first. This removes the login/restore race where an
  // early catalog fetch would 401 (=> empty list / empty search).
  final db = ref.read(appDatabaseProvider);
  final authRepo = AuthRepository(db);
  client.setTokenLoader(() => authRepo.loadToken());
  // Keep the in-memory token in sync with the auth session too.
  ref.listen(authControllerProvider, (prev, next) {
    if (next.user != null && next.status == AuthStatus.loggedIn) {
      authRepo.loadToken().then(client.setToken);
    } else if (next.status == AuthStatus.loggedOut) {
      client.setToken(null);
    }
  });
  return client;
});

// Provider for app initialization. Opens the local DB, then loads any stored
// auth token into the /api/db client so gated reads succeed (anti-scrape:
// no catalog data ships to the client; the backend is the single source).
final appInitializationProvider = FutureProvider<void>((ref) async {
  ref.watch(appDatabaseProvider);
  // Restore the bearer token for the /api/db client (login persists token in
  // local UserSettings). AuthController also restores it; wire here too so the
  // client is ready before any UI triggers catalog reads.
  final repo = AuthRepository(ref.read(appDatabaseProvider));
  final token = await repo.loadToken();
  ref.read(dbWhiskyApiClientProvider).setToken(token);
});

// Provider for the repository — backend (/api/db) is the single source of
// truth. Legacy local CSV repository removed with /api/whiskies/* closure.
final whiskyRepositoryProvider = Provider<WhiskyRepository>((ref) {
  final db = ref.watch(appDatabaseProvider);
  final dbClient = ref.watch(dbWhiskyApiClientProvider);
  return DbWhiskyRepositoryImpl(db, dbClient);
});

// State provider for the search query
final searchQueryProvider = StateProvider<String>((ref) => '');

// State provider for filtering favorites only
final favoritesOnlyProvider = StateProvider<bool>((ref) => false);

// State provider for selected search filters/chips
final selectedFiltersProvider = StateProvider<List<String>>((ref) => []);

// Stream provider for the filtered list of whiskies.
// Consumes the PAGINATED catalog state (CatalogPaginationNotifier) — pages
// loaded so far, not the whole catalog. Query text and favorites are applied
// CLIENT-SIDE on the loaded pages; server-side chips filter at fetch time.
final whiskiesStreamProvider = StreamProvider<List<Whisky>>((ref) {
  // Watch the paginated catalog so the stream rebuilds when pages load.
  ref.watch(catalogPaginationProvider);
  final query = ref.watch(searchQueryProvider);
  final favoritesOnly = ref.watch(favoritesOnlyProvider);

  // Watch local favorites table to overlay isFavorite onto catalog items
  final db = ref.watch(appDatabaseProvider);
  final favoritesStream = db.select(db.favorites).watch();

  return favoritesStream.asyncMap((favoritesRows) async {
    // Build a set of local whisky IDs that are favorited
    final favoriteWhiskyIds = favoritesRows.map((f) => f.whiskyId).toSet();

    // Get the current catalog list
    final list = await ref.read(catalogPaginationProvider.future);

    // Overlay isFavorite onto each Whisky object based on local favorites table
    final listWithFavorites = list.map((w) {
      final isFav = favoriteWhiskyIds.contains(w.id);
      return isFav ? w.copyWith(isFavorite: true) : w;
    }).toList();

    return _filterWhiskies(listWithFavorites, query, favoritesOnly);
  });
});

List<Whisky> _filterWhiskies(
  List<Whisky> list,
  String query,
  bool favoritesOnly,
) {
  var filtered = list;
  if (query.isNotEmpty) {
    final q = query.toLowerCase();
    filtered = filtered
        .where((w) => (w.name).toLowerCase().contains(q))
        .toList();
  }

  final seen = <String>{};
  final unique = <Whisky>[];
  for (final w in filtered) {
    final name = w.name.trim().toLowerCase();
    if (!seen.contains(name)) {
      seen.add(name);
      unique.add(w);
    }
  }
  filtered = unique;

  if (favoritesOnly) {
    filtered = filtered.where((w) => w.isFavorite).toList();
  }
  return filtered;
}

// Stream provider for a single whisky (for detail screen real-time updates)
final whiskyDetailProvider = StreamProvider.family<Whisky?, int>((ref, id) {
  final db = ref.watch(appDatabaseProvider);
  return db.select(db.whiskies).join([
    leftOuterJoin(db.userWhiskyScores, db.userWhiskyScores.whiskyId.equalsExp(db.whiskies.id)),
    leftOuterJoin(db.userNotes, db.userNotes.whiskyId.equalsExp(db.whiskies.id)),
    leftOuterJoin(db.favorites, db.favorites.whiskyId.equalsExp(db.whiskies.id)),
  ]).watch().map((rows) {
    final matching = rows.where((row) => row.readTable(db.whiskies).id == id);
    if (matching.isEmpty) return null;
    final row = matching.first;
    return Whisky.fromEntities(
      whisky: row.readTable(db.whiskies),
      score: row.readTableOrNull(db.userWhiskyScores)?.score,
      notes: row.readTableOrNull(db.userNotes)?.note,
      favorite: row.readTableOrNull(db.favorites) != null,
    );
  });
});

// ---------------------------------------------------------------------------
// DbApi-mode providers (backend = single source of truth).
// These mirror the local providers but key on the backend whisky_id and read
// through the repository, which talks to FastAPI -> SQLite. No Drift sync, no
// cache duplication.
// ---------------------------------------------------------------------------

// All whiskies from the backend (certified rows first).
final backendWhiskiesProvider = FutureProvider<List<Whisky>>((ref) async {
  final repository = ref.watch(whiskyRepositoryProvider);
  return repository.getAllWhiskies(limit: 50, offset: 0);
});

// A single whisky by its backend whisky_id (used by the detail screen in DbApi
// mode). Keys on whisky_id, not the local integer id.
final backendWhiskyDetailProvider =
    StreamProvider.family<Whisky?, String>((ref, whiskyId) async* {
  final repository = ref.watch(whiskyRepositoryProvider);
  yield await repository.getWhiskyByBackendId(whiskyId);
});

// Similar whiskies by flavor profile (backend-driven).
final backendSimilarWhiskiesProvider =
    FutureProvider.family<List<Whisky>, String>((ref, whiskyId) async {
  final repository = ref.watch(whiskyRepositoryProvider);
  return repository.getSimilarWhiskies(whiskyId, limit: 5);
});

// Stream provider for reference settings (100pt whisky configuration)
final referenceSettingsStreamProvider = StreamProvider<Map<String, dynamic>>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return (db.select(db.userSettings)..where((tbl) => tbl.key.like('reference_whisky%')))
      .watch()
      .map((rows) {
    final map = <String, dynamic>{};
    for (final row in rows) {
      if (row.key == 'reference_whisky_id') {
        map['reference_whisky_id'] = int.tryParse(row.value);
      } else if (row.key == 'reference_whisky_absolute_score') {
        map['reference_whisky_absolute_score'] = int.tryParse(row.value);
      }
    }
    return map;
  });
});

// Stream provider for the Reference Whisky object itself
final referenceWhiskyModelProvider = StreamProvider<Whisky?>((ref) {
  final settingsAsync = ref.watch(referenceSettingsStreamProvider);
  return settingsAsync.when(
    data: (settings) {
      final id = settings['reference_whisky_id'] as int?;
      if (id == null) return Stream.value(null);
      final db = ref.watch(appDatabaseProvider);
      return (db.select(db.whiskies)..where((tbl) => tbl.id.equals(id)))
          .watchSingleOrNull()
          .map((entity) => entity != null ? Whisky.fromEntities(whisky: entity) : null);
    },
    loading: () => Stream.value(null),
    error: (error, stackTrace) => Stream.value(null),
  );
});
