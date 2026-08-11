import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:google_sign_in/google_sign_in.dart';

/// Thin seam around the `google_sign_in` plugin so the auth controller (and
/// its tests) never touch the platform implementation directly.
///
/// Web + mobile share one flow: interactive sign-in → OAuth id token.
/// Returns `null` when the user cancels / closes the popup before a token
/// is produced (the "popup kapalı" case the backend contract calls 400).
class GoogleAuth {
  /// Error codes the platform plugins use when the user dismisses the flow.
  ///
  /// The host's `signIn()` already maps `sign_in_canceled` (mobile) to null,
  /// but the web implementation (google_sign_in_web 0.12.4) throws
  /// `PlatformException(code: 'popup_closed_by_user')` when the popup is
  /// closed — which the host does NOT translate. We normalise all of them.
  static const Set<String> _cancelCodes = {
    'popup_closed_by_user',
    'sign_in_canceled',
    'canceled',
  };

  final String? _clientId;
  final GoogleSignIn _google;

  /// [clientId] is the web OAuth client id (from
  /// `--dart-define=GOOGLE_CLIENT_ID_WEB`). `null` on mobile is fine — the
  /// platform plugins fall back to the client ids configured natively; an
  /// *empty string* would crash iOS `GIDConfiguration(clientID: '')`, so we
  /// never pass `''` through.
  GoogleAuth({String? clientId, List<String> scopes = const ['email']})
    : _clientId = clientId,
      _google = GoogleSignIn(clientId: clientId, scopes: scopes);

  /// Runs the interactive Google sign-in flow and returns the OAuth ID token.
  ///
  /// `null` means the flow was dismissed (popup closed) — never an exception.
  /// On web a missing/empty [clientId] (dart-define not yet wired) fails fast
  /// with a descriptive error instead of a confusing plugin failure.
  Future<String?> fetchIdToken() async {
    if (kIsWeb && (_clientId == null || _clientId.isEmpty)) {
      throw StateError(
        'GOOGLE_CLIENT_ID_WEB is not configured '
        '(missing --dart-define=GOOGLE_CLIENT_ID_WEB=...)',
      );
    }
    try {
      final account = await _google.signIn();
      if (account == null) return null;
      final auth = await account.authentication;
      return auth.idToken;
    } on PlatformException catch (e) {
      // Popup closed by the user (web) or flow canceled (mobile): treat it
      // exactly like `account == null` — a dismissed flow, not an error.
      if (_cancelCodes.contains(e.code)) return null;
      rethrow;
    }
  }

  /// Signs the current Google account out locally (best effort).
  Future<void> signOut() async {
    await _google.signOut();
  }
}
