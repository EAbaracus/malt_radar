import 'package:flutter/material.dart';
import '../theme/app_theme_colors.dart';

enum MedallionLevel { master, icon, micro }

/// Marka amblemi — "7 eksenli ölçüm"ün sabit sembolü. ETİKETSİZDİR;
/// canonical eksen isimleri yalnızca app içindeki gerçek radar chart'ta gösterilir.
class MedallionPainter extends CustomPainter {
  MedallionPainter({
    required this.palette,
    this.level = MedallionLevel.master,
    this.needleRotation = 0.0, // radyan; animasyonlu sweep Task 6'da set edilir
  });

  final MedallionPalette palette;
  final MedallionLevel level;
  final double needleRotation;

  // Dış 7-gen köşeleri (200x200 viewBox), marka dokümanından.
  static const List<Offset> outer7 = [
    Offset(100, 30), Offset(154.73, 56.35), Offset(168.26, 115.57),
    Offset(130.37, 163.07), Offset(69.63, 163.07),
    Offset(31.74, 115.57), Offset(45.27, 56.35),
  ];
  static const List<Offset> mid7 = [
    Offset(100, 45), Offset(143.0, 65.71), Offset(153.64, 112.24),
    Offset(123.86, 149.56), Offset(76.14, 149.56),
    Offset(46.36, 112.24), Offset(57.0, 65.71),
  ];
  static const List<Offset> inner7 = [
    Offset(100, 60), Offset(131.27, 75.06), Offset(139.01, 108.90),
    Offset(117.36, 136.04), Offset(82.64, 136.04),
    Offset(60.99, 108.90), Offset(68.73, 75.06),
  ];

  bool get _showInnerRings => level == MedallionLevel.master;
  bool get _showOuterRim => level != MedallionLevel.micro;
  bool get _showDots => level != MedallionLevel.micro;
  double get _webStroke => level == MedallionLevel.micro ? 2.0 : 1.3;
  double get _needleStroke => level == MedallionLevel.micro ? 2.2 : 1.6;

  @override
  void paint(Canvas canvas, Size size) {
    // viewBox 200x200 -> size scale
    final s = size.shortestSide / 200.0;
    canvas.scale(s);
    final center = const Offset(100, 100);

    final webPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _webStroke
      ..color = palette.web;

    if (_showOuterRim) {
      final rimPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6
        ..color = palette.rim;
      canvas.drawCircle(center, 95, rimPaint);
      if (_showInnerRings) {
        final innerRim = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.6
          ..color = palette.rim.withValues(alpha: 0.55);
        canvas.drawCircle(center, 88, innerRim);
      }
    }

    final path = Path()..moveTo(outer7[0].dx, outer7[0].dy);
    for (var i = 1; i < outer7.length; i++) {
      path.lineTo(outer7[i].dx, outer7[i].dy);
    }
    path.close();
    canvas.drawPath(path, webPaint);

    if (_showInnerRings) {
      canvas.drawPath(_poly(mid7), Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.6
        ..color = palette.web.withValues(alpha: 0.5));
      canvas.drawPath(_poly(inner7), Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.6
        ..color = palette.web.withValues(alpha: 0.35));
    }

    if (_showDots) {
      final dotPaint = Paint()..color = palette.dot;
      for (final p in outer7) {
        canvas.drawCircle(p, 2.4, dotPaint);
      }
    }

    // İbre (pivot (100,100))
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(needleRotation);
    final needlePaint = Paint()
      ..strokeWidth = _needleStroke
      ..strokeCap = StrokeCap.round
      ..color = palette.needle;
    canvas.drawLine(const Offset(0, 0), const Offset(0, -66), needlePaint);
    canvas.drawCircle(Offset.zero, 3.4, Paint()..color = palette.needle);
    canvas.restore();
  }

  Path _poly(List<Offset> pts) {
    final p = Path()..moveTo(pts[0].dx, pts[0].dy);
    for (var i = 1; i < pts.length; i++) {
      p.lineTo(pts[i].dx, pts[i].dy);
    }
    return p..close();
  }

  @override
  bool shouldRepaint(covariant MedallionPainter oldDelegate) =>
      oldDelegate.palette != palette ||
      oldDelegate.level != level ||
      oldDelegate.needleRotation != needleRotation;
}
