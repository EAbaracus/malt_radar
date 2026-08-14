// Golden render tests — REAL rendered pixels (Flutter render pipeline) for
// the login/register screen. Catches horizontal overflow (throws), text
// clipping, glow/shadow rendering — the things widget-behavior tests cannot.
//
// Usage:
//   flutter test --no-pub --update-goldens test/features/auth/auth_screen_golden_test.dart  (generate)
//   flutter test --no-pub test/features/auth/auth_screen_golden_test.dart                   (verify)
//
// The BEFORE/AFTER pair is produced by generating once against HEAD (git
// stash) and once against the working tree — same test, same pump, same
// viewports. Goldens live in test/features/auth/goldens/.

import 'dart:io' show Platform;

import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart' show FontLoader, rootBundle;

import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/config/feature_flags.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

class _NoopAuthApi extends AuthApi {
  @override
  Future<Map<String, dynamic>> login(String email, String password) async =>
      throw UnimplementedError('golden test never submits successfully');
  @override
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? displayName,
    required String ageCountry,
    required int ageMin,
    required bool privacyConsent,
  }) async =>
      throw UnimplementedError('golden test never submits successfully');
  @override
  Future<Map<String, dynamic>> signInWithGoogle(String idToken) async =>
      throw UnimplementedError();
  @override
  Future<void> logout(String token) async {}
}

/// Loads the bundled brand fonts so goldens render REAL glyphs, not the Ahem
/// placeholder blocks. Mirrors the app's offline bundle (4 families).
Future<void> _loadFonts() async {
  Future<void> load(String family, String asset) async {
    final loader = FontLoader(family)..addFont(rootBundle.load(asset));
    await loader.load();
  }

  await load('Fraunces', 'assets/fonts/Fraunces.ttf');
  await load('SourceSerif4', 'assets/fonts/SourceSerif4.ttf');
  await load('Inter', 'assets/fonts/Inter.ttf');
  await load('CourierPrime', 'assets/fonts/CourierPrime-Regular.ttf');
}

Future<AppDatabase> _makeDb() async {
  final db = AppDatabase.forTesting(NativeDatabase.memory());
  addTearDown(() => db.close());
  return db;
}

Future<void> _pumpAuth(WidgetTester tester,
    {AuthMode mode = AuthMode.login}) async {
  final db = await _makeDb();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        appDatabaseProvider.overrideWithValue(db),
        authApiProvider.overrideWithValue(_NoopAuthApi()),
        googleSignInEnabledProvider.overrideWithValue(false),
      ],
      child: MaterialApp(home: AuthScreen(initialMode: mode)),
    ),
  );
  await tester.pumpAndSettle();
}

/// Auth goldens are Linux-CI truth (issue #81): real-font rasterization
/// (fontconfig vs DirectWrite) drifts cross-platform, and flutter_test's
/// golden comparator is exact. On non-Linux hosts the comparison would
/// produce a false failure — skip it there. Regenerate with
/// `flutter test --update-goldens` on the CI runner (Linux).
final bool _skipGolden = !Platform.isLinux;

Future<void> _setViewport(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

void main() {
  setUpAll(_loadFonts);

  testWidgets('login renders at 390x844 (mobile)', skip: _skipGolden,
      (tester) async {
    await _setViewport(tester, const Size(390, 844));
    await _pumpAuth(tester);
    await expectLater(
      find.byType(AuthScreen),
      matchesGoldenFile('goldens/auth_login_390.png'),
    );
  });

  testWidgets('register renders at 390x844 (mobile)', skip: _skipGolden,
      (tester) async {
    await _setViewport(tester, const Size(390, 844));
    await _pumpAuth(tester, mode: AuthMode.register);
    await expectLater(
      find.byType(AuthScreen),
      matchesGoldenFile('goldens/auth_register_390.png'),
    );
  });

  testWidgets('login renders at 1280x800 (web/desktop)', skip: _skipGolden,
      (tester) async {
    await _setViewport(tester, const Size(1280, 800));
    await _pumpAuth(tester);
    await expectLater(
      find.byType(AuthScreen),
      matchesGoldenFile('goldens/auth_login_1280.png'),
    );
  });

  testWidgets('empty submit shows error SnackBar at 390x844',
      skip: _skipGolden, (tester) async {
    await _setViewport(tester, const Size(390, 844));
    await _pumpAuth(tester);

    await tester.tap(find.text('SIGN IN'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300)); // SnackBar entrance
    await expectLater(
      find.byType(AuthScreen),
      matchesGoldenFile('goldens/auth_error_390.png'),
    );
    // Drain the SnackBar timer so no pending Timer fails the test.
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();
  });
}
