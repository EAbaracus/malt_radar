// Unit tests: DbWhiskyRepositoryImpl.getWhiskyByBackendId must NOT swallow
// auth-required (401) failures into null. Today `catch (_) { return null; }`
// erases the 401, so the detail screen cannot tell "login required" from
// "whisky not found". 404 (client returns null) must still resolve to null.

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/data/repositories/db_whisky_repository_impl.dart';

class _FakeDbClient extends DbWhiskyApiClient {
  final Map<String, dynamic>? whiskyByIdResult;
  final Object? whiskyByIdError;
  final Object? tastingNotesError;

  _FakeDbClient({
    this.whiskyByIdResult,
    this.whiskyByIdError,
    this.tastingNotesError,
  });

  @override
  Future<Map<String, dynamic>?> getWhiskyById(String id) async {
    if (whiskyByIdError != null) throw whiskyByIdError!;
    return whiskyByIdResult;
  }

  @override
  Future<Map<String, dynamic>?> getFlavorProfile(String whiskyId) async => null;

  @override
  Future<List<Map<String, dynamic>>> getTastingNotes(String whiskyId) async {
    if (tastingNotesError != null) throw tastingNotesError!;
    return [];
  }
}

void main() {
  DbWhiskyRepositoryImpl buildRepo(_FakeDbClient client) {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(db.close);
    return DbWhiskyRepositoryImpl(db, client);
  }

  test('getWhiskyById 401 → DbApiAuthRequiredException propagates (not null)',
      () async {
    final repo = buildRepo(
      _FakeDbClient(whiskyByIdError: DbApiAuthRequiredException('getWhiskyById')),
    );

    expect(
      () => repo.getWhiskyByBackendId('W-1'),
      throwsA(isA<DbApiAuthRequiredException>()),
    );
  });

  test('404 (client null) → returns null', () async {
    final repo = buildRepo(_FakeDbClient(whiskyByIdResult: null));

    expect(await repo.getWhiskyByBackendId('W-YOK'), isNull);
  });

  test('tasting-notes 401 after whisky 200 → propagates (guest bug path)',
      () async {
    final repo = buildRepo(
      _FakeDbClient(
        whiskyByIdResult: {'id': 1, 'whisky_id': 'W-1'},
        tastingNotesError: DbApiAuthRequiredException('getTastingNotes'),
      ),
    );

    expect(
      () => repo.getWhiskyByBackendId('W-1'),
      throwsA(isA<DbApiAuthRequiredException>()),
    );
  });
}
