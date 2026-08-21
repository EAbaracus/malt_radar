import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/localization/flavor_tag_translator.dart';

void main() {
  group('localizeFlavorTag', () {
    test('translates English to Turkish correctly', () {
      expect(localizeFlavorTag('apple', 'tr'), 'Elma');
      expect(localizeFlavorTag('sherry', 'tr'), 'Şeri');
      expect(localizeFlavorTag('sweet', 'tr'), 'Tatlı');
    });

    test('translates Turkish to English correctly', () {
      expect(localizeFlavorTag('elma', 'en'), 'Apple');
      expect(localizeFlavorTag('şeri', 'en'), 'Sherry');
      expect(localizeFlavorTag('tatlı', 'en'), 'Sweet');
    });

    test('handles whitespace and mixed casing correctly', () {
      expect(localizeFlavorTag('  aPPle  ', 'tr'), 'Elma');
      expect(localizeFlavorTag('  eLma  ', 'en'), 'Apple');
    });

    test('returns capitalized original tag if not found in map', () {
      expect(localizeFlavorTag('unknownTag', 'tr'), 'Unknowntag');
      expect(localizeFlavorTag('unknownTag', 'en'), 'Unknowntag');
      expect(localizeFlavorTag('bilinmeyen', 'en'), 'Bilinmeyen');
    });

    test('handles empty strings and whitespace-only strings gracefully', () {
      expect(localizeFlavorTag('', 'tr'), '');
      expect(localizeFlavorTag('   ', 'en'), '');
    });
  });

  group('localizeTastingNote', () {
    test('translates Turkish tasting note to English correctly', () {
      expect(localizeTastingNote('Zengin vanilya', 'en'), 'Rich vanilla');
      expect(localizeTastingNote('Burun: bal', 'en'), 'Nose: honey');
      expect(localizeTastingNote('Damak: esmer şeker', 'en'), 'Palate: brown sugar');
      expect(localizeTastingNote('Bitiş: Orta', 'en'), 'Finish: Medium');
    });

    test('translates English tasting note to Turkish correctly (exact matches)', () {
      expect(localizeTastingNote('Rich vanilla', 'tr'), 'Zengin vanilya');
      expect(localizeTastingNote('Medium', 'tr'), 'Orta');
    });

    test('translates English tasting note prefixes to Turkish correctly', () {
      expect(localizeTastingNote('Nose: Some notes', 'tr'), 'Burun: Some notes');
      expect(localizeTastingNote('Palate: some notes', 'tr'), 'Damak: some notes');
      expect(localizeTastingNote('Finish: some notes', 'tr'), 'Bitiş: some notes');
    });

    test('returns original string if no translation found', () {
      expect(localizeTastingNote('Unknown note', 'tr'), 'Unknown note');
      expect(localizeTastingNote('Unknown note', 'en'), 'Unknown note');
    });

    test('handles whitespace in tasting notes gracefully', () {
      expect(localizeTastingNote('  Rich vanilla  ', 'tr'), 'Zengin vanilya');
      expect(localizeTastingNote('  Zengin vanilya  ', 'en'), 'Rich vanilla');
    });
  });
}
