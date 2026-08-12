import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import '../data/auth_repository.dart';
import '../data/google_auth.dart';
import '../data/sync_service.dart';
import '../domain/auth_user.dart';

enum AuthStatus { unknown, loggedOut, loggedIn }

@immutable
class AuthState {
  final AuthStatus status;
  final AuthUser? user;
  final String? error;

  const AuthState(this.status, {this.user, this.error});

  const AuthState.initial() : this(AuthStatus.unknown);
  bool get isLoggedIn => status == AuthStatus.loggedIn && user != null;
}

class AuthController extends StateNotifier<AuthState> {
  final AuthApi api;
  final AuthRepository repo;
  final GoogleAuth googleAuth;

  /// Error codes the platform plugins use when the user dismisses the Google
  /// flow (web popup closed / mobile cancel). The seam already normalises
  /// these to a null token; this set is a defensive backstop so a stray
  /// PlatformException still reads as "popup closed", never a raw error.
  static const Set<String> _googleCancelCodes = {
    'popup_closed_by_user',
    'sign_in_canceled',
    'canceled',
  };

  bool _googleSignInInProgress = false;

  AuthController({
    required this.api,
    required this.repo,
    GoogleAuth? googleAuth,
  }) : googleAuth = googleAuth ?? GoogleAuth(),
       super(const AuthState.initial()) {
    _restore();
  }

  Future<void> _restore() async {
    final token = await repo.loadToken();
    final user = await repo.loadUser();
    if (token != null && user != null) {
      state = AuthState(AuthStatus.loggedIn, user: user);
    } else {
      state = const AuthState(AuthStatus.loggedOut);
    }
  }

  Future<String?> login(String email, String password) async {
    try {
      final res = await api.login(email.trim(), password);
      final user = AuthUser.fromJson(res['user'] as Map<String, dynamic>);
      final token = res['token'] as String;
      await repo.saveSession(token, user);
      state = AuthState(AuthStatus.loggedIn, user: user);
      return null;
    } on AuthApiException catch (e) {
      state = AuthState(AuthStatus.loggedOut, error: e.message);
      return e.message;
    } catch (e) {
      // Catch any unexpected exception (timeout, parse error, etc.)
      final msg = 'Beklenmeyen hata: $e';
      state = AuthState(AuthStatus.loggedOut, error: msg);
      return msg;
    }
  }

  Future<String?> register({
    required String email,
    required String password,
    String? displayName,
    required String ageCountry,
    required int ageMin,
    required bool privacyConsent,
  }) async {
    try {
      final res = await api.register(
        email: email.trim(),
        password: password,
        displayName: displayName,
        ageCountry: ageCountry,
        ageMin: ageMin,
        privacyConsent: privacyConsent,
      );
      final user = AuthUser.fromJson(res['user'] as Map<String, dynamic>);
      final token = res['token'] as String;
      await repo.saveSession(token, user);
      state = AuthState(AuthStatus.loggedIn, user: user);
      return null;
    } on AuthApiException catch (e) {
      state = AuthState(AuthStatus.loggedOut, error: e.message);
      return e.message;
    }
  }

  /// Google sign-in: interactive OAuth flow -> id token -> backend
  /// `POST /api/auth/google` -> session persisted through the SAME
  /// [AuthRepository.saveSession] path as email login.
  ///
  /// Returns `null` on success; a semantic error code otherwise
  /// (`google_popup_closed` / `google_sign_in_failed` / `google_unknown`).
  /// The UI layer localizes codes to user-facing text and [AuthState.error]
  /// carries the same code. Backend `AuthApiException` messages pass
  /// through unchanged (same as email login). Duplicate calls while a flow
  /// is already running are ignored.
  Future<String?> signInWithGoogle() async {
    if (_googleSignInInProgress) {
      // Re-entry guard: a second tap while the popup is open must not start
      // a parallel flow. Return null so the caller treats it as a no-op.
      return null;
    }
    _googleSignInInProgress = true;
    try {
      final idToken = await googleAuth.fetchIdToken();
      if (idToken == null || idToken.isEmpty) {
        // Popup dismissed before a token was produced (backend 400 case).
        state = const AuthState(
          AuthStatus.loggedOut,
          error: 'google_popup_closed',
        );
        return 'google_popup_closed';
      }
      final res = await api.signInWithGoogle(idToken);
      final user = AuthUser.fromJson(res['user'] as Map<String, dynamic>);
      final token = res['token'] as String;
      await repo.saveSession(token, user);
      state = AuthState(AuthStatus.loggedIn, user: user);
      return null;
    } on AuthApiException catch (e) {
      state = AuthState(AuthStatus.loggedOut, error: e.message);
      return e.message;
    } on PlatformException catch (e) {
      // Should not normally reach here (seam maps cancels to null), but
      // classify defensively so no raw platform error leaks to the user.
      final code = _googleCancelCodes.contains(e.code)
          ? 'google_popup_closed'
          : 'google_sign_in_failed';
      state = AuthState(AuthStatus.loggedOut, error: code);
      return code;
    } on GoogleSignInException catch (e) {
      // 7.x path: the seam normalises cancels to null, so a
      // GoogleSignInException reaching here is a non-cancel failure (or a
      // cancel on a path the seam didn't get to normalise). Classify
      // defensively so no raw exception leaks to the user.
      final code = e.code == GoogleSignInExceptionCode.canceled
          ? 'google_popup_closed'
          : 'google_sign_in_failed';
      state = AuthState(AuthStatus.loggedOut, error: code);
      return code;
    } catch (_) {
      state = const AuthState(AuthStatus.loggedOut, error: 'google_unknown');
      return 'google_unknown';
    } finally {
      _googleSignInInProgress = false;
    }
  }

  Future<void> logout() async {
    try {
      // Best-effort local Google sign-out; never let it block logout.
      await googleAuth.signOut();
    } catch (_) {
      // Local Google session may already be gone — ignore.
    }
    final token = await repo.loadToken();
    if (token != null) {
      try {
        await api.logout(token);
      } catch (_) {
        // Best-effort server revocation; always clear the local session.
      }
    }
    await repo.clearSession();
    state = const AuthState(AuthStatus.loggedOut);
  }

  Future<void> refresh() async {
    try {
      final token = await repo.loadToken();
      if (token == null) {
        state = const AuthState(AuthStatus.loggedOut);
        return;
      }
      final res = await api.me(token);
      final user = AuthUser.fromJson(res);
      await repo.saveSession(token, user);
      state = AuthState(AuthStatus.loggedIn, user: user);
    } on AuthApiException {
      // Offline / invalid token: keep the cached session; user can retry.
    }
  }

  Future<String?> updateProfile({String? displayName}) async {
    if (!state.isLoggedIn) return 'Not authenticated';
    final token = await repo.loadToken();
    if (token == null) return 'Not authenticated';
    try {
      final res = await api.updateProfile(token, displayName: displayName);
      final user = AuthUser.fromJson(res);
      await repo.saveSession(token, user);
      state = AuthState(AuthStatus.loggedIn, user: user);
      return null;
    } on AuthApiException catch (e) {
      return e.message;
    }
  }
}

final authApiProvider = Provider<AuthApi>((ref) => AuthApi());

/// Web Google OAuth client id, injected at build time via
/// `--dart-define=GOOGLE_CLIENT_ID_WEB=...`. `null` until wired — the web
/// flow then fails fast with a clear message. Nullable (never `''`) so
/// mobile platforms don't receive an empty client id, which crashes iOS
/// `GIDConfiguration(clientID: '')`; on mobile the plugin falls back to the
/// client ids configured natively.
const String? googleClientId = bool.hasEnvironment('GOOGLE_CLIENT_ID_WEB')
    ? String.fromEnvironment('GOOGLE_CLIENT_ID_WEB')
    : null;

final googleAuthProvider = Provider<GoogleAuth>(
  (ref) => GoogleAuth(clientId: googleClientId),
);

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return AuthRepository(db);
});

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) {
    final api = ref.watch(authApiProvider);
    final repo = ref.watch(authRepositoryProvider);
    final googleAuth = ref.watch(googleAuthProvider);
    return AuthController(api: api, repo: repo, googleAuth: googleAuth);
  },
);

final syncServiceProvider = Provider<SyncService>((ref) {
  final db = ref.watch(appDatabaseProvider);
  final api = ref.watch(authApiProvider);
  final repo = ref.watch(authRepositoryProvider);
  return SyncService(db, api, repo);
});
