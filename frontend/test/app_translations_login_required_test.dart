// The login-required detail state must have real translations in BOTH
// supported locales — a missing key silently renders the raw key string.

import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/localization/app_translations.dart';

void main() {
  test('whisky_login_required exists and is translated in TR and EN', () {
    final tr = appTranslations['tr']!['whisky_login_required'];
    final en = appTranslations['en']!['whisky_login_required'];

    expect(tr, isNotNull);
    expect(tr, isNotEmpty);
    expect(en, isNotNull);
    expect(en, isNotEmpty);
    // Real translations — the two locales must not share the same string.
    expect(tr, isNot(equals(en)));
  });
}
