import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

/// Thin seam around the `google_sign_in` plugin so the auth controller (and
/// its tests) never touch the platform implementation directly.
///
/// Web + mobile share one flow: interactive sign-in → OAuth id token.
/// Returns `null` when the user cancels / closes the popup before a token
/// is produced (the "popup kapalı" case the backend contract calls 400).
class GoogleAuth {
  final String _clientId;
  final GoogleSignIn _google;

  GoogleAuth({String clientId = '', List<String> scopes = const ['email']})
    : _clientId = clientId,
      _google = GoogleSignIn(clientId: clientId, scopes: scopes);

  /// Runs the interactive Google sign-in flow and returns the OAuth ID token.
  ///
  /// `null` means the flow was dismissed (popup closed) — never an exception.
  /// On web an empty [clientId] (dart-define not yet wired) fails fast with a
  /// descriptive error instead of a confusing plugin failure.
  Future<String?> fetchIdToken() async {
    if (kIsWeb && _clientId.isEmpty) {
      throw StateError(
        'GOOGLE_CLIENT_ID_WEB is not configured '
        '(missing --dart-define=GOOGLE_CLIENT_ID_WEB=...)',
      );
    }
    final account = await _google.signIn();
    if (account == null) return null;
    final auth = await account.authentication;
    return auth.idToken;
  }

  /// Signs the current Google account out locally (best effort).
  Future<void> signOut() async {
    await _google.signOut();
  }
}