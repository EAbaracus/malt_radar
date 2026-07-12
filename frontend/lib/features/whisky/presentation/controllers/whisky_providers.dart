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

// Provider for app initialization (seed data)
final appInitializationProvider = FutureProvider<void>((ref) async {
  final db = ref.watch(appDatabaseProvider);
  await DataSeedService.seedDatabaseIfEmpty(db);
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

// Stream provider for the list of whiskies
final whiskiesStreamProvider = StreamProvider<List<Whisky>>((ref) {
  final repository = ref.watch(whiskyRepositoryProvider);
  final query = ref.watch(searchQueryProvider);
  final favoritesOnly = ref.watch(favoritesOnlyProvider);
  final selectedFilters = ref.watch(selectedFiltersProvider);
  
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
