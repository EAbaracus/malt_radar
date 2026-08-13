// Widget test: DetailScreen backend 404 (allowlist dışı) durumunda lokal
// Drift kaydına düşer — "Viski bulunamadı" göstermek yerine lokal kaydı basar.
//
// Regression: kullanıcının favoriler/listelerinde olup anonim katalog
// (allowlist) dışında kalan bir viski detayı ölüyordu.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/whisky/presentation/screens/detail_screen.dart';

Whisky _whisky() => Whisky(
      id: 1,
      externalId: 'W-ALLOWLIST-DISI',
      name: 'Favori Viski',
      tastingNotes: const [],
      companionSuggestions: const [],
      personalScore: 0,
      personalNotes: '',
      isFavorite: true,
    );

/// Every repository method throws; only backend detail returns null (404) so
/// the provider resolves to "not in public catalog".
class _FakeRepo implements WhiskyRepository {
  @override
  Future<Whisky?> getWhiskyByBackendId(String backendId) async => null;

  @override
  Future<List<Map<String, dynamic>>> getEvidence(String backendId) async =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> getSimilarWhiskies(String backendId,
          {int limit = 5}) async =>
      const [];

  @override
  Future<List<Whisky>> searchBackend(String query) async => const [];

  @override
  Future<List<Whisky>> getWhiskiesPage(
          {required int offset, int limit = 50, String? filter}) async =>
      const [];

  @override
  Stream<List<Whisky>> watchLocalWhiskies(
          {String query = '',
          bool favoritesOnly = false,
          List<String> filters = const []}) =>
      throw UnimplementedError();

  @override
  Future<List<Whisky>> getAllWhiskies(
          {int limit = 100, int offset = 0, String? filter}) async =>
      const [];

  @override
  Future<Whisky?> getWhiskyById(int id) => throw UnimplementedError();

  @override
  Future<Whisky?> getWhiskyByExternalId(String externalId) async => null;

  @override
  Future<int> addWhiskyToLibrary(Whisky whisky) async => 0;

  @override
  Future<List<Whisky>> searchExternalWhiskies(String query) async =>
      const [];

  @override
  Future<void> fetchAndUpdateDetails(int id, String externalId) async {}

  @override
  Future<void> addManualPrice(
          {required int whiskyId,
          required double price,
          required String currency,
          required String country,
          required String sourceName,
          required String sourceUrl}) async {}

  @override
  Future<List<Map<String, dynamic>>> getWhiskyPrices(
          int localId, String? externalId) async =>
      const [];

  @override
  Future<void> setReferenceWhisky(int whiskyId, int absoluteScore) async {}

  @override
  Future<Map<String, dynamic>> getReferenceWhisky() async => {};

  @override
  Future<void> updatePersonalNotes(int id, String notes) async {}

  @override
  Future<void> updatePersonalScore(int id, int score) async {}

  @override
  Future<void> toggleFavorite(int id) async {}

  @override
  Future<void> clearCache() async {}

  @override
  Future<void> clearReferenceWhisky() async {}
}

void main() {
  testWidgets(
      'backend 404 (allowlist dışı) → lokal kayıt fallback gösterilir',
      (tester) async {
    final whisky = _whisky();
    final container = ProviderContainer(overrides: [
      whiskyRepositoryProvider.overrideWithValue(_FakeRepo()),
      backendWhiskyDetailProvider
          .overrideWith((ref, id) => Stream.value(null)),
      whiskyDetailProvider.overrideWith((ref, id) => Stream.value(whisky)),
      referenceSettingsStreamProvider
          .overrideWith((ref) => Stream.value(<String, dynamic>{})),
      referenceWhiskyModelProvider.overrideWith((ref) => Stream.value(null)),
      trProvider.overrideWithValue((String key, [List<dynamic>? args]) => key),
    ]);
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: DetailScreen(whiskyId: 1, backendId: 'W-ALLOWLIST-DISI'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Lokal kayıt basılıyor; "bulunamadı" yok.
    expect(find.text('Favori Viski'), findsOneWidget);
    expect(find.textContaining('bulunamad'), findsNothing);
  });

  testWidgets('backend ve lokal de yoksa "bulunamadı" gösterilir',
      (tester) async {
    final container = ProviderContainer(overrides: [
      whiskyRepositoryProvider.overrideWithValue(_FakeRepo()),
      backendWhiskyDetailProvider
          .overrideWith((ref, id) => Stream.value(null)),
      whiskyDetailProvider.overrideWith((ref, id) => Stream.value(null)),
      referenceSettingsStreamProvider
          .overrideWith((ref) => Stream.value(<String, dynamic>{})),
      referenceWhiskyModelProvider.overrideWith((ref) => Stream.value(null)),
      trProvider.overrideWithValue((String key, [List<dynamic>? args]) => key),
    ]);
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: DetailScreen(whiskyId: 99, backendId: 'W-YOK'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('whisky_not_found'), findsOneWidget);
  });
}
