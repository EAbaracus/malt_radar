import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Brand Colors from DESIGN.md
  static const Color background = Color(0xFF0F0F0F); // Obsidian
  static const Color surface = Color(0xFF1A1A1A); // Surface for cards
  static const Color surfaceElevated = Color(0xFF1E1E28);
  
  // Accents
  static const Color primary = Color(0xFFD4AF37);    // Primary Gold
  static const Color secondary = Color(0xFFB8860B);  // Amber Secondary
  static const Color accent = Color(0xFFF3E5AB);
  
  // Feedback
  static const Color error = Color(0xFFE57373);
  static const Color success = Color(0xFF81C784);
  
  // Text
  static const Color textPrimary = Color(0xFFFDFDFD);
  static const Color textSecondary = Color(0xFFA5A6AC);
  static const Color textMuted = Color(0xFF6B6C75);

  static ThemeData get darkTheme {
    final baseInter = GoogleFonts.interTextTheme(ThemeData.dark().textTheme);

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
        titleTextStyle: GoogleFonts.playfairDisplay(
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
          borderRadius: BorderRadius.circular(24), // Rounded-XL
          side: BorderSide(
            color: Colors.white.withValues(alpha: 0.08),
            width: 1,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF121212),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: const Color(0xFF000000).withValues(alpha: 0.2)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: const Color(0xFFA0A0A0).withValues(alpha: 0.2)),
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
        valueIndicatorTextStyle: const TextStyle(color: background, fontWeight: FontWeight.bold),
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
          textStyle: GoogleFonts.inter(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ),
      textTheme: baseInter.copyWith(
        displayLarge: GoogleFonts.playfairDisplay(color: textPrimary, fontSize: 48, fontWeight: FontWeight.w700, letterSpacing: -0.96),
        headlineLarge: GoogleFonts.playfairDisplay(color: textPrimary, fontSize: 32, fontWeight: FontWeight.w600),
        headlineMedium: GoogleFonts.playfairDisplay(color: textPrimary, fontSize: 24, fontWeight: FontWeight.w500),
        titleLarge: GoogleFonts.playfairDisplay(color: textPrimary, fontSize: 20, fontWeight: FontWeight.w600),
        titleMedium: GoogleFonts.inter(color: textPrimary, fontSize: 16, fontWeight: FontWeight.w500),
        bodyLarge: GoogleFonts.inter(color: textPrimary, fontSize: 18, fontWeight: FontWeight.w400),
        bodyMedium: GoogleFonts.inter(color: textPrimary, fontSize: 16, fontWeight: FontWeight.w400),
        bodySmall: GoogleFonts.inter(color: textSecondary, fontSize: 14, fontWeight: FontWeight.w400),
        labelMedium: GoogleFonts.inter(color: textPrimary, fontSize: 14, fontWeight: FontWeight.w500, letterSpacing: 0.7),
        labelSmall: GoogleFonts.inter(color: textSecondary, fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 1.2),
      ),
    );
  }
}
