import '../models/whisky.dart';

abstract class WhiskyRepository {
  // Watch local cache (local Drift DB mode)
  Stream<List<Whisky>> watchLocalWhiskies({
    String query = '',
    bool favoritesOnly = false,
    List<String> filters = const [],
  });

  // --- Backend (DbApi) data path -----------------------------------------
  // Single source of
  // truth: Flutter -> DbWhiskyRepositoryImpl -> FastAPI -> SQLite. They are
  // backed by the local Drift DB only in offline/legacy/fallback mode.

  /// All whiskies from the backend (certified rows first).
  Future<List<Whisky>> getAllWhiskies({int limit = 100, int offset = 0, String? filter});

  /// ONE page of the catalog (paginated catalog mode). Returns up to [limit]
  /// rows starting at [offset]. A short page (< [limit]) signals end-of-list.
  /// Implementation lands in D-hardening Task 2.
  Future<List<Whisky>> getWhiskiesPage({required int offset, int limit = 50, String? filter});

  /// A single whisky by its backend whisky_id (e.g. 'GSD-CAND-0001' / 'W000441').
  Future<Whisky?> getWhiskyByBackendId(String backendId);

  /// official_source_references for a whisky, exactly as stored by the backend.
  Future<List<Map<String, dynamic>>> getEvidence(String backendId);

  /// Whiskies with a similar 7-axis flavor profile to the given backend whisky.
  Future<List<Whisky>> getSimilarWhiskies(String backendId, {int limit = 5});

  /// Search the backend by name/distillery (certified first, deduped).
  Future<List<Whisky>> searchBackend(String query);

  // Search external backend (legacy alias for searchBackend)
  Future<List<Whisky>> searchExternalWhiskies(String query);
  
  // Local Detail Lookups
  Future<Whisky?> getWhiskyById(int id);
  Future<Whisky?> getWhiskyByExternalId(String externalId);
  
  // Caching / Adding to library
  Future<int> addWhiskyToLibrary(Whisky whisky);
  Future<void> fetchAndUpdateDetails(int id, String externalId);
  
  // User preferences & logs
  Future<void> toggleFavorite(int id);
  Future<void> updatePersonalNotes(int id, String notes);
  Future<void> updatePersonalScore(int id, int score);
  
  // Price Listings
  Future<List<Map<String, dynamic>>> getWhiskyPrices(int localId, String? externalId);
  Future<void> addManualPrice({
    required int whiskyId,
    required double price,
    required String currency,
    required String country,
    required String sourceName,
    required String sourceUrl,
  });

  // Reference Whisky (100-Point baseline)
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore);
  Future<Map<String, dynamic>> getReferenceWhisky(); // Returns reference local ID and absolute score

  // Cache Management
  Future<void> clearCache();
  
  // Clear Reference Whisky
  Future<void> clearReferenceWhisky();
}
