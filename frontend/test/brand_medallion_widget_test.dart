import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  testWidgets('animate:false default — statik, pumpAndSettle güvenli', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Medallion(size: 60, level: MedallionLevel.master, palette: kMasterDarkPalette),
    ));
    await tester.pumpAndSettle(); // ticker yok → takılmaz
    expect(find.byType(Medallion), findsOneWidget);
  });

  testWidgets('animate:true — tek sefer sweep COMPLETED, döngü yok', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: SizedBox(
        width: 200,
        height: 200,
        child: Medallion(
            size: 200, level: MedallionLevel.master, palette: kMasterDarkPalette, animate: true),
      ),
    ));
    await tester.pumpAndSettle(const Duration(milliseconds: 3000));
    expect(find.byType(Medallion), findsOneWidget);
  });

  testWidgets('reduced-motion — animasyon kapalı', (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    await tester.pumpWidget(const MaterialApp(
      home: Medallion(size: 100, animate: true, palette: kMasterDarkPalette),
    ));
    await tester.pumpAndSettle();
    expect(find.byType(Medallion), findsOneWidget);
  });
}
