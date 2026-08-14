import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:google_sign_in/google_sign_in.dart';

/// Thin seam around the `google_sign_in` plugin so the auth controller (and
/// its tests) never touch the platform implementation directly.
///
/// Web + mobile share one flow: interactive sign-in → OAuth id token.
/// Returns `null` when the user cancels / closes the popup before a token
/// is produced (the "popup kapalı" case the backend contract calls 400).
///
/// Uses the modern 7.x Google Identity Services (GSI) flow:
/// `GoogleSignIn.instance.initialize()` (loads the GSI script on web, required
/// before any other call) followed by `GoogleSignIn.instance.authenticate()`.
/// The legacy 6.x `signIn()` web path was removed by Google in 2024 and now
/// surfaces as a silent failure ("Something went wrong" / "Popup kapatıldı"),
/// which is the bug this migration fixes.
class GoogleAuth {
  /// Error codes the platform plugins used to surface when the user dismisses
  /// the flow. Legacy 6.x web threw `PlatformException(code:
  /// 'popup_closed_by_user')`; mobile used `sign_in_canceled`. Kept as a
  /// defensive backstop: the 7.x flow throws `GoogleSignInException(code:
  /// GoogleSignInExceptionCode.canceled)` instead, but a stray legacy
  /// `PlatformException` still maps to a dismissed flow, never a raw error.
  static const Set<String> _cancelCodes = {
    'popup_closed_by_user',
    'sign_in_canceled',
    'canceled',
  };

  /// `initialize()` must be called exactly once before any other method on the
  /// `GoogleSignIn` singleton. Memoize the future so repeated/concurrent calls
  /// share a single initialization — calling it twice is undefined behavior.
  static Future<void>? _initFuture;

  /// Test-only: clears the memoized [initialize] future so a fake platform can
  /// be re-initialized per test. Never call this from app code.
  @visibleForTesting
  static void resetInitializationForTest() => _initFuture = null;

  final String? _clientId;
  final List<String> _scopes;

  /// [clientId] is the web OAuth client id (from
  /// `--dart-define=GOOGLE_CLIENT_ID_WEB`). `null` on mobile is fine — the
  /// platform plugins fall back to the client ids configured natively; an
  /// *empty string* would crash iOS `GIDConfiguration(clientID: '')`, so we
  /// never pass `''` through.
  GoogleAuth({this._clientId, this._scopes = const ['email']});

  /// Web OAuth client id (`--dart-define=GOOGLE_CLIENT_ID_WEB`). Null on
  /// mobile. Exposed so the web GSI button can initialize the plugin with the
  /// same id used by the interactive flow.
  String? get clientId => _clientId;

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
      // 7.x: initialize the singleton exactly once (loads the GSI script on
      // web). Re-initializing is undefined behavior, so memoize the future via
      // `??=` and reset it only on failure to allow a later retry.
      _initFuture ??= GoogleSignIn.instance.initialize(clientId: _clientId);
      await _initFuture;
      final account = await GoogleSignIn.instance.authenticate(
        scopeHint: _scopes,
      );
      // 7.x: `authentication` is a synchronous getter (not a Future) holding
      // the tokens returned at authentication time.
      return account.authentication.idToken;
    } on GoogleSignInException catch (e) {
      // 7.x cancel path: the user closed the popup / dismissed the prompt
      // (or the UI was unavailable). Treat exactly like a dismissed flow — a
      // null token, never an error.
      if (e.code == GoogleSignInExceptionCode.canceled ||
          e.code == GoogleSignInExceptionCode.interrupted ||
          e.code == GoogleSignInExceptionCode.uiUnavailable) {
        return null;
      }
      rethrow;
    } on PlatformException catch (e) {
      // Legacy 6.x web/mobile cancel path (see [_cancelCodes]).
      if (_cancelCodes.contains(e.code)) return null;
      rethrow;
    }
  }

  /// Signs the current Google account out locally (best effort).
  Future<void> signOut() async {
    // Best-effort local Google sign-out; safe to call even if no account is
    // currently signed in (it is a no-op in that case).
    await GoogleSignIn.instance.signOut();
  }
}
