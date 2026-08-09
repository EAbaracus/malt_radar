import 'package:flutter/material.dart';
import 'app_theme_colors.dart';

class AppTheme {
  // Marka tokenları — tek kaynak app_theme_colors.dart.
  // Brass (C9A227) KASITLI olarak burada YOKTUR: yalnızca amblem mühür + ibrede
  // (MedallionPalette). UI'nin brass'a erişimi UI'dan yalıtılmıştır.
  static const Color background = AppThemeColors.caskChar; // #1A120B
  static const Color surface = Color(0xFF241A10); // kart zemin (marka koyu)
  static const Color surfaceElevated = Color(0xFF2B1F14);

  // Vurgular
  static const Color primary = AppThemeColors.copper; // Birincil
  static const Color secondary = AppThemeColors.verdigris; // Rozet / ikincil
  static const Color accent = AppThemeColors.copperDim; // Alt vurgu

  // Bildirim
  static const Color error = AppThemeColors.oxblood; // uyarı/hata (nadir)
  static const Color success = Color(0xFF81C784);

  // Metin (koyu zeminde)
  static const Color textPrimary = AppThemeColors.parchment; // #EDE1C8
  static const Color textSecondary = Color(0xFFBDB2A0);
  static const Color textMuted = Color(0xFF8C8071);

  static ThemeData get darkTheme {
    final base = ThemeData.dark().textTheme;

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: secondary,
        surface: surface,
        error: error,
        onPrimary: background,
        onSecondary: background,
        onSurface: textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        iconTheme: const IconThemeData(color: primary),
        titleTextStyle: const TextStyle(
          fontFamily: 'Fraunces',
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.2,
        ),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(
            color: AppThemeColors.parchment.withValues(alpha: 0.08),
            width: 1,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF1F170E),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(
            color: AppThemeColors.caskChar.withValues(alpha: 0.2),
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(
            color: AppThemeColors.parchment.withValues(alpha: 0.2),
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: primary, width: 1.5),
        ),
        labelStyle: const TextStyle(color: textSecondary),
        hintStyle: const TextStyle(color: textMuted),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: primary,
        inactiveTrackColor: surfaceElevated,
        thumbColor: primary,
        overlayColor: primary.withValues(alpha: 0.12),
        valueIndicatorColor: primary,
        valueIndicatorTextStyle: const TextStyle(
          color: background,
          fontWeight: FontWeight.bold,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: background,
          elevation: 4,
          shadowColor: primary.withValues(alpha: 0.3),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ),
      textTheme: base.copyWith(
        displayLarge: MarkaFonts.fraunces(textPrimary, 48, FontWeight.w700, -0.96),
        headlineLarge: MarkaFonts.fraunces(textPrimary, 32, FontWeight.w600, 0),
        headlineMedium: MarkaFonts.fraunces(textPrimary, 24, FontWeight.w500, 0),
        titleLarge: MarkaFonts.fraunces(textPrimary, 20, FontWeight.w600, 0),
        titleMedium: MarkaFonts.inter(textPrimary, 16, FontWeight.w500, 0),
        bodyLarge: MarkaFonts.serif(textPrimary, 18, FontWeight.w400, 0),
        bodyMedium: MarkaFonts.serif(textPrimary, 16, FontWeight.w400, 0),
        bodySmall: MarkaFonts.serif(textSecondary, 14, FontWeight.w400, 0),
        labelMedium: MarkaFonts.inter(textPrimary, 14, FontWeight.w500, 0.7),
        labelSmall: MarkaFonts.inter(textSecondary, 12, FontWeight.w600, 1.2),
      ),
    );
  }
}

/// Marka font aileleri bundle'dan gelir (offline-safe, Play-safe).
class MarkaFonts {
  const MarkaFonts._();

  static TextStyle fraunces(Color c, double s, FontWeight w, double ls) =>
      TextStyle(fontFamily: 'Fraunces', color: c, fontSize: s, fontWeight: w, letterSpacing: ls);
  static TextStyle serif(Color c, double s, FontWeight w, double ls) =>
      TextStyle(fontFamily: 'SourceSerif4', color: c, fontSize: s, fontWeight: w, letterSpacing: ls);
  static TextStyle inter(Color c, double s, FontWeight w, double ls) =>
      TextStyle(fontFamily: 'Inter', color: c, fontSize: s, fontWeight: w, letterSpacing: ls);
}
