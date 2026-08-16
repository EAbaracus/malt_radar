// Widget tests for the compliance age gate (Malt Radar / Turkey-alcohol work).
//
// Verifies the gate's three states:
//   1. Fresh install (no consent) → AgeGateScreen blocks content.
//   2. Confirm → consent persists and the user reaches MainNavigationScreen.
//   3. "I am underage" → AgeGateBlockedScreen locks the app.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';

import 'package:malt_radar/main.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/presentation/screens/main_navigation_screen.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';
import 'package:malt_radar/features/compliance/presentation/age_gate_screen.dart';
import 'package:malt_radar/features/compliance/presentation/age_gate_blocked_screen.dart';
import 'package:malt_radar/features/compliance/presentation/pre_gate_discovery_shell.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/lists/presentation/controllers/user_lists_providers.dart';

void main() {

  Future<AppDatabase> pumpApp(
    WidgetTester tester, {
    bool seedConsented = false,
  }) async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());

    if (seedConsented) {
      await db
          .into(db.userSettings)
          .insertOnConflictUpdate(
            UserSettingsCompanion.insert(key: 'age_gate', value: 'US|21'),
          );
    }

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appDatabaseProvider.overrideWithValue(db),
          appInitializationProvider.overrideWith((ref) => Future<void>.value()),
          referenceSettingsStreamProvider.overrideWith(
            (ref) => Stream.value({'reference_whisky_id': 1}),
          ),
          whiskiesStreamProvider.overrideWith((ref) => Stream.value([])),
          watchUserListsProvider.overrideWith((ref) => Stream.value([])),
          referenceWhiskyModelProvider.overrideWith(
            (ref) => Stream.value(null),
          ),
          // Seed the pre-gate discovery provider with test data so the shell
          // renders cards (each showing a lock_outline icon).
          preGateWhiskiesProvider.overrideWith(
            (ref) => Stream.value([
              PreGateWhisky(
                id: 1,
                name: 'Test Malt',
                country: 'Turkey',
                region: 'Istanbul',
                type: 'Single Malt',
                distillery: 'Test Distillery',
                age: 12,
              ),
            ]),
          ),
        ],
        child: const MaltRadarApp(),
      ),
    );
    await tester.pumpAndSettle();
    return db;
  }

  testWidgets('fresh install shows the age gate over a public preview shell', (
    tester,
  ) async {
    await pumpApp(tester);
    expect(find.byType(AgeGateScreen), findsOneWidget);
    expect(find.byType(MainNavigationScreen), findsNothing);
    // Brand header appears (in both the preview shell and the gate).
    expect(find.text('MALT RADAR'), findsWidgets);
    // Pre-gate public discovery shell must be present beneath the overlay.
    expect(find.byType(PreGateDiscoveryShell), findsOneWidget);
    // No age-gated product content (detail screens, scores) pre-consent.
    expect(find.byIcon(Icons.lock_outline), findsWidgets);
  });

  testWidgets('confirming the age gate persists consent and enters the app', (
    tester,
  ) async {
    final db = await pumpApp(tester);

    // Confirm checkbox then the (disabled until confirmed) Continue button.
    await tester.tap(find.byType(Checkbox));
    await tester.pump();
    await tester.ensureVisible(find.byType(ElevatedButton));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(ElevatedButton));
    await tester.pumpAndSettle();

    // Age gate passed; the app now requires login before the catalog (no
    // session in this test) -> the auth screen is shown, not the catalog yet.
    expect(find.byType(AuthScreen), findsOneWidget);
    expect(find.byType(AgeGateScreen), findsNothing);
    expect(find.byType(MainNavigationScreen), findsNothing);

    // Consent persisted for default selection (US, +21).
    final row = await (db.select(
      db.userSettings,
    )..where((t) => t.key.equals('age_gate'))).getSingleOrNull();
    expect(row?.value, 'US|21');
  });

  testWidgets('declaring underage locks the app', (tester) async {
    await pumpApp(tester);
    await tester.ensureVisible(find.byType(TextButton));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(TextButton));
    await tester.pumpAndSettle();
    expect(find.byType(AgeGateBlockedScreen), findsOneWidget);
    expect(find.byType(AgeGateScreen), findsNothing);
  });

  testWidgets('an already-consented install goes straight to auth (content is gated behind login)', (
    tester,
  ) async {
    await pumpApp(tester, seedConsented: true);
    // Age gate is skipped (consent present), but the catalog is now behind
    // login: no session in this test -> the auth screen is shown.
    expect(find.byType(AgeGateScreen), findsNothing);
    expect(find.byType(AuthScreen), findsOneWidget);
    expect(find.byType(MainNavigationScreen), findsNothing);
  });
}
