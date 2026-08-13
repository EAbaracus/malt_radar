// Widget tests for AuthScreen (login/register form).
//
// Patterns follow guest_mode_navigation_test.dart (pump AuthScreen inside
// ProviderScope) and auth_controller_test.dart (FakeAuthApi + in-memory Drift).
// These tests lock the form's BEHAVIOR (validation, mode toggle, busy state,
// gating) so the design pass can refactor visuals without breaking it.

import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/config/feature_flags.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';
import 'package:malt_radar/features/compliance/presentation/age_gate_providers.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

/// Records every auth call so tests can assert WHAT was submitted and HOW
/// many times — without touching the network.
class SpyAuthApi extends AuthApi {
  int loginCalls = 0;
  int registerCalls = 0;
  String? lastLoginEmail;
  String? lastLoginPassword;
  String? lastRegEmail;
  String? lastRegCountry;
  int? lastRegMinAge;
  bool? lastRegConsent;
  Duration? loginDelay;

  static Map<String, dynamic> _user() => {
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
    loginCalls++;
    lastLoginEmail = email;
    lastLoginPassword = password;
    if (loginDelay != null) await Future<void>.delayed(loginDelay!);
    if (email.trim() != 'user@example.com' || password != 's3curePass') {
      throw AuthApiException('Invalid email or password');
    }
    return {'token': 'tok-1', 'user': _user()};
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
    registerCalls++;
    lastRegEmail = email;
    lastRegCountry = ageCountry;
    lastRegMinAge = ageMin;
    lastRegConsent = privacyConsent;
    return {'token': 'tok-2', 'user': _user()};
  }

  @override
  Future<Map<String, dynamic>> signInWithGoogle(String idToken) async {
    throw AuthApiException('not used in these tests');
  }

  @override
  Future<void> logout(String token) async {}
}

Future<AppDatabase> makeDb() async {
  final db = AppDatabase.forTesting(NativeDatabase.memory());
  addTearDown(() => db.close());
  return db;
}

/// Builds the screen inside a ProviderScope with the fake API + in-memory DB.
Future<ProviderContainer> pumpAuthScreen(
  WidgetTester tester, {
  required AppDatabase db,
  required SpyAuthApi api,
  bool googleEnabled = false,
}) async {
  final container = ProviderContainer(
    overrides: [
      appDatabaseProvider.overrideWithValue(db),
      authApiProvider.overrideWithValue(api),
      googleSignInEnabledProvider.overrideWithValue(googleEnabled),
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

/// Dismisses the SnackBar so no timer is left pending at test end.
Future<void> drainSnackBar(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 5));
  await tester.pumpAndSettle();
}

Future<void> fillLogin(
  WidgetTester tester, {
  String email = 'user@example.com',
  String password = 's3curePass',
}) async {
  await tester.enterText(find.byType(TextField).at(0), email);
  await tester.enterText(find.byType(TextField).at(1), password);
}

Future<void> switchToRegister(WidgetTester tester) async {
  await tester.tap(find.text("Don't have an account? Sign up"));
  await tester.pumpAndSettle();
}

Future<void> checkConsents(WidgetTester tester) async {
  final boxes = find.byType(Checkbox);
  expect(boxes, findsNWidgets(2));
  await tester.tap(boxes.at(0));
  await tester.tap(boxes.at(1));
  await tester.pump();
}

void main() {
  testWidgets('empty login fields show toast and never call the API', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    await tester.tap(find.text('SIGN IN'));
    await tester.pump();

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('Please fill in all fields'), findsOneWidget);
    expect(api.loginCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('valid login submits email and password to the controller', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    await fillLogin(tester);
    await tester.tap(find.text('SIGN IN'));
    await tester.pumpAndSettle();

    // The screen owns the submit path; the controller-level session
    // persistence is covered by auth_controller_test.dart. The screen's
    // `ref.invalidate(authControllerProvider)` races async _restore(), so
    // assert only what this widget is responsible for.
    expect(api.loginCalls, 1);
    expect(api.lastLoginEmail, 'user@example.com');
    expect(api.lastLoginPassword, 's3curePass');
  });

  testWidgets('register rejects password shorter than 8 chars', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    await switchToRegister(tester);
    await tester.enterText(find.byType(TextField).at(1), 'user@example.com');
    await tester.enterText(find.byType(TextField).at(2), 'short');
    await tester.enterText(find.byType(TextField).at(3), 'short');
    await checkConsents(tester);
    await tester.tap(find.text('SIGN UP'));
    await tester.pump();

    expect(find.text('Password must be at least 8 characters'), findsOneWidget);
    expect(api.registerCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('register rejects mismatched passwords', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    await switchToRegister(tester);
    await tester.enterText(find.byType(TextField).at(1), 'user@example.com');
    await tester.enterText(find.byType(TextField).at(2), 'password123');
    await tester.enterText(find.byType(TextField).at(3), 'different123');
    await checkConsents(tester);
    await tester.tap(find.text('SIGN UP'));
    await tester.pump();

    expect(find.text('Passwords do not match'), findsOneWidget);
    expect(api.registerCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('register requires both consent boxes', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    await switchToRegister(tester);
    await tester.enterText(find.byType(TextField).at(1), 'user@example.com');
    await tester.enterText(find.byType(TextField).at(2), 'password123');
    await tester.enterText(find.byType(TextField).at(3), 'password123');
    await tester.tap(find.text('SIGN UP'));
    await tester.pump();

    expect(
      find.text('Please accept the consent boxes to continue'),
      findsOneWidget,
    );
    expect(api.registerCalls, 0);
    await drainSnackBar(tester);
  });

  testWidgets('mode toggle shows register-only fields and hides them back', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    // Login mode: email + password only, no consents.
    expect(find.byType(TextField), findsNWidgets(2));
    expect(find.byType(Checkbox), findsNothing);

    await switchToRegister(tester);
    // Register: display name + email + password + confirm.
    expect(find.byType(TextField), findsNWidgets(4));
    expect(find.byType(Checkbox), findsNWidgets(2));
    expect(find.text('SIGN UP'), findsOneWidget);

    await tester.tap(find.text('Already have an account? Sign in'));
    await tester.pumpAndSettle();
    expect(find.byType(TextField), findsNWidgets(2));
    expect(find.byType(Checkbox), findsNothing);
    expect(find.text('SIGN IN'), findsOneWidget);
  });

  testWidgets('submit disables the button and shows spinner while busy', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi()..loginDelay = const Duration(milliseconds: 300);
    await pumpAuthScreen(tester, db: db, api: api);

    await fillLogin(tester);
    await tester.tap(find.text('SIGN IN'));
    await tester.pump(); // start submit -> busy

    final button = tester.widget<ElevatedButton>(find.byType(ElevatedButton));
    expect(button.onPressed, isNull); // disabled while busy

    await tester.pumpAndSettle();
    final after = tester.widget<ElevatedButton>(find.byType(ElevatedButton));
    expect(after.onPressed, isNotNull);
  });

  testWidgets('google sign-in is hidden by default and shown when enabled', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();

    await pumpAuthScreen(tester, db: db, api: SpyAuthApi());
    expect(find.text('Continue with Google'), findsNothing);
    expect(find.text('or'), findsNothing);

    await pumpAuthScreen(
      tester,
      db: await makeDb(),
      api: SpyAuthApi(),
      googleEnabled: true,
    );
    expect(find.text('Continue with Google'), findsOneWidget);
    expect(find.text('or'), findsOneWidget);
  });

  testWidgets('guest button flips guestModeProvider to true', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    final container = await pumpAuthScreen(tester, db: db, api: api);

    expect(container.read(guestModeProvider), isFalse);
    await tester.tap(find.text('Explore as Guest'));
    await tester.pump();
    expect(container.read(guestModeProvider), isTrue);
  });

  testWidgets('register forwards persisted age-gate country and minAge', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    // Seed the age gate exactly like AgeGateNotifier.consent() would.
    await db
        .into(db.userSettings)
        .insertOnConflictUpdate(
          UserSettingsCompanion.insert(key: 'age_gate', value: 'TR|19'),
        );
    final api = SpyAuthApi();
    final container = await pumpAuthScreen(tester, db: db, api: api);

    // Mirror production: main.dart watches ageGateProvider at startup, so by
    // the time the user reaches this screen the decision is already loaded.
    // Trigger creation + settle here so the lazy provider race can't bite.
    container.read(ageGateProvider);
    await tester.pumpAndSettle();

    await switchToRegister(tester);
    await tester.enterText(find.byType(TextField).at(1), 'user@example.com');
    await tester.enterText(find.byType(TextField).at(2), 'password123');
    await tester.enterText(find.byType(TextField).at(3), 'password123');
    await checkConsents(tester);
    await tester.tap(find.text('SIGN UP'));
    await tester.pumpAndSettle();

    expect(api.registerCalls, 1);
    expect(api.lastRegCountry, 'TR');
    expect(api.lastRegMinAge, 19);
    expect(api.lastRegConsent, isTrue);
  });

  testWidgets('malformed email shows toast and never calls the API', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    final db = await makeDb();
    final api = SpyAuthApi();
    await pumpAuthScreen(tester, db: db, api: api);

    await fillLogin(tester, email: 'not-an-email', password: 's3curePass');
    await tester.tap(find.text('SIGN IN'));
    await tester.pump();

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text('Please enter a valid email'), findsOneWidget);
    expect(api.loginCalls, 0);
    await drainSnackBar(tester);
  });
}
