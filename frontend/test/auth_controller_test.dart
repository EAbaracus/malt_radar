// Unit tests for the auth controller + session persistence. Uses a fake API
// and an in-memory Drift DB — no network, no widgets.

import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';

import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/auth/data/google_auth.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

class FakeAuthApi extends AuthApi {
  String? serverToken;
  int signInWithGoogleCallCount = 0;
  Duration? signInDelay;
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
    signInWithGoogleCallCount++;
    if (signInDelay != null) await Future<void>.delayed(signInDelay!);
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
/// null to simulate failure and popup-dismissed cases. Tracks signOut calls
/// and can delay fetchIdToken to exercise the re-entry guard.
class FakeGoogleAuth extends GoogleAuth {
  final String? idToken;
  final Object? error;
  final Duration? fetchDelay;
  Object? signOutError;
  bool signOutCalled = false;
  int fetchIdTokenCallCount = 0;
  FakeGoogleAuth({this.idToken, this.error, this.fetchDelay});

  @override
  Future<String?> fetchIdToken() async {
    fetchIdTokenCallCount++;
    if (fetchDelay != null) await Future<void>.delayed(fetchDelay!);
    if (error != null) throw error!;
    return idToken;
  }

  @override
  Future<void> signOut() async {
    signOutCalled = true;
    if (signOutError != null) throw signOutError!;
  }
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

      // Backend-provided messages pass through unlocalized (same as email).
      final err = await auth.signInWithGoogle();
      expect(err, 'Gecersiz Google kimlik dogrulamasi');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'Gecersiz Google kimlik dogrulamasi');
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
      expect(err, 'google_popup_closed');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_popup_closed');
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
      expect(err, 'google_unknown');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_unknown');
    });

    test('web popup closed (PlatformException popup_closed_by_user) maps to '
        'google_popup_closed code, no raw exception leak', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(
          error: PlatformException(code: 'popup_closed_by_user'),
        ),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, 'google_popup_closed');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_popup_closed');
      // The raw platform exception must never reach the UI.
      expect(state.error, isNot(contains('popup_closed_by_user')));
    });

    test('mobile cancel (sign_in_canceled) also maps to google_popup_closed '
        'code', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(
          error: PlatformException(code: 'sign_in_canceled'),
        ),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, 'google_popup_closed');
      final state = container.read(authControllerProvider);
      expect(state.error, 'google_popup_closed');
      expect(state.error, isNot(contains('sign_in_canceled')));
    });

    test('non-cancel PlatformException maps to google_sign_in_failed code, '
        'no raw exception leak', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(
          error: PlatformException(
            code: 'network_error',
            message: 'Error 500: internal',
          ),
        ),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, 'google_sign_in_failed');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_sign_in_failed');
      expect(state.error, isNot(contains('network_error')));
      expect(state.error, isNot(contains('Error 500')));
    });

    test('7.x GoogleSignInException (canceled) maps to google_popup_closed '
        'code, no raw exception leak', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(
          error: const GoogleSignInException(
            code: GoogleSignInExceptionCode.canceled,
          ),
        ),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, 'google_popup_closed');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_popup_closed');
      // The raw platform exception must never reach the UI.
      expect(state.error, isNot(contains('canceled')));
    });

    test('7.x GoogleSignInException (non-cancel) maps to google_sign_in_failed '
        'code, no raw exception leak', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(
        db,
        FakeAuthApi(),
        googleAuth: FakeGoogleAuth(
          error: const GoogleSignInException(
            code: GoogleSignInExceptionCode.unknownError,
            description: 'misconfigured client',
          ),
        ),
      );
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogle();
      expect(err, 'google_sign_in_failed');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_sign_in_failed');
      expect(state.error, isNot(contains('misconfigured')));
    });

    test('logout calls Google signOut (best effort) and clears session',
        () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final googleAuth = FakeGoogleAuth(idToken: 'good-google-token');
      final container =
          await buildContainer(db, FakeAuthApi(), googleAuth: googleAuth);
      final auth = container.read(authControllerProvider.notifier);

      await auth.signInWithGoogle();
      expect(container.read(authControllerProvider).isLoggedIn, isTrue);

      await auth.logout();
      expect(googleAuth.signOutCalled, isTrue);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      final repo = container.read(authRepositoryProvider);
      expect(await repo.loadToken(), isNull);
    });

    test('logout still clears session when Google signOut throws '
        '(best-effort, error swallowed)', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final googleAuth = FakeGoogleAuth(idToken: 'good-google-token')
        ..signOutError = StateError('disconnected');
      final container =
          await buildContainer(db, FakeAuthApi(), googleAuth: googleAuth);
      final auth = container.read(authControllerProvider.notifier);

      await auth.signInWithGoogle();
      expect(container.read(authControllerProvider).isLoggedIn, isTrue);

      await auth.logout(); // must not throw
      expect(container.read(authControllerProvider).isLoggedIn, isFalse);
      final repo = container.read(authRepositoryProvider);
      expect(await repo.loadToken(), isNull);
    });

    test('re-entry guard: concurrent second call is a no-op', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final googleAuth = FakeGoogleAuth(
        idToken: 'good-google-token',
        fetchDelay: const Duration(milliseconds: 50),
      );
      final container =
          await buildContainer(db, FakeAuthApi(), googleAuth: googleAuth);
      final auth = container.read(authControllerProvider.notifier);

      // Both calls race while the first flow is in flight: the guard must
      // let only ONE fetchIdToken through; the second call is a no-op.
      await Future.wait([
        auth.signInWithGoogle(),
        auth.signInWithGoogle(),
      ]);
      expect(googleAuth.fetchIdTokenCallCount, 1);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isTrue);
      expect(state.user?.email, 'user@example.com');
    });
  });

  // F5: web GSI `renderButton` credential-exchange path (AuthController
  // .signInWithGoogleFromCredential). This is the web counterpart of
  // signInWithGoogle(): it takes the id token Google delivers via the
  // authenticationEvents stream and performs the SAME backend exchange. It does
  // not touch the GoogleAuth seam, so it runs on the non-web test VM.
  group('google web renderButton credential exchange', () {
    test('successful credential logs in and persists the session', () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final api = FakeAuthApi();
      final container = await buildContainer(db, api);
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogleFromCredential('good-google-token');
      expect(err, isNull);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isTrue);
      expect(state.user?.email, 'user@example.com');
      expect(state.error, isNull);
      // Same persistence path as the mobile/email login.
      final repo = container.read(authRepositoryProvider);
      expect(await repo.loadToken(), 'tok-google');
      expect((await repo.loadUser())?.email, 'user@example.com');
      expect(api.signInWithGoogleCallCount, 1);
    });

    test('empty credential reads as google_popup_closed (no raw leak)',
        () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(db, FakeAuthApi());
      final auth = container.read(authControllerProvider.notifier);

      final err = await auth.signInWithGoogleFromCredential('');
      expect(err, 'google_popup_closed');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'google_popup_closed');
    });

    test('backend rejection keeps loggedOut and sets the server message',
        () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final container = await buildContainer(db, FakeAuthApi());
      final auth = container.read(authControllerProvider.notifier);

      // Server-provided messages pass through unlocalized (same as mobile).
      final err = await auth.signInWithGoogleFromCredential('expired-token');
      expect(err, 'Gecersiz Google kimlik dogrulamasi');
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isFalse);
      expect(state.error, 'Gecersiz Google kimlik dogrulamasi');
    });

    test('re-entry guard: concurrent deliveries run only one backend exchange',
        () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(() => db.close());
      final api = FakeAuthApi()..signInDelay = const Duration(milliseconds: 50);
      final container = await buildContainer(db, api);
      final auth = container.read(authControllerProvider.notifier);

      // Two GSI credential deliveries race while the first is in flight; the
      // shared guard must let only ONE backend exchange through.
      await Future.wait([
        auth.signInWithGoogleFromCredential('good-google-token'),
        auth.signInWithGoogleFromCredential('good-google-token'),
      ]);
      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isTrue);
      expect(api.signInWithGoogleCallCount, 1,
          reason: 'only one backend exchange despite two deliveries');
    });
  });

  // Genuine seam test: drive the REAL GoogleAuth.fetchIdToken() through a fake
  // GoogleSignInPlatform so we exercise the actual 7.x initialize() +
  // authenticate() calls (NOT the removed 6.x signIn()), and confirm a canceled
  // flow maps to null. This is the only test that proves the migration swapped
  // the underlying API rather than just the FakeGoogleAuth contract.
  group('GoogleAuth 7.x seam (real authenticate() path)', () {
    late _FakeGsPlatform fakePlatform;

    setUp(() {
      fakePlatform = _FakeGsPlatform()..idTokenToReturn = 'real-7x-id-token';
      GoogleSignInPlatform.instance = fakePlatform;
      // Reset the seam's memoized init future so initialize() is re-invoked per
      // test (the singleton is shared across the test process).
      GoogleAuth.resetInitializationForTest();
    });

    test('fetchIdToken calls initialize() + authenticate() and returns idToken',
        () async {
      final googleAuth = GoogleAuth(clientId: 'web-client-id');
      final token = await googleAuth.fetchIdToken();
      expect(token, 'real-7x-id-token');
      expect(fakePlatform.authenticateCalls, 1,
          reason: 'must call the 7.x authenticate() API, not signIn()');
      expect(fakePlatform.initCalls, 1,
          reason: 'initialize() must run exactly once before authenticate()');
      expect(fakePlatform.lastScopeHint, contains('email'));
    });

    test('canceled authenticate() (GoogleSignInException.canceled) maps to null',
        () async {
      fakePlatform.exceptionToThrow = const GoogleSignInException(
        code: GoogleSignInExceptionCode.canceled,
      );
      final googleAuth = GoogleAuth(clientId: 'web-client-id');
      final token = await googleAuth.fetchIdToken();
      expect(token, isNull,
          reason: 'a dismissed popup must read as null, never throw');
      expect(fakePlatform.authenticateCalls, 1);
    });

    test('non-web GoogleAuth with no clientId still runs the flow (mobile '
        'fallback, clientId absent is allowed off-web)', () async {
      final googleAuth = GoogleAuth(); // no clientId, non-web test VM
      final token = await googleAuth.fetchIdToken();
      expect(token, 'real-7x-id-token');
      expect(fakePlatform.authenticateCalls, 1);
    });
  });
}

/// Fake [GoogleSignInPlatform] that records initialize()/authenticate() calls
/// and optionally returns a token or throws, so the real [GoogleAuth] seam can
/// be driven without a browser or the GSI script.
class _FakeGsPlatform extends GoogleSignInPlatform {
  _FakeGsPlatform() : super();

  int initCalls = 0;
  int authenticateCalls = 0;
  List<String>? lastScopeHint;
  String? idTokenToReturn;
  GoogleSignInException? exceptionToThrow;

  @override
  Future<void> init(InitParameters params) async {
    initCalls++;
  }

  @override
  Future<AuthenticationResults> authenticate(AuthenticateParameters params) async {
    authenticateCalls++;
    lastScopeHint = params.scopeHint;
    if (exceptionToThrow != null) throw exceptionToThrow!;
    return AuthenticationResults(
      user: const GoogleSignInUserData(email: 'seam@g.com', id: 'seam-1'),
      authenticationTokens: AuthenticationTokenData(idToken: idTokenToReturn),
    );
  }

  @override
  bool supportsAuthenticate() => true;

  @override
  bool authorizationRequiresUserInteraction() => false;

  @override
  Future<AuthenticationResults?>? attemptLightweightAuthentication(
    AttemptLightweightAuthenticationParameters params,
  ) =>
      null;

  @override
  Future<ClientAuthorizationTokenData?> clientAuthorizationTokensForScopes(
    ClientAuthorizationTokensForScopesParameters params,
  ) async =>
      null;

  @override
  Future<ServerAuthorizationTokenData?> serverAuthorizationTokensForScopes(
    ServerAuthorizationTokensForScopesParameters params,
  ) async =>
      null;

  @override
  Future<void> disconnect(DisconnectParams params) async {}

  @override
  Future<void> signOut(SignOutParams params) async {}
}
