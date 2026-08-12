/// Maps the semantic Google sign-in error codes returned by
/// [AuthController.signInWithGoogle] / [AuthController.signInWithGoogleFromCredential]
/// to localized, user-facing text.
///
/// Non-code errors (backend `AuthApiException` messages) pass through unchanged
/// — the same contract the email login path uses, so the backend stays the
/// single source of truth for server-side messages.
String googleSignInErrorMessage(String code, {required bool isTr}) {
  switch (code) {
    case 'google_popup_closed':
      return isTr
          ? 'Popup kapatıldı. Tekrar deneyin.'
          : 'Sign-in popup closed. Please try again.';
    case 'google_sign_in_failed':
      return isTr
          ? 'Google ile giriş yapılamadı. Tekrar deneyin.'
          : 'Google sign-in failed. Please try again.';
    case 'google_unknown':
      return isTr
          ? 'Bir şeyler ters gitti. Tekrar deneyin.'
          : 'Something went wrong. Please try again.';
    default:
      return code;
  }
}
