// Unit tests: DbWhiskyApiClient auth-gated (401) detail-chain failures must
// surface as DbApiAuthRequiredException — NOT as a generic Exception and NOT
// as null. The detail screen needs to tell "login required" apart from
// "whisky not found" (404 → null stays).
//
// Regression: guest tapping an allowlisted whisky hit the authed
// tasting-notes path → 401 → swallowed → "Viski bulunamadı".

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';

void main() {
  DbWhiskyApiClient clientThatReturns(int statusCode) =>
      DbWhiskyApiClient(client: MockClient((_) async => http.Response('x', statusCode)));

  test('getWhiskyById 401 → DbApiAuthRequiredException (not null)', () async {
    final client = clientThatReturns(401);

    expect(
      () => client.getWhiskyById('W-1'),
      throwsA(isA<DbApiAuthRequiredException>()),
    );
  });

  test('getFlavorProfile 401 → DbApiAuthRequiredException', () async {
    final client = clientThatReturns(401);

    expect(
      () => client.getFlavorProfile('W-1'),
      throwsA(isA<DbApiAuthRequiredException>()),
    );
  });

  test('getTastingNotes 401 → DbApiAuthRequiredException', () async {
    final client = clientThatReturns(401);

    expect(
      () => client.getTastingNotes('W-1'),
      throwsA(isA<DbApiAuthRequiredException>()),
    );
  });

  test('getWhiskyById 404 → null (not-found contract preserved)', () async {
    final client = clientThatReturns(404);

    expect(await client.getWhiskyById('W-YOK'), isNull);
  });
}
