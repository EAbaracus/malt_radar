import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/compliance/domain/legal_age.dart';

void main() {
  group('Legal Age Domain', () {
    group('legalAgeFor', () {
      test('returns 21 for United States (US)', () {
        expect(legalAgeFor('US'), 21);
      });

      test('returns 20 for Japan (JP)', () {
        expect(legalAgeFor('JP'), 20);
      });

      test('returns 19 for South Korea (KR)', () {
        expect(legalAgeFor('KR'), 19);
      });

      test('returns 18 for United Kingdom (GB)', () {
        expect(legalAgeFor('GB'), 18);
      });

      test('returns defaultMinAge (18) for unknown country code', () {
        expect(legalAgeFor('ZZ'), defaultMinAge);
      });

      test('is case sensitive for unknown formats (assuming input is upper)', () {
        // The implementation does strict `==` check. 'us' would fallback to default.
        expect(legalAgeFor('us'), defaultMinAge);
      });
    });

    group('sortedEntries', () {
      test('returns a list sorted alphabetically by name', () {
        final sorted = sortedEntries();

        expect(sorted.isNotEmpty, true);

        for (int i = 0; i < sorted.length - 1; i++) {
          final a = sorted[i].name;
          final b = sorted[i + 1].name;
          expect(a.compareTo(b) <= 0, true, reason: '$a should be before or equal to $b');
        }
      });

      test('does not modify the original list', () {
        final sorted = sortedEntries();

        // Find an entry that moves, e.g., 'Argentina' which should be first in sorted
        // but isn't first in the original list.
        expect(legalDrinkingAges.first.name, 'United States');
        expect(sorted.first.name, 'Argentina');
      });

      test('contains the exact same elements as the original list', () {
        final sorted = sortedEntries();
        expect(sorted.length, legalDrinkingAges.length);

        for (final entry in legalDrinkingAges) {
          expect(sorted.contains(entry), true);
        }
      });
    });
  });
}
