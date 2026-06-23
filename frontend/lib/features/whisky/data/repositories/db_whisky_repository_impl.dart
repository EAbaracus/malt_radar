import 'package:drift/drift.dart';
import 'package:malt_radar/core/api/api_client.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import '../../domain/models/whisky.dart';
import '../../domain/repositories/whisky_repository.dart';
import '../dto/db_whisky_dto.dart';

class DbWhiskyRepositoryImpl implements WhiskyRepository {
  final AppDatabase _db;
  // ignore: unused_field
  final ApiClient _apiClient;
  final DbWhiskyApiClient _dbClient;

  DbWhiskyRepositoryImpl(this._db, this._apiClient, this._dbClient);

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
      final response = await _dbClient.getWhiskies(q: query, limit: 50);
      return response.items.map((map) {
        final legacyMap = DbWhiskyMapper.toLegacyMap(map);
        return Whisky.fromMap(legacyMap);
      }).toList();
    } catch (_) {
      return [];
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
    if (whisky.externalId != null) {
      final existing = await getWhiskyByExternalId(whisky.externalId!);
      if (existing != null) {
        return existing.id;
      }
    }

    Whisky detailedWhisky = whisky;
    if (whisky.externalId != null) {
      try {
        final dbWhisky = await _dbClient.getWhiskyById(whisky.externalId!);
        if (dbWhisky != null) {
          final flavorProfile = await _dbClient.getFlavorProfile(whisky.externalId!);
          final tastingNotes = await _dbClient.getTastingNotes(whisky.externalId!);
          final legacyMap = DbWhiskyMapper.toLegacyMap(
            dbWhisky,
            flavorProfile: flavorProfile,
            tastingNotes: tastingNotes,
          );
          detailedWhisky = Whisky.fromMap(legacyMap);
        }
      } catch (_) {}
    }

    final localId = await _db.into(_db.whiskies).insert(detailedWhisky.toCompanion());

    if (whisky.externalId != null) {
      try {
        final prices = await _dbClient.getPriceHistory(whisky.externalId!);
        for (final p in prices) {
          await _db.into(_db.whiskyPrices).insert(
            WhiskyPricesCompanion.insert(
              whiskyId: localId,
              sourceName: p['source'] ?? 'Unknown',
              price: (p['price'] as num).toDouble(),
              currency: p['currency'] ?? 'USD',
              country: p['country'] ?? '',
              sourceUrl: p['url'] ?? '',
              fetchedAt: p['date'] ?? DateTime.now().toIso8601String(),
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
      final dbWhisky = await _dbClient.getWhiskyById(externalId);
      if (dbWhisky != null) {
        final flavorProfile = await _dbClient.getFlavorProfile(externalId);
        final tastingNotes = await _dbClient.getTastingNotes(externalId);
        final legacyMap = DbWhiskyMapper.toLegacyMap(
          dbWhisky,
          flavorProfile: flavorProfile,
          tastingNotes: tastingNotes,
        );
        final detailedWhisky = Whisky.fromMap(legacyMap);

        await _db.update(_db.whiskies).replace(
          detailedWhisky.copyWith(id: id).toCompanion(),
        );
      }
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
    return;
  }

  @override
  Future<void> clearReferenceWhisky() async {
    await (_db.delete(_db.userSettings)
          ..where((tbl) => tbl.key.isIn([
            'reference_whisky_id',
            'reference_whisky_absolute_score',
          ])))
        .go();
  }
}
