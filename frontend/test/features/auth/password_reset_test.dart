// Widget tests for the password-reset flow (forgot -> reset) on AuthScreen.
//
// Harness mirrors auth_screen_test.dart: ProviderScope + SpyAuthApi (no
// network) + in-memory Drift. The tests lock the STEP ORDER (login -> forgot ->
// reset -> login), the client-side validation, and that a successful reset
// drops the local session (server kills all sessions, so a stale token would
// leave the app "logged in" with a dead credential).

import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/config/feature_flags.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

class SpyResetApi extends AuthApi {
  int forgotCalls = 0;
  int resetCalls = 0;
  String? lastForgotEmail;
  String? lastResetEmail;
  String? lastResetCode;
  String? lastResetPassword;
  bool failForgot = false;
  bool failReset = false;
  String resetError = 'Invalid or expired reset code';

  @override
  Future<void> forgotPassword(String email) async {
    forgotCalls++;
    lastForgotEmail = email;
    if (failForgot) throw AuthApiException('Sunucuya bağlanılamadı');
  }

  @override
  Future<void> resetPassword({
    required String email,
    required String code,
    required String newPassword,
  }) async {
    resetCalls++;
    lastResetEmail = email;
    lastResetCode = code;
    lastResetPassword = newPassword;
    if (failReset) throw AuthApiException(resetError);
  }

  @override
  Future<Map<String, dynamic>> login(String email, String password) async {
    throw AuthApiException('not used here');
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
    throw AuthApiException('not used here');
  }

  @override
  Future<Map<String, dynamic>> signInWithGoogle(String idToken) async {
    throw AuthApiException('not used here');
  }

  @override
  Future<void> logout(String token) async {}
}

Future<AppDatabase> makeDb() async {
  final db = AppDatabase.forTesting(NativeDatabase.memory());
  addTearDown(() => db.close());
  return db;
}

Future<ProviderContainer> pumpScreen(
  WidgetTester tester, {
  required AppDatabase db,
  required SpyResetApi api,
}) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  final container = ProviderContainer(
    overrides: [
      appDatabaseProvider.overrideWithValue(db),
      authApiProvider.overrideWithValue(api),
      googleSignInEnabledProvider.overrideWithValue(false),
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: AuthScreen()),
    ),
  );
  await tester.pumpAndSettle();
  return container;
}

Future<void> drainSnackBar(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 5));
  await tester.pumpAndSettle();
}

/// login -> forgot (the entry point lives under the password field).
Future<void> goToForgot(WidgetTester tester) async {
  await tester.tap(find.text('Forgot password?'));
  await tester.pumpAndSettle();
}

/// forgot -> reset by submitting an email and receiving a code.
///
/// Drains the "code sent" SnackBar: while one SnackBar is visible the next is
/// QUEUED, so a later validation toast would never appear and the assertion
/// would fail for the wrong reason.
Future<void> requestCode(
  WidgetTester tester, {
  String email = 'user@example.com',
  bool drainSnack = true,
}) async {
  await tester.enterText(find.byType(TextField).at(0), email);
  await tester.tap(find.text('SEND CODE'));
  await tester.pumpAndSettle();
  if (drainSnack) await drainSnackBar(tester);
}

void main() {
  testWidgets('login offers a forgot-password entry point', (tester) async {
    final db = await makeDb();
    await pumpScreen(tester, db: db, api: SpyResetApi());

    expect(find.text('Forgot password?'), findsOneWidget);
    // Password field present on login.
    expect(find.byType(TextField), findsNWidgets(2));

    await goToForgot(tester);
    expect(find.text('Forgot password'), findsOneWidget);
    // The code request needs no password: only the email field remains.
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('an invalid email never reaches the API', (tester) async {
    final db = await makeDb();
    final api = SpyResetApi();
    await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);

    await tester.enterText(find.byType(TextField).at(0), 'not-an-email');
    await tester.tap(find.text('SEND CODE'));
    await tester.pump();

    expect(find.text('Please enter a valid email'), findsOneWidget);
    expect(api.forgotCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('requesting a code calls the API once and moves to the code step', (
    tester,
  ) async {
    final db = await makeDb();
    final api = SpyResetApi();
    await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);

    await requestCode(tester);

    expect(api.forgotCalls, 1);
    expect(api.lastForgotEmail, 'user@example.com');
    // 'New password' is ambiguous — it is both the headline and the password
    // field label — so assert on the step's button instead.
    expect(find.text('CHANGE PASSWORD'), findsOneWidget);
    // email + code + new password + confirm
    expect(find.byType(TextField), findsNWidgets(4));
    await drainSnackBar(tester);
  });

  testWidgets('a short code is rejected client-side', (tester) async {
    final db = await makeDb();
    final api = SpyResetApi();
    await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);
    await requestCode(tester);

    await tester.enterText(find.byType(TextField).at(1), '12345');
    await tester.enterText(find.byType(TextField).at(2), 'newPassw0rd');
    await tester.enterText(find.byType(TextField).at(3), 'newPassw0rd');
    await tester.tap(find.text('CHANGE PASSWORD'));
    await tester.pump();

    expect(find.text('Enter the 6-digit code'), findsOneWidget);
    expect(api.resetCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('mismatched passwords are rejected client-side', (tester) async {
    final db = await makeDb();
    final api = SpyResetApi();
    await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);
    await requestCode(tester);

    await tester.enterText(find.byType(TextField).at(1), '123456');
    await tester.enterText(find.byType(TextField).at(2), 'newPassw0rd');
    await tester.enterText(find.byType(TextField).at(3), 'differentPass');
    await tester.tap(find.text('CHANGE PASSWORD'));
    await tester.pump();

    expect(find.text('Passwords do not match'), findsOneWidget);
    expect(api.resetCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('a successful reset clears the local session and returns to login', (
    tester,
  ) async {
    final db = await makeDb();
    final api = SpyResetApi();
    final container = await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);
    await requestCode(tester);

    await tester.enterText(find.byType(TextField).at(1), '123456');
    await tester.enterText(find.byType(TextField).at(2), 'newPassw0rd');
    await tester.enterText(find.byType(TextField).at(3), 'newPassw0rd');
    await tester.tap(find.text('CHANGE PASSWORD'));
    await tester.pumpAndSettle();

    expect(api.resetCalls, 1);
    expect(api.lastResetEmail, 'user@example.com');
    expect(api.lastResetCode, '123456');
    expect(api.lastResetPassword, 'newPassw0rd');

    // Server killed every session; the client must not look logged in.
    expect(container.read(authControllerProvider).status, AuthStatus.loggedOut);
    expect(await container.read(authRepositoryProvider).loadToken(), isNull);

    // Back on the sign-in step for the new password.
    expect(find.text('Sign in'), findsOneWidget);
    await drainSnackBar(tester);
  });

  testWidgets('a backend rejection keeps the user on the code step', (
    tester,
  ) async {
    final db = await makeDb();
    final api = SpyResetApi()..failReset = true;
    await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);
    await requestCode(tester);

    await tester.enterText(find.byType(TextField).at(1), '999999');
    await tester.enterText(find.byType(TextField).at(2), 'newPassw0rd');
    await tester.enterText(find.byType(TextField).at(3), 'newPassw0rd');
    await tester.tap(find.text('CHANGE PASSWORD'));
    await tester.pumpAndSettle();

    expect(api.resetCalls, 1);
    expect(find.text('Invalid or expired reset code'), findsOneWidget);
    // Still on the code step so the user can retry.
    expect(find.text('CHANGE PASSWORD'), findsOneWidget);
    await drainSnackBar(tester);
  });

  testWidgets('a failed code request reports the error and stays put', (
    tester,
  ) async {
    final db = await makeDb();
    final api = SpyResetApi()..failForgot = true;
    await pumpScreen(tester, db: db, api: api);
    await goToForgot(tester);
    // Keep the SnackBar on screen: this test asserts on the error itself.
    await requestCode(tester, drainSnack: false);

    expect(api.forgotCalls, 1);
    expect(find.text('Sunucuya bağlanılamadı'), findsOneWidget);
    expect(find.text('Forgot password'), findsOneWidget);
    await drainSnackBar(tester);
  });

  testWidgets('the reset flow can be abandoned via Back to sign in', (
    tester,
  ) async {
    final db = await makeDb();
    await pumpScreen(tester, db: db, api: SpyResetApi());
    await goToForgot(tester);

    expect(find.text('Back to sign in'), findsOneWidget);
    await tester.tap(find.text('Back to sign in'));
    await tester.pumpAndSettle();

    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('Forgot password?'), findsOneWidget);
  });
}