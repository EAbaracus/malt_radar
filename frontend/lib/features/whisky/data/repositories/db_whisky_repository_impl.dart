import 'package:drift/drift.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/flavor/domain/flavor_profile_normalizer.dart';
import '../../domain/models/whisky.dart';
import '../../domain/repositories/whisky_repository.dart';
import '../dto/db_whisky_dto.dart';

class DbWhiskyRepositoryImpl implements WhiskyRepository {
  final AppDatabase _db;
  final DbWhiskyApiClient _dbClient;

  DbWhiskyRepositoryImpl(this._db, this._dbClient);

  @override
  Stream<List<Whisky>> watchLocalWhiskies({
    String query = '',
    bool favoritesOnly = false,
    List<String> filters = const [],
  }) {
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
      final list = rows.map((row) {
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

      if (filters.isEmpty) return list;

      return list.where((w) {
        for (final filter in filters) {
          if (!_matchesFilter(w, filter)) return false;
        }
        return true;
      }).toList();
    });
  }

  bool _matchesFilter(Whisky w, String filter) {
    final f = filter.toLowerCase();

    // Category / Type match
    if (f == 'single malt') {
      return (w.type?.toLowerCase() == 'malt' || w.category?.toLowerCase() == 'single malt' || w.category?.toLowerCase() == 'scotch' && w.type?.toLowerCase() == 'malt');
    }
    if (f == 'blended') {
      return (w.type?.toLowerCase() == 'blend' || w.category?.toLowerCase() == 'blended' || w.category?.toLowerCase() == 'blend');
    }
    if (f == 'bourbon') {
      return (w.category?.toLowerCase() == 'bourbon' || w.type?.toLowerCase() == 'bourbon');
    }
    if (f == 'rye') {
      return (w.category?.toLowerCase() == 'rye' || w.type?.toLowerCase() == 'rye');
    }

    // Region match
    if (w.region != null && w.region!.toLowerCase() == f) {
      return true;
    }

    // Flavor character match
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
          return (profile['sherry'] ?? 0.0) > threshold || (profile['oak_cask'] ?? 0.0) > threshold || (w.caskType?.toLowerCase().contains('sherry') ?? false);
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

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) async {
    return searchBackend(query);
  }

  @override
  Future<List<Whisky>> searchBackend(String query) async {
    try {
      final maps = await _dbClient.search(query);
      return maps.map((map) => Whisky.fromMap(DbWhiskyMapper.toLegacyMap(map))).toList();
    } catch (_) {
      return [];
    }
  }

  @override
  Future<List<Whisky>> getAllWhiskies({int limit = 100, int offset = 0, String? filter}) async {
    // Bounded: a SINGLE page fetch (no eager multi-page cascade). The backend
    // clamps to CATALOG_MAX_PAGE (50) and rejects limit>100 (422); callers
    // needing more use the paginated catalog state (CatalogPaginationNotifier).
    try {
      return await getWhiskiesPage(offset: offset, limit: limit, filter: filter);
    } catch (_) {
      return [];
    }
  }

  @override
  Future<List<Whisky>> getWhiskiesPage(
      {required int offset, int limit = 50, String? filter}) async {
    final resp =
        await _dbClient.getWhiskies(limit: limit, offset: offset, filter: filter);
    return resp.items
        .map((map) => Whisky.fromMap(DbWhiskyMapper.toLegacyMap(map)))
        .toList();
  }

  @override
  Future<Whisky?> getWhiskyByBackendId(String backendId) async {
    try {
      final map = await _dbClient.getWhiskyById(backendId);
      if (map == null) return null;
      final flavorProfile = await _dbClient.getFlavorProfile(backendId);
      final tastingNotes = await _dbClient.getTastingNotes(backendId);
      final legacyMap = DbWhiskyMapper.toLegacyMap(
        map,
        flavorProfile: flavorProfile,
        tastingNotes: tastingNotes,
      );
      return Whisky.fromMap(legacyMap);
    } on DbApiAuthRequiredException {
      // 401 = "login required", NOT "whisky not found". Propagate so the UI
      // can render a sign-in state instead of a bogus not-found message.
      rethrow;
    } catch (_) {
      return null;
    }
  }

  @override
  Future<List<Map<String, dynamic>>> getEvidence(String backendId) async {
    try {
      return await _dbClient.getEvidence(backendId);
    } catch (_) {
      return [];
    }
  }

  @override
  Future<List<Whisky>> getSimilarWhiskies(String backendId, {int limit = 5}) async {
    // Öncelik: server-side full-pool endpoint (spec G1/G6). null (404: hedef
    // yok VEYA eski backend route'u yok) ve network/5xx hatası -> bounded-fetch
    // fallback (eski davranış). Yeni backend'de hedef gerçekten yoksa fallback
    // kendi içinde [] döner ("no similar flavors").
    try {
      final maps = await _dbClient.getSimilarWhiskies(backendId, limit: limit);
      if (maps == null) {
        return _boundedSimilarFallback(backendId, limit: limit);
      }
      return maps
          .map((m) {
            final legacy = DbWhiskyMapper.toLegacyMap(m);
            final sim = m['similarity'];
            if (sim is num) legacy['style_similarity'] = sim.toString();
            return Whisky.fromMap(legacy);
          })
          .toList();
    } catch (_) {
      return _boundedSimilarFallback(backendId, limit: limit);
    }
  }

  /// Eski backend uyumluluğu: 5-page (250 satır) alfabetik bounded fetch.
  /// Yeni backend'de yalnızca endpoint hatasında tetiklenir.
  Future<List<Whisky>> _boundedSimilarFallback(String backendId,
      {int limit = 5}) async {
    try {
      final target = await getWhiskyByBackendId(backendId);
      if (target?.flavorProfile == null) return [];

      Map<String, double> targetProfile;
      try {
        targetProfile = normalizeFlavorProfileJson(target!.flavorProfile!);
      } catch (_) {
        return [];
      }
      if (targetProfile.isEmpty) return [];

      final all = <Whisky>[];
      for (var p = 0; p < 5; p++) {
        final page = await getWhiskiesPage(offset: p * 50, limit: 50);
        if (page.isEmpty) break;
        all.addAll(page);
      }
      if (all.isEmpty) return [];

      final scored = <Map<String, dynamic>>[];
      for (final other in all) {
        if (other.externalId == backendId) continue;
        if (other.flavorProfile == null) continue;
        Map<String, double> otherProfile;
        try {
          otherProfile = normalizeFlavorProfileJson(other.flavorProfile!);
        } catch (_) {
          continue;
        }
        double sumSquares = 0.0;
        bool hasData = false;
        for (final entry in targetProfile.entries) {
          final v = otherProfile[entry.key] ?? 0.0;
          final diff = entry.value - v;
          sumSquares += diff * diff;
          hasData = true;
        }
        if (hasData) scored.add({'whisky': other, 'distance': sumSquares});
      }

      scored.sort(
          (a, b) => (a['distance'] as double).compareTo(b['distance'] as double));
      return scored.take(limit).map((e) => e['whisky'] as Whisky).toList();
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
