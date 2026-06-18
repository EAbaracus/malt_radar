import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/config/app_config.dart';
import 'package:malt_radar/features/whisky/data/dto/db_whisky_dto.dart';

void main() {
  group('Feature Flag Validation', () {
    test('USE_DB_API default is false', () {
      expect(AppConfig.useDbApi, false);
    });
  });

  group('DTO Mapper Validation', () {
    test('Maps full DB whisky correctly to legacy map', () {
      final dbWhisky = {
        'whisky_id': 'db-12345',
        'name': 'Test Whisky',
        'country': 'Scotland',
        'region': 'Islay',
        'category': 'Single Malt',
        'distillery': 'Test Distillery',
        'stated_age': 10,
        'abv': 46.0,
        'cask_type': 'Ex-Bourbon',
        'retail_price': 50.0,
        'currency': 'GBP',
        'source': 'TheWhiskyExchange',
        'url': 'http://test.com',
        'global_rating': 85.5
      };

      final flavorProfile = {
        'flavor_vector_json': '[0.1, 0.2, 0.3]',
        'flavor_tags_json': '["peat", "smoke"]',
        'source': 'Internal'
      };

      final tastingNotes = [
        {'note_text': 'A hint of smoke'},
        {'note_text': 'Vanilla and oak'}
      ];

      final mapped = DbWhiskyMapper.toLegacyMap(
        dbWhisky,
        flavorProfile: flavorProfile,
        tastingNotes: tastingNotes,
      );

      expect(mapped['external_id'], 'db-12345');
      expect(mapped['name'], 'Test Whisky');
      expect(mapped['age'], 10);
      expect(mapped['default_price'], 50.0);
      expect(mapped['tasting_notes'], ['A hint of smoke', 'Vanilla and oak']);
      expect(mapped['flavor_profile'], isNotNull);
      expect(mapped['flavor_vector'], '[0.1, 0.2, 0.3]');
    });

    test('Maps null-heavy DB whisky gracefully', () {
      final dbWhisky = {
        'whisky_id': 999, // Integer instead of string
        'name': null,     // Null name
      };

      final mapped = DbWhiskyMapper.toLegacyMap(dbWhisky);

      expect(mapped['external_id'], '999'); // stringified
      expect(mapped['name'], 'Unknown'); // Fallback
      expect(mapped['tasting_notes'], isEmpty);
      expect(mapped['flavor_profile'], isNull);
    });
  });
}
