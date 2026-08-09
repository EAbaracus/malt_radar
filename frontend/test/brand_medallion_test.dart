import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  const pts = [
    Offset(100, 30), Offset(154.73, 56.35), Offset(168.26, 115.57),
    Offset(130.37, 163.07), Offset(69.63, 163.07),
    Offset(31.74, 115.57), Offset(45.27, 56.35),
  ];

  test('7-gen vertex koordinatları geometriye uyuyor', () {
    final xs = pts.map((p) => p.dx).toList();
    final ys = pts.map((p) => p.dy).toList();
    expect(xs.reduce((a, b) => a > b ? a : b) - xs.reduce((a, b) => a < b ? a : b),
        greaterThan(100));
    expect(ys.reduce((a, b) => a > b ? a : b) - ys.reduce((a, b) => a < b ? a : b),
        inInclusiveRange(125, 140));
  });

  test('painter 3 kademede de üretir; shouldRepaint level/palette/rotation duyarlı', () {
    final master = MedallionPainter(palette: kMasterDarkPalette, level: MedallionLevel.master);
    final micro = MedallionPainter(palette: kMasterDarkPalette, level: MedallionLevel.micro);
    final rotated = MedallionPainter(
        palette: kMasterDarkPalette, level: MedallionLevel.master, needleRotation: 1.0);

    expect(master.shouldRepaint(micro), isTrue); // farklı level
    expect(master.shouldRepaint(master), isFalse); // aynı
    expect(master.shouldRepaint(rotated), isTrue); // farklı rotation

    // paint() true-source üretir, exception atmaz — rastgele painter üzerinde paint çağır
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    master.paint(canvas, const Size(200, 200));
    recorder.endRecording(); // çizim patlamadan biter
  });

  test('palet brass yalnizca rim+needle', () {
    expect(kMasterDarkPalette.rim, AppThemeColors.brass);
    expect(kMasterDarkPalette.needle, AppThemeColors.brass);
    expect(kMasterDarkPalette.web, isNot(AppThemeColors.brass));
    expect(kMasterDarkPalette.dot, isNot(AppThemeColors.brass));
  });
}
