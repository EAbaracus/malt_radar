import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/auth/presentation/google_sign_in_messages.dart';
import 'package:malt_radar/core/localization/app_translations.dart';

void main() {
  String mockTr(String lang, String key) {
    return appTranslations[lang]?[key] ?? key;
  }

  group('googleSignInErrorMessage', () {
    test('returns correct message for google_popup_closed (English)', () {
      expect(
        googleSignInErrorMessage('google_popup_closed', tr: (k, [a]) => mockTr('en', k)),
        'Sign-in popup closed. Please try again.',
      );
    });

    test('returns correct message for google_popup_closed (Turkish)', () {
      expect(
        googleSignInErrorMessage('google_popup_closed', tr: (k, [a]) => mockTr('tr', k)),
        'Popup kapatıldı. Tekrar deneyin.',
      );
    });

    test('returns correct message for google_sign_in_failed (English)', () {
      expect(
        googleSignInErrorMessage('google_sign_in_failed', tr: (k, [a]) => mockTr('en', k)),
        'Google sign-in failed. Please try again.',
      );
    });

    test('returns correct message for google_sign_in_failed (Turkish)', () {
      expect(
        googleSignInErrorMessage('google_sign_in_failed', tr: (k, [a]) => mockTr('tr', k)),
        'Google ile giriş yapılamadı. Tekrar deneyin.',
      );
    });

    test('returns correct message for google_unknown (English)', () {
      expect(
        googleSignInErrorMessage('google_unknown', tr: (k, [a]) => mockTr('en', k)),
        'Something went wrong. Please try again.',
      );
    });

    test('returns correct message for google_unknown (Turkish)', () {
      expect(
        googleSignInErrorMessage('google_unknown', tr: (k, [a]) => mockTr('tr', k)),
        'Bir şeyler ters gitti. Tekrar deneyin.',
      );
    });

    test('returns backend message unchanged for other codes (English)', () {
      expect(
        googleSignInErrorMessage('some_backend_error', tr: (k, [a]) => mockTr('en', k)),
        'some_backend_error',
      );
    });

    test('returns backend message unchanged for other codes (Turkish)', () {
      expect(
        googleSignInErrorMessage('some_backend_error', tr: (k, [a]) => mockTr('tr', k)),
        'some_backend_error',
      );
    });
  });
}
