import '../models/whisky.dart';

abstract class WhiskyRepository {
  // Watch local cache
  Stream<List<Whisky>> watchLocalWhiskies({String query = '', bool favoritesOnly = false});
  
  // Search external backend
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
}
