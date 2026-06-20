import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/localization/flavor_tag_translator.dart';

void main() {
  group('tasting notes localization', () {
    test('English locale translates Burun note', () {
      expect(
        localizeTastingNote('Burun: Zengin vanilya', 'en'),
        'Nose: Rich vanilla',
      );
    });

    test('English locale translates Damak note', () {
      expect(
        localizeTastingNote('Damak: Pürüzsüz maltsı tatlılık', 'en'),
        'Palate: Smooth malty sweetness',
      );
    });

    test('English locale translates Bitiş note', () {
      expect(localizeTastingNote('Bitiş: Orta', 'en'), 'Finish: Medium');
    });

    test('English locale translates individual tasting note chips', () {
      expect(localizeTastingNote('bal', 'en'), 'honey');
      expect(localizeTastingNote('esmer şeker', 'en'), 'brown sugar');
      expect(localizeTastingNote('tatlı meşe', 'en'), 'sweet oak');
    });

    test('Turkish locale returns original Turkish strings', () {
      expect(
        localizeTastingNote('Burun: Zengin vanilya', 'tr'),
        'Burun: Zengin vanilya',
      );
      expect(localizeTastingNote('bal', 'tr'), 'bal');
      expect(localizeTastingNote('tatlı meşe', 'tr'), 'tatlı meşe');
    });

    test('unknown string falls back to original raw string', () {
      expect(
        localizeTastingNote('beklenmeyen tadım notu', 'en'),
        'beklenmeyen tadım notu',
      );
    });
  });
}
