import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  test('marka paleti hex değerleri kilitli', () {
    expect(AppThemeColors.caskChar, const Color(0xFF1A120B));
    expect(AppThemeColors.parchment, const Color(0xFFEDE1C8));
    expect(AppThemeColors.copper, const Color(0xFFA6672C));
    expect(AppThemeColors.verdigris, const Color(0xFF5C7A6E));
    expect(AppThemeColors.brass, const Color(0xFFC9A227));
    expect(AppThemeColors.oxblood, const Color(0xFF6B1E23));
  });

  test('MedallionPalette masterDark: web/dot copper, rim/needle brass, metin parchment', () {
    final p = kMasterDarkPalette;
    expect(p.web, const Color(0xFFA6672C));
    expect(p.rim, const Color(0xFFC9A227));
    expect(p.needle, const Color(0xFFC9A227));
    expect(p.dot, const Color(0xFFA6672C));
    expect(p.textColor, const Color(0xFFEDE1C8));
  });

  test('brass AppThemeColors üzerinde yalnız; web/dot brass değil', () {
    expect(kMasterDarkPalette.rim, AppThemeColors.brass);
    expect(kMasterDarkPalette.needle, AppThemeColors.brass);
    expect(kMasterDarkPalette.web, isNot(AppThemeColors.brass));
    expect(kMasterDarkPalette.dot, isNot(AppThemeColors.brass));
  });
}
