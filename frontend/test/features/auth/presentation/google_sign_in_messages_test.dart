import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/auth/presentation/google_sign_in_messages.dart';

void main() {
  group('googleSignInErrorMessage', () {
    test('returns correct message for google_popup_closed (English)', () {
      expect(
        googleSignInErrorMessage('google_popup_closed', isTr: false),
        'Sign-in popup closed. Please try again.',
      );
    });

    test('returns correct message for google_popup_closed (Turkish)', () {
      expect(
        googleSignInErrorMessage('google_popup_closed', isTr: true),
        'Popup kapatıldı. Tekrar deneyin.',
      );
    });

    test('returns correct message for google_sign_in_failed (English)', () {
      expect(
        googleSignInErrorMessage('google_sign_in_failed', isTr: false),
        'Google sign-in failed. Please try again.',
      );
    });

    test('returns correct message for google_sign_in_failed (Turkish)', () {
      expect(
        googleSignInErrorMessage('google_sign_in_failed', isTr: true),
        'Google ile giriş yapılamadı. Tekrar deneyin.',
      );
    });

    test('returns correct message for google_unknown (English)', () {
      expect(
        googleSignInErrorMessage('google_unknown', isTr: false),
        'Something went wrong. Please try again.',
      );
    });

    test('returns correct message for google_unknown (Turkish)', () {
      expect(
        googleSignInErrorMessage('google_unknown', isTr: true),
        'Bir şeyler ters gitti. Tekrar deneyin.',
      );
    });

    test('returns backend message unchanged for other codes (English)', () {
      expect(
        googleSignInErrorMessage('some_backend_error', isTr: false),
        'some_backend_error',
      );
    });

    test('returns backend message unchanged for other codes (Turkish)', () {
      expect(
        googleSignInErrorMessage('some_backend_error', isTr: true),
        'some_backend_error',
      );
    });
  });
}
