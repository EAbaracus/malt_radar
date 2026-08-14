import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  test('AppTheme tokenları marka paletine map\'li — eski gold yok', () {
    expect(AppTheme.background, AppThemeColors.caskChar);
    expect(AppTheme.surface, isNot(const Color(0xFF1A1A1A)));
    expect(AppTheme.primary, AppThemeColors.copper);
    expect(AppTheme.secondary, AppThemeColors.verdigris);
    expect(AppTheme.error, AppThemeColors.oxblood);
    expect(AppTheme.primary, isNot(const Color(0xFFD4AF37)));
    expect(AppTheme.secondary, isNot(const Color(0xFFB8860B)));
  });

  test('brass AppTheme üzerinde tanımlı DEĞİL (UI yalıtımı)', () {
    expect(AppThemeColors.brass, const Color(0xFFC9A227));
    expect(kMasterDarkPalette.rim, AppThemeColors.brass);
  });

  test('darkTheme font dokuları marka ailesini kullanır', () {
    final t = AppTheme.darkTheme;
    expect(t.textTheme.displayLarge?.fontFamily, 'Fraunces');
    expect(t.textTheme.headlineLarge?.fontFamily, 'Fraunces');
    expect(t.textTheme.bodyLarge?.fontFamily, 'SourceSerif4');
    expect(t.textTheme.bodyMedium?.fontFamily, 'SourceSerif4');
    expect(t.textTheme.labelSmall?.fontFamily, 'Inter');
    expect(t.textTheme.labelMedium?.fontFamily, 'Inter');
    expect(t.textTheme.titleMedium?.fontFamily, 'Inter');
  });
}
