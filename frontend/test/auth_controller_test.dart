// Unit tests for the auth controller + session persistence. Uses a fake API
// and an in-memory Drift DB — no network, no widgets.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';

import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/auth/data/google_auth.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

class FakeAuthApi extends AuthApi {
  String? serverToken;
  Map<String, dynamic> _user() => {
        'id': 1,
        'email': 'user@example.com',
        'display_name': null,
        'email_verified': 1,
        'privacy_consent': 1,
        'age_country': 'TR',
        'age_min': 18,
        'created_at': '2026-08-06T00:00:00+00:00',
      };

  @override
  Future<Map<String, dynamic>> login(String email, String password) async {
    if (email.trim() != 'user@example.com' || password != 's3curePass') {
      throw AuthApiException('Invalid email or password');
    }
    serverToken = 'tok-1';
    return {'token': serverToken!, 'user': _user()};
  }

  @override
  Future<Map<String, dynamic>> signInWithGoogle(String idToken) async {
    if (idToken != 'good-google-token') {
      // Mirrors the backend contract: 401 for an invalid/expired token.
      throw AuthApiException('Gecersiz Google kimlik dogrulamasi');
    }
    serverToken = 'tok-google';
    return {'token': serverToken!, 'user': _user()};
  }

  @override
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? displayName,
    required String ageCountry,
    required int ageMin,
    required bool privacyConsent,
  }) async {
    serverToken = 'tok-2';
    if (!privacyConsent) {
      throw AuthApiException('Privacy consent is required');
    }
    return {'token': serverToken!, 'user': _user()};
  }

  @override
  Future<void> logout(String token) async {
    if (serverToken == token) serverToken = null;
  }
}

/// Fake Google OAuth seam: returns a fixed id token, or throws / returns
/// null to simulate failure and popup-dismissed cases.
class FakeGoogleAuth extends GoogleAuth {
  final String? idToken;
  final Object? error;
  FakeGoogleAuth({this.idToken, this.error});

  @override
  Future<String?> fetchIdToken() async {
    if (error != null) throw error!;
    return idToken;
  }

  @override
  Future<void> signOut() async {}
}

Future<ProviderContainer> buildContainer(
  AppDatabase db,
  AuthApi api, {
  GoogleAuth? googleAuth,
}) async {
  final container = ProviderContainer(
    overrides: [
      appDatabaseProvider.overrideWithValue(db),
      authApiProvider.overrideWithValue(api),
      if (googleAuth != null) googleAuthProvider.overrideWithValue(googleAuth),
    ],
  );
  addTearDown(container.dispose);
  // Create the controller (triggers async session restore) and let it settle.
  container.read(authControllerProvider);
  await pumpEventQueue();
  return container;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('login populates session and persists it', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());

    final container = await buildContainer(db, FakeAuthApi());
    final auth = container.read(authControllerProvider.notifier);

    final err = await auth.login('user@example.com', 's3curePass');
    expect(err, isNull);
    final state = container.read(authControllerProvider);
    expect(state.isLoggedIn, isTrue);
    expect(state.user?.email, 'user@example.com');

    final repo =
        container.read(authRepositoryProvider);
    expect(await repo.loadToken(), 'tok-1');
    expect((await repo.loadUser())?.email, 'user@example.com');
  });

  test('login failure surfaces error and keeps logged out', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());
    final container = await buildContainer(db, FakeAuthApi());
    final auth = container.read(authControllerProvider.notifier);
    final state = container.read(authControllerProvider);
    final err = await auth.login('user@example.com', 'wrong-pass');
    expect(err, isNotNull);
    expect(state.isLoggedIn, isFalse);
  });
  test('session survives across containers (persistence)', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());

    final first = await buildContainer(db, FakeAuthApi());
    await first.read(authControllerProvider.notifier)
        .login('user@example.com', 's3curePass');

    // A brand-new controller over the same DB restores the session.
    final second = await buildContainer(db, FakeAuthApi());
    final state = second.read(authControllerProvider);
    expect(state.isLoggedIn, isTrue);
    expect(state.user?.email, 'user@example.com');
  });

  test('logout clears the session', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());
    final container = await buildContainer(db, FakeAuthApi());
    final auth = container.read(authControllerProvider.notifier);
    await auth.login('user@example.com', 's3curePass');
    var state = container.read(authControllerProvider);
    expect(state.isLoggedIn, isTrue);

    await auth.logout();
    state = container.read(authControllerProvider);
    expect(state.isLoggedIn, isFalse);

    final repo = container.read(authRepositoryProvider);
    expect(await repo.loadToken(), isNull);
    expect(await repo.loadUser(), isNull);
  });

  test('register requires privacy consent', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());
    final container = await buildContainer(db, FakeAuthApi());
    final auth = container.read(authControllerProvider.notifier);
    final err = await auth.register(
      email: 'user@example.com',
      password: 's3curePass',
      ageCountry: 'TR',
      ageMin: 18,
      privacyConsent: false,
    );
    expect(err, isNotNull);
    expect(container.read(authControllerProvider).isLoggedIn, isFalse);
  });

  group('google sign-in', () {
    test('success persists session and logs in', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(idToken: 'good-google-token'),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, isNull);

      // Re-read the provider AFTER the async call (fresh snapshot).
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isTrue);
      expect(state.user?.email, 'user@example.com');
      expect(state.error, isNull);

      // Same persistence path as email login (Drift UserSettings).
      final repo = container.read(authRepositoryProvider);
      expect(await repo.loadToken(), 'tok-google');
      expect((await repo.loadUser())?.email, 'user@example.com');
    });

    test('backend rejection keeps loggedOut and sets error', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(idToken: 'expired-token'),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, isNotNull);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, isNotNull);
    });

    test('popup dismissed (null token) keeps loggedOut with message', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(idToken: null),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, isNotNull);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, isNotNull);
    });

    test('google flow exception falls into loggedOut error path', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(error: StateError('network down')),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, isNotNull);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, isNotNull);
    });
  });
}
