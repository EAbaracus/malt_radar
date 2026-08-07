import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import '../data/auth_repository.dart';
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

  AuthController({required this.api, required this.repo})
    : super(const AuthState.initial()) {
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

  Future<void> logout() async {
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

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return AuthRepository(db);
});

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) {
    final api = ref.watch(authApiProvider);
    final repo = ref.watch(authRepositoryProvider);
    return AuthController(api: api, repo: repo);
  },
);

final syncServiceProvider = Provider<SyncService>((ref) {
  final db = ref.watch(appDatabaseProvider);
  final api = ref.watch(authApiProvider);
  final repo = ref.watch(authRepositoryProvider);
  return SyncService(db, api, repo);
});
