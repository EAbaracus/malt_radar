import 'package:flutter/material.dart';

/// Marka paleti — tek token kaynağı. Görsel spec:
/// docs/superpowers/specs/2026-08-09-brand-identity-implementation-design.md
/// Kullanım oranı: ~%65 char/parşömen · %20 bakır · %10 verdigris · %5 pirinç/oxblood.
class AppThemeColors {
  const AppThemeColors._();

  static const Color caskChar = Color(0xFF1A120B); // zemin / metin
  static const Color parchment = Color(0xFFEDE1C8); // açık zemin
  static const Color parchmentLt = Color(0xFFF5ECD8);
  static const Color inkSoft = Color(0xFF2B1F14);
  static const Color copper = Color(0xFFA6672C); // birincil vurgu
  static const Color copperDim = Color(0xFF8A5424);
  static const Color verdigris = Color(0xFF5C7A6E); // ikincil vurgu / rozet
  static const Color brass = Color(
    0xFFC9A227,
  ); // SADECE amblem mühür halkası + ibre
  static const Color oxblood = Color(0xFF6B1E23); // nadir — uyarı/özel rozet
  static const Color oxbloodLt = Color(
    0xFFD6645C,
  ); // oxblood açık shade — koyu zeminde ikon/metin (4.99:1 caskChar üstünde)
}

/// Medallion renk paketi. `brass` yalnızca burada (rim/needle) yaşar.
/// UI widgetlarının brass'a erişimi YOKTUR (AppTheme'e konmaz).
class MedallionPalette {
  const MedallionPalette({
    required this.web,
    required this.rim,
    required this.needle,
    required this.dot,
    required this.textColor,
  });

  final Color web; // 7-gen çizgileri
  final Color rim; // dış mühür halkası (brass)
  final Color needle; // ibre (brass)
  final Color dot; // köşe noktaları
  final Color textColor; // yedek — etiket yok, ileride kullanılırsa

  static const MedallionPalette masterDark = MedallionPalette(
    web: AppThemeColors.copper,
    rim: AppThemeColors.brass,
    needle: AppThemeColors.brass,
    dot: AppThemeColors.copper,
    textColor: AppThemeColors.parchment,
  );

  static const MedallionPalette masterLight = MedallionPalette(
    web: AppThemeColors.copperDim,
    rim: AppThemeColors.copperDim,
    needle: AppThemeColors.oxblood,
    dot: AppThemeColors.oxblood,
    textColor: AppThemeColors.caskChar,
  );
}

const kMasterDarkPalette = MedallionPalette.masterDark;
const kMasterLightPalette = MedallionPalette.masterLight;
const kMedallionFontFamily = 'CourierPrime';
