// Widget tests for the "Continue with Google" button.
//
// Covers both layers:
//  * GoogleSignInButton in isolation (pure widget — no controller / plugin
//    binding needed thanks to the injected onPressed callback + isLoading).
//  * AuthScreen integration: the real button triggers
//    AuthController.signInWithGoogle through a FakeGoogleAuth seam, and the
//    success / error paths are reflected in session state + the SnackBar.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';

import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/data/google_auth.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';
import 'package:malt_radar/features/auth/presentation/google_sign_in_button.dart';

// Reuse the controller test fakes (FakeAuthApi, FakeGoogleAuth).
import 'auth_controller_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GoogleSignInButton (isolated)', () {
    testWidgets('fires onPressed when tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GoogleSignInButton(
              label: 'Continue with Google',
              isLoading: false,
              onPressed: () => tapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('google-sign-in-button')));
      await tester.pump();
      expect(tapped, isTrue);
    });

    testWidgets('is disabled and shows spinner while loading', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GoogleSignInButton(
              label: 'Continue with Google',
              isLoading: true,
              onPressed: () => tapped = true,
            ),
          ),
        ),
      );

      final button = tester.widget<OutlinedButton>(
        find.byKey(const Key('google-sign-in-button')),
      );
      expect(button.onPressed, isNull, reason: 'button must be disabled');
      expect(find.byType(BrandSpinner), findsOneWidget,
          reason: 'spinner shown while loading');

      // A disabled button never invokes the callback.
      await tester.tap(find.byKey(const Key('google-sign-in-button')),
          warnIfMissed: false);
      await tester.pump();
      expect(tapped, isFalse);
    });

    testWidgets('renders the supplied label text', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GoogleSignInButton(
              label: 'Google ile devam et',
              isLoading: false,
              onPressed: () {},
            ),
          ),
        ),
      );
      expect(find.text('Google ile devam et'), findsOneWidget);
    });
  });

  group('AuthScreen Google sign-in (integration)', () {
    Future<ProviderContainer> pumpAuthScreen(
      WidgetTester tester, {
      required GoogleAuth googleAuth,
    }) async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      addTearDown(db.close);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            appDatabaseProvider.overrideWithValue(db),
            authApiProvider.overrideWithValue(FakeAuthApi()),
            googleAuthProvider.overrideWithValue(googleAuth),
          ],
          child: const MaterialApp(home: AuthScreen()),
        ),
      );
      await tester.pumpAndSettle();
      // Return the live container so the test can assert on session state.
      final ctx = tester.element(find.byType(AuthScreen));
      return ProviderScope.containerOf(ctx);
    }

    testWidgets('shows the button and logs in on tap (success)',
        (tester) async {
      final googleAuth = FakeGoogleAuth(idToken: 'good-google-token');
      final container =
          await pumpAuthScreen(tester, googleAuth: googleAuth);

      // Locale-independent: the button is present and its label mentions Google.
      final btn = tester.widget<GoogleSignInButton>(
        find.byType(GoogleSignInButton),
      );
      expect(btn.label, contains('Google'));
      expect(container.read(authControllerProvider).isLoggedIn, isFalse);

      await tester.tap(find.byKey(const Key('google-sign-in-button')));
      await tester.pumpAndSettle();

      final state = container.read(authControllerProvider);
      expect(state.isLoggedIn, isTrue);
      expect(state.user?.email, 'user@example.com');
      expect(googleAuth.fetchIdTokenCallCount, 1);
    });

    testWidgets('shows error SnackBar when the flow is dismissed',
        (tester) async {
      final googleAuth = FakeGoogleAuth(idToken: null);
      final container =
          await pumpAuthScreen(tester, googleAuth: googleAuth);

      await tester.tap(find.byKey(const Key('google-sign-in-button')));
      // One frame is enough for the SnackBar to appear.
      await tester.pump();

      expect(find.text('Popup kapatıldı. Tekrar deneyin.'), findsOneWidget);
      expect(container.read(authControllerProvider).isLoggedIn, isFalse);
    });

    testWidgets('shows error SnackBar on backend rejection', (tester) async {
      final googleAuth = FakeGoogleAuth(idToken: 'expired-token');
      final container =
          await pumpAuthScreen(tester, googleAuth: googleAuth);

      await tester.tap(find.byKey(const Key('google-sign-in-button')));
      await tester.pump();

      expect(
        find.text('Gecersiz Google kimlik dogrulamasi'),
        findsOneWidget,
      );
      expect(container.read(authControllerProvider).isLoggedIn, isFalse);
    });
  });
}
