// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/main.dart';
import 'package:flutter/material.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

void main() {
  testWidgets('Malt Radar App smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appInitializationProvider.overrideWith((ref) => Future.value()),
          referenceSettingsStreamProvider.overrideWith((ref) => Stream.value({'reference_whisky_id': 1})),
          whiskiesStreamProvider.overrideWith((ref) => Stream.value([])),
        ],
        child: const MaltRadarApp(),
      ),
    );

    // Give the async providers a chance to emit their first value
    await tester.pump();
    await tester.pump();

    // Verify that the app boots and renders a MaterialApp.
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
