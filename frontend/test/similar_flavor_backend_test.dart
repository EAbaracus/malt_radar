import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/data/repositories/db_whisky_repository_impl.dart';
import 'package:drift/native.dart';

const _similarJson = {
  'whisky_id': 'W000001',
  'similar': [
    {
      'whisky_id': 'W000002',
      'name': 'Ardbeg 10',
      'distillery_name': 'Ardbeg',
      'region': 'Islay',
      'type': 'Malt',
      'meta_critic_score': 8.4,
      'distance': 0.5,
      'similarity': 0.586,
    },
    {
      'whisky_id': 'W000003',
      'name': 'Laphroaig 10',
      'distillery_name': 'Laphroaig',
      'region': 'Islay',
      'type': 'Malt',
      'distance': 1.2,
      'similarity': 0.477,
    },
  ],
};

void main() {
  test('client getSimilarWhiskies parses public /similar response', () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async {
        expect(req.url.path, '/api/db/public/whiskies/W000001/similar');
        return http.Response('''{"whisky_id":"W000001","similar":[
          {"whisky_id":"W000002","name":"Ardbeg 10","distillery_name":"Ardbeg",
           "region":"Islay","type":"Malt","meta_critic_score":8.4,
           "distance":0.5,"similarity":0.586}]}''', 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }),
    );
    final result = await client.getSimilarWhiskies('W000001', limit: 5);
    expect(result, isNotNull);
    expect(result!.length, 1);
    expect(result.first['whisky_id'], 'W000002');
  });

  test('client returns null on 404 (target not found)', () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async => http.Response('not found', 404)),
    );
    expect(await client.getSimilarWhiskies('W000001'), isNull);
  });

  test('repo uses endpoint result and maps similarity to styleSimilarity',
      () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async => http.Response(
          jsonEncode(_similarJson), 200,
          headers: {'content-type': 'application/json; charset=utf-8'})),
    );
    final repo = DbWhiskyRepositoryImpl(AppDatabase.forTesting(NativeDatabase.memory()), client);
    final result = await repo.getSimilarWhiskies('W000001', limit: 5);
    expect(result.length, 2);
    expect(result.first.externalId, 'W000002');
    expect(result.first.styleSimilarity, isNotNull);
    expect(result.first.globalScore, 8.4); // meta_critic_score fallback
    await repo.clearCache();
  });

  test('repo falls back to bounded fetch when endpoint 404s', () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async {
        if (req.url.path.endsWith('/similar')) {
          return http.Response('not found', 404);
        }
        if (req.url.path.contains('/whiskies')) {
          return http.Response(
              '{"items":[{"whisky_id":"W000009","name":"Glenfiddich 12",'
              '"flavor_profile":"{\\"fruity\\":3.0,\\"sweet\\":4.0,'
              '\\"spicy\\":1.0,\\"smoky_peaty\\":0.0,\\"oak_cask\\":2.0,'
              '\\"malty_cereal\\":5.0,\\"floral_herbal\\":2.0}"}],'
              '"total_count":1,"limit":50,"offset":0}', 200,
              headers: {'content-type': 'application/json; charset=utf-8'});
        }
        return http.Response('{"similar":[]}', 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }),
    );
    final repo = DbWhiskyRepositoryImpl(AppDatabase.forTesting(NativeDatabase.memory()), client);
    final result = await repo.getSimilarWhiskies('W000001', limit: 5);
    expect(result, isA<List>());
    await repo.clearCache();
  });
}
