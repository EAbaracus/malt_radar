import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';

void main() {
  test('getWhiskies sends the filter param to the backend (not swallowed)', () async {
    Uri? captured;
    final mock = MockClient((request) async {
      captured = request.url;
      return http.Response(
        jsonEncode({
          'items': <Object>[],
          'total_count': 0,
          'limit': 50,
          'offset': 0,
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final client = DbWhiskyApiClient(client: mock);
    await client.getWhiskies(limit: 50, offset: 0, filter: 'peated,sherry');

    expect(captured, isNotNull);
    final params = captured!.queryParameters;
    expect(params['filter'], 'peated,sherry');
  });

  test('getWhiskies omits filter when null/empty', () async {
    Uri? captured;
    final mock = MockClient((request) async {
      captured = request.url;
      return http.Response(
        jsonEncode({
          'items': <Object>[],
          'total_count': 0,
          'limit': 50,
          'offset': 0,
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final client = DbWhiskyApiClient(client: mock);
    await client.getWhiskies(limit: 50, offset: 0);

    expect(captured, isNotNull);
    expect(captured!.queryParameters.containsKey('filter'), isFalse);
  });
}
