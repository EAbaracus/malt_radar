// Basic Flutter widget test — Malt Radar App smoke test.
//
// Verifies that the app boots and renders a MaterialApp without crashing or
// timing out. Uses bounded pump() calls (not pumpAndSettle()) so that async
// font loading from GoogleFonts and any other background network operations
// cannot block the frame loop.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:drift/native.dart';

import 'package:malt_radar/main.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/lists/presentation/controllers/user_lists_providers.dart';

void main() {
  // Disable GoogleFonts runtime font fetching so the test never hangs on
  // async font downloads. In CI the runner has network access, which would
  // otherwise leave pumpAndSettle() (and even bounded pump frames if fonts
  // are slow) in an indeterminate waiting state.
  GoogleFonts.config.allowRuntimeFetching = false;

  testWidgets('Malt Radar App smoke test', (WidgetTester tester) async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());

    // Simulate a user who already passed the age gate so the smoke test keeps
    // exercising the post-gate flow (MainNavigationScreen) as before the gate
    // was introduced. The gate itself is covered by age_gate_test.dart.
    await db
        .into(db.userSettings)
        .insertOnConflictUpdate(
          UserSettingsCompanion.insert(key: 'age_gate', value: 'US|21'),
        );

    // Build the full app inside a ProviderScope with stable overrides for
    // every provider the IndexedStack builds at once (Home / Lists / Settings
    // tabs are all rendered by MainNavigationScreen).
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          // Core database — in-memory test instance
          appDatabaseProvider.overrideWithValue(db),

          // App init — skip the real seed (2986 rows) → resolves immediately
          appInitializationProvider.overrideWith((ref) => Future<void>.value()),

          // Settings  — pretend reference-whisky is configured so the app
          //             navigates to MainNavigationScreen (not SetupScreen)
          referenceSettingsStreamProvider.overrideWith(
            (ref) => Stream.value({'reference_whisky_id': 1}),
          ),

          // Whiskies  — empty list, avoids real DB queries
          whiskiesStreamProvider.overrideWith((ref) => Stream.value([])),

          // Lists tab — empty lists, avoids real Drift db.watch() stream
          watchUserListsProvider.overrideWith((ref) => Stream.value([])),

          // Settings tab — no reference whisky model
          referenceWhiskyModelProvider.overrideWith(
            (ref) => Stream.value(null),
          ),
        ],
        child: const MaltRadarApp(),
      ),
    );

    // Pump a handful of bounded frames so the widget tree reaches a steady
    // state.  We deliberately avoid pumpAndSettle() because even with
    // GoogleFonts fetch disabled, Flutter's internal tickers or other
    // async lifecycle hooks can leave the frame loop unsettled on CI.
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 100));

    // The app boots by rendering a MaterialApp — this is the smoke assertion.
    expect(find.byType(MaterialApp), findsOneWidget);

    // Tear down the widget so the test DB can close cleanly.
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
