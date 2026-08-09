import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/data/auth_repository.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import '../../data/repositories/db_whisky_repository_impl.dart';
import '../../domain/models/whisky.dart';
import '../../domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/flavor/domain/flavor_profile_normalizer.dart';

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

// Stream provider for the list of whiskies.
// In local mode it observes the Drift cache; in DbApi mode it is backed by the
// backend (single source of truth). Both keep the same Stream<List<Whisky>>
// contract so the UI is unchanged.
final whiskiesStreamProvider = StreamProvider<List<Whisky>>((ref) {
  // Depend on auth so the list (re)fetches once a session (and thus the
  // /api/db bearer token) is available. Without this, the first build fires
  // before login/restore sets the token -> 401 -> silently-empty catalog.
  ref.watch(authControllerProvider);
  final query = ref.watch(searchQueryProvider);
  final favoritesOnly = ref.watch(favoritesOnlyProvider);
  final selectedFilters = ref.watch(selectedFiltersProvider);

  // Backend-driven list. Build with Stream.multi so that on every (re)listen
  // (including the auth-induced rebuild) we FIRST ensure the bearer token is
  // loaded into the client, THEN fetch — closing the login/restore race where
  // an early build fires before the token is set and returns a 401 -> empty.
  final stream = Stream<List<Whisky>>.multi((controller) async {
    final repo = ref.read(whiskyRepositoryProvider);
    // Ensure the /api/db bearer token is present before the catalog fetch.
    final auth = ref.read(authControllerProvider);
    if (auth.isLoggedIn) {
      final token =
          await AuthRepository(ref.read(appDatabaseProvider)).loadToken();
      ref.read(dbWhiskyApiClientProvider).setToken(token);
    }
    final list = await repo.getAllWhiskies(limit: 5000, offset: 0);
    controller.add(_filterWhiskies(list, query, favoritesOnly, selectedFilters));
    controller.close();
  });
  return stream;
});

List<Whisky> _filterWhiskies(
  List<Whisky> list,
  String query,
  bool favoritesOnly,
  List<String> selectedFilters,
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
  if (selectedFilters.isNotEmpty) {
    filtered = filtered.where((w) {
      for (final f in selectedFilters) {
        if (!_matchesFilterStatic(w, f)) return false;
      }
      return true;
    }).toList();
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
  return repository.getAllWhiskies(limit: 5000, offset: 0);
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

// Static flavour/filter matcher shared by the DbApi list filtering and the
// local repository matcher. Mirrors DbWhiskyRepositoryImpl._matchesFilter.
bool _matchesFilterStatic(Whisky w, String filter) {
  final f = filter.toLowerCase();

  if (f == 'single malt') {
    return (w.type?.toLowerCase() == 'malt' ||
        w.category?.toLowerCase() == 'single malt' ||
        w.category?.toLowerCase() == 'scotch' && w.type?.toLowerCase() == 'malt');
  }
  if (f == 'blended') {
    return (w.type?.toLowerCase() == 'blend' ||
        w.category?.toLowerCase() == 'blended' ||
        w.category?.toLowerCase() == 'blend');
  }
  if (f == 'bourbon') {
    return (w.category?.toLowerCase() == 'bourbon' || w.type?.toLowerCase() == 'bourbon');
  }
  if (f == 'rye') {
    return (w.category?.toLowerCase() == 'rye' || w.type?.toLowerCase() == 'rye');
  }

  if (w.region != null && w.region!.toLowerCase() == f) return true;

  if (w.flavorProfile != null) {
    try {
      final profile = normalizeFlavorProfileJson(w.flavorProfile!);
      const double threshold = 1.0;
      if (f == 'peated') {
        return (profile['smoky_peaty'] ?? 0.0) > threshold || (profile['peaty'] ?? 0.0) > threshold;
      }
      if (f == 'smoky') {
        return (profile['smoky_peaty'] ?? 0.0) > threshold || (profile['smoky'] ?? 0.0) > threshold;
      }
      if (f == 'sherry' || f == 'sherry cask') {
        return (profile['sherry'] ?? 0.0) > threshold ||
            (profile['oak_cask'] ?? 0.0) > threshold ||
            (w.caskType?.toLowerCase().contains('sherry') ?? false);
      }
      if (f == 'sweet') {
        return (profile['sweet'] ?? 0.0) > threshold;
      }
      if (f == 'fruity') {
        return (profile['fruity'] ?? 0.0) > threshold;
      }
    } catch (_) {}
  } else {
    if ((f == 'sherry' || f == 'sherry cask') && (w.caskType?.toLowerCase().contains('sherry') ?? false)) {
      return true;
    }
  }
  return false;
}

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
