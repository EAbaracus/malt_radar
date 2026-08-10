// D-hardening H1 Task 2: DbWhiskyRepositoryImpl.getWhiskiesPage fetches ONE
// page from the backend (/api/db/whiskies) with limit/offset/filter query
// params and maps the raw rows to domain Whisky objects. Uses a MockClient
// (package:http/testing) — no network, no real backend.
//
// RED phase note: this test fails until getWhiskiesPage is implemented
// (it currently throws UnimplementedError).

import 'dart:convert';

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/data/repositories/db_whisky_repository_impl.dart';

void main() {
  test('getWhiskiesPage fetches limit/offset URL and maps rows to Whisky',
      () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(db.close);

    Uri? captured;
    final mock = MockClient((request) async {
      captured = request.url;
      return http.Response(
        jsonEncode({
          'items': [
            {
              'whisky_id': 'W000001',
              'name': 'Test Dram One',
              'country': 'Scotland',
              'category': 'Single Malt',
            },
            {
              'whisky_id': 'W000002',
              'name': 'Test Dram Two',
              'country': 'Scotland',
              'category': 'Single Malt',
            },
          ],
          'total_count': 2,
          'limit': 50,
          'offset': 100,
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final repo = DbWhiskyRepositoryImpl(db, DbWhiskyApiClient(client: mock));
    final page = await repo.getWhiskiesPage(offset: 100, limit: 50);

    // The request URL must carry the requested page window.
    expect(captured, isNotNull);
    expect(captured!.path, '/api/db/whiskies');
    expect(captured!.queryParameters['limit'], '50');
    expect(captured!.queryParameters['offset'], '100');

    // The raw backend rows must be mapped to domain Whisky objects.
    expect(page.length, 2);
    expect(page.first.externalId, 'W000001');
    expect(page.first.name, 'Test Dram One');
    expect(page.last.externalId, 'W000002');
  });

  test('getWhiskiesPage passes a filter through to the request URL', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(db.close);

    Uri? captured;
    final mock = MockClient((request) async {
      captured = request.url;
      return http.Response(
        jsonEncode({
          'items': <Object>[],
          'total_count': 0,
          'limit': 25,
          'offset': 0,
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final repo = DbWhiskyRepositoryImpl(db, DbWhiskyApiClient(client: mock));
    await repo.getWhiskiesPage(offset: 0, limit: 25, filter: 'peated');

    expect(captured, isNotNull);
    expect(captured!.queryParameters['limit'], '25');
    expect(captured!.queryParameters['offset'], '0');
    expect(captured!.queryParameters['filter'], 'peated');
  });
}
