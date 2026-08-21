/// Maps the semantic Google sign-in error codes returned by
/// [AuthController.signInWithGoogle] / [AuthController.signInWithGoogleFromCredential]
/// to localized, user-facing text.
///
/// Non-code errors (backend `AuthApiException` messages) pass through unchanged
/// — the same contract the email login path uses, so the backend stays the
/// single source of truth for server-side messages.
String googleSignInErrorMessage(String code, {required String Function(String) tr}) {
  switch (code) {
    case 'google_popup_closed':
      return tr('google_popup_closed');
    case 'google_sign_in_failed':
      return tr('google_sign_in_failed');
    case 'google_unknown':
      return tr('google_unknown');
    default:
      return code;
  }
}
