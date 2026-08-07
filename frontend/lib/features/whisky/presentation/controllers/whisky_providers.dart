import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/api/api_client.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/config/app_config.dart';
import 'package:malt_radar/core/database/database.dart';
import '../../data/repositories/whisky_repository_impl.dart';
import '../../data/repositories/db_whisky_repository_impl.dart';
import '../../domain/models/whisky.dart';
import '../../domain/repositories/whisky_repository.dart';
import 'package:malt_radar/core/database/data_seed_service.dart';
import 'package:malt_radar/features/flavor/domain/flavor_profile_normalizer.dart';

// Provider for the local Drift database
final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(() => db.close());
  return db;
});

// Provider for the API client
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// Provider for the new DB API client
final dbWhiskyApiClientProvider = Provider<DbWhiskyApiClient>((ref) {
  return DbWhiskyApiClient();
});

// Provider for app initialization
final appInitializationProvider = FutureProvider<void>((ref) async {
  final db = ref.watch(appDatabaseProvider);
  // Backend/web mode: the catalog comes from FastAPI, so do NOT seed the local
  // Drift DB from the bundled CSV (avoids pulling catalog data from the web
  // asset bundle — part of the anti-scrape posture).
  if (!AppConfig.useDbApi) {
    await DataSeedService.seedDatabaseIfEmpty(db);
  }
});

// Provider for the repository (Feature flag switch)
final whiskyRepositoryProvider = Provider<WhiskyRepository>((ref) {
  final db = ref.watch(appDatabaseProvider);
  final client = ref.watch(apiClientProvider);
  
  if (AppConfig.useDbApi) {
    final dbClient = ref.watch(dbWhiskyApiClientProvider);
    return DbWhiskyRepositoryImpl(db, client, dbClient);
  }
  
  return WhiskyRepositoryImpl(db, client);
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
  final repository = ref.watch(whiskyRepositoryProvider);
  final query = ref.watch(searchQueryProvider);
  final favoritesOnly = ref.watch(favoritesOnlyProvider);
  final selectedFilters = ref.watch(selectedFiltersProvider);

  if (AppConfig.useDbApi) {
      // Backend-driven list. The repository fetches from FastAPI/SQLite; we
      // expose it as a stream via a Future -> Stream bridge so the UI, filters
      // and favorites toggle behave identically to local mode.
      final stream = ref
              .read(whiskyRepositoryProvider)
              .getAllWhiskies(limit: 5000, offset: 0)
              .asStream()
        .asyncMap<List<Whisky>>((list) async {
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
    });
    return stream;
  }

  return repository.watchLocalWhiskies(
    query: query,
    favoritesOnly: favoritesOnly,
    filters: selectedFilters,
  );
});

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
