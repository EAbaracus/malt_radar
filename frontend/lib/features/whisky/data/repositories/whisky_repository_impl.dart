import 'package:drift/drift.dart';
import 'package:malt_radar/core/api/api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import '../../domain/models/whisky.dart';
import '../../domain/repositories/whisky_repository.dart';

class WhiskyRepositoryImpl implements WhiskyRepository {
  final AppDatabase _db;
  final ApiClient _apiClient;

  WhiskyRepositoryImpl(this._db, this._apiClient);

  @override
  Stream<List<Whisky>> watchLocalWhiskies({String query = '', bool favoritesOnly = false}) {
    final selectQuery = _db.select(_db.whiskies).join([
      leftOuterJoin(_db.userWhiskyScores, _db.userWhiskyScores.whiskyId.equalsExp(_db.whiskies.id)),
      leftOuterJoin(_db.userNotes, _db.userNotes.whiskyId.equalsExp(_db.whiskies.id)),
      leftOuterJoin(_db.favorites, _db.favorites.whiskyId.equalsExp(_db.whiskies.id)),
    ]);

    if (query.isNotEmpty) {
      selectQuery.where(_db.whiskies.name.like('%$query%'));
    }
    
    if (favoritesOnly) {
      selectQuery.where(_db.favorites.whiskyId.isNotNull());
    }

    selectQuery.orderBy([OrderingTerm.asc(_db.whiskies.name)]);

    return selectQuery.watch().map((rows) {
      return rows.map((row) {
        final whisky = row.readTable(_db.whiskies);
        final score = row.readTableOrNull(_db.userWhiskyScores)?.score;
        final notes = row.readTableOrNull(_db.userNotes)?.note;
        final favorite = row.readTableOrNull(_db.favorites) != null;
        return Whisky.fromEntities(
          whisky: whisky,
          score: score,
          notes: notes,
          favorite: favorite,
        );
      }).toList();
    });
  }

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) async {
    try {
      final results = await _apiClient.searchExternalWhiskies(query);
      return results.map((map) => Whisky.fromMap(map)).toList();
    } catch (_) {
      return []; // Return empty list on API failures
    }
  }

  @override
  Future<Whisky?> getWhiskyById(int id) async {
    final query = _db.select(_db.whiskies).join([
      leftOuterJoin(_db.userWhiskyScores, _db.userWhiskyScores.whiskyId.equalsExp(_db.whiskies.id)),
      leftOuterJoin(_db.userNotes, _db.userNotes.whiskyId.equalsExp(_db.whiskies.id)),
      leftOuterJoin(_db.favorites, _db.favorites.whiskyId.equalsExp(_db.whiskies.id)),
    ])..where(_db.whiskies.id.equals(id));

    final row = await query.getSingleOrNull();
    if (row == null) return null;

    return Whisky.fromEntities(
      whisky: row.readTable(_db.whiskies),
      score: row.readTableOrNull(_db.userWhiskyScores)?.score,
      notes: row.readTableOrNull(_db.userNotes)?.note,
      favorite: row.readTableOrNull(_db.favorites) != null,
    );
  }

  @override
  Future<Whisky?> getWhiskyByExternalId(String externalId) async {
    final query = _db.select(_db.whiskies).join([
      leftOuterJoin(_db.userWhiskyScores, _db.userWhiskyScores.whiskyId.equalsExp(_db.whiskies.id)),
      leftOuterJoin(_db.userNotes, _db.userNotes.whiskyId.equalsExp(_db.whiskies.id)),
      leftOuterJoin(_db.favorites, _db.favorites.whiskyId.equalsExp(_db.whiskies.id)),
    ])..where(_db.whiskies.externalId.equals(externalId));

    final row = await query.getSingleOrNull();
    if (row == null) return null;

    return Whisky.fromEntities(
      whisky: row.readTable(_db.whiskies),
      score: row.readTableOrNull(_db.userWhiskyScores)?.score,
      notes: row.readTableOrNull(_db.userNotes)?.note,
      favorite: row.readTableOrNull(_db.favorites) != null,
    );
  }

  @override
  Future<int> addWhiskyToLibrary(Whisky whisky) async {
    // Check if already in library
    if (whisky.externalId != null) {
      final existing = await getWhiskyByExternalId(whisky.externalId!);
      if (existing != null) {
        return existing.id;
      }
    }

    // Fetch full details (tasting notes, etc.) from the backend before inserting
    Whisky detailedWhisky = whisky;
    if (whisky.externalId != null) {
      try {
        final detailsMap = await _apiClient.getWhiskyDetails(whisky.externalId!);
        detailedWhisky = Whisky.fromMap(detailsMap);
      } catch (_) {
        // If details fetch fails, fall back to the basic info from search
      }
    }

    // Insert new entry
    final localId = await _db.into(_db.whiskies).insert(detailedWhisky.toCompanion());

    // Fetch and cache external prices
    if (whisky.externalId != null) {
      try {
        final prices = await _apiClient.getWhiskyPrices(whisky.externalId!);
        for (final p in prices) {
          await _db.into(_db.whiskyPrices).insert(
            WhiskyPricesCompanion.insert(
              whiskyId: localId,
              sourceName: p['source_name'],
              price: (p['price'] as num).toDouble(),
              currency: p['currency'],
              country: p['country'],
              sourceUrl: p['source_url'],
              fetchedAt: p['fetched_at'],
            ),
          );
        }
      } catch (_) {}
    }

    return localId;
  }

  @override
  Future<void> fetchAndUpdateDetails(int id, String externalId) async {
    try {
      final detailsMap = await _apiClient.getWhiskyDetails(externalId);
      final detailedWhisky = Whisky.fromMap(detailsMap);
      
      await _db.update(_db.whiskies).replace(
        detailedWhisky.copyWith(id: id).toCompanion(),
      );
    } catch (_) {}
  }

  @override
  Future<void> toggleFavorite(int id) async {
    final query = _db.select(_db.favorites)..where((tbl) => tbl.whiskyId.equals(id));
    final existing = await query.getSingleOrNull();

    if (existing != null) {
      await (_db.delete(_db.favorites)..where((tbl) => tbl.whiskyId.equals(id))).go();
    } else {
      await _db.into(_db.favorites).insert(
        FavoritesCompanion.insert(
          whiskyId: Value(id),
          addedAt: DateTime.now().toIso8601String(),
        ),
      );
    }
  }

  @override
  Future<void> updatePersonalNotes(int id, String notes) async {
    await _db.into(_db.userNotes).insertOnConflictUpdate(
      UserNotesCompanion.insert(
        whiskyId: Value(id),
        note: notes,
        updatedAt: DateTime.now().toIso8601String(),
      ),
    );
  }

  @override
  Future<void> updatePersonalScore(int id, int score) async {
    await _db.into(_db.userWhiskyScores).insertOnConflictUpdate(
      UserWhiskyScoresCompanion.insert(
        whiskyId: Value(id),
        score: score,
        ratedAt: DateTime.now().toIso8601String(),
      ),
    );
  }

  @override
  Future<List<Map<String, dynamic>>> getWhiskyPrices(int localId, String? externalId) async {
    final list = await (_db.select(_db.whiskyPrices)..where((tbl) => tbl.whiskyId.equals(localId))).get();
    
    // Convert to map structure
    return list.map((item) => <String, dynamic>{
      'source_name': item.sourceName,
      'price': item.price,
      'currency': item.currency,
      'country': item.country,
      'source_url': item.sourceUrl,
      'fetched_at': item.fetchedAt,
      'is_manual': item.isManual,
    }).toList();
  }

  @override
  Future<void> addManualPrice({
    required int whiskyId,
    required double price,
    required String currency,
    required String country,
    required String sourceName,
    required String sourceUrl,
  }) async {
    await _db.into(_db.whiskyPrices).insert(
      WhiskyPricesCompanion.insert(
        whiskyId: whiskyId,
        sourceName: sourceName,
        price: price,
        currency: currency,
        country: country,
        sourceUrl: sourceUrl,
        fetchedAt: DateTime.now().toIso8601String(),
        isManual: const Value(true),
      ),
    );
  }

  @override
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore) async {
    await _db.into(_db.userSettings).insertOnConflictUpdate(
      UserSettingsCompanion.insert(key: 'reference_whisky_id', value: whiskyId.toString()),
    );
    await _db.into(_db.userSettings).insertOnConflictUpdate(
      UserSettingsCompanion.insert(key: 'reference_whisky_absolute_score', value: absoluteScore.toString()),
    );
  }

  @override
  Future<Map<String, dynamic>> getReferenceWhisky() async {
    final idSetting = await (_db.select(_db.userSettings)..where((tbl) => tbl.key.equals('reference_whisky_id'))).getSingleOrNull();
    final scoreSetting = await (_db.select(_db.userSettings)..where((tbl) => tbl.key.equals('reference_whisky_absolute_score'))).getSingleOrNull();
    
    return {
      'reference_whisky_id': idSetting != null ? int.tryParse(idSetting.value) : null,
      'reference_whisky_absolute_score': scoreSetting != null ? int.tryParse(scoreSetting.value) : null,
    };
  }

  @override
  Future<void> clearCache() async {
    final favList = await _db.select(_db.favorites).get();
    final scoreList = await _db.select(_db.userWhiskyScores).get();

    final keepIds = {
      ...favList.map((f) => f.whiskyId),
      ...scoreList.map((s) => s.whiskyId),
    };

    // Delete cached whiskies not actively scored/favorited
    await (_db.delete(_db.whiskies)..where((tbl) => tbl.id.isNotIn(keepIds.toList()))).go();
    await (_db.delete(_db.whiskyPrices)..where((tbl) => tbl.whiskyId.isNotIn(keepIds.toList()))).go();
  }
}
