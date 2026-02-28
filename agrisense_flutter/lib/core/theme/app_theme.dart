import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  // Primary palette — natural greens for agriculture
  static const Color primary = Color(0xFF2E7D32);       // Forest green
  static const Color primaryDark = Color(0xFF1B5E20);    // Deep green
  static const Color primaryLight = Color(0xFF66BB6A);   // Soft green

  // Background — warm off-white with subtle green undertone
  static const Color bgLight = Color(0xFFF6F8F4);       // Main background
  static const Color bgWhite = Color(0xFFFFFFFF);        // Cards / surfaces
  static const Color bgDarker = Color(0xFFEEF2EA);       // Slightly darker sections
  static const Color bgCard = Color(0xFFFFFFFF);          // Card background
  static const Color bgCardLight = Color(0xFFF0F4EC);    // Tinted card surface
  static const Color background = bgLight;

  // Legacy alias — bgDark now maps to a usable light-scheme color
  static const Color bgDark = Color(0xFFF6F8F4);

  // Accent — teal-green, complements primary
  static const Color accent = Color(0xFF00897B);
  static const Color accentLight = Color(0xFF4DB6AC);

  // Status
  static const Color success = Color(0xFF388E3C);
  static const Color warning = Color(0xFFF9A825);
  static const Color error = Color(0xFFD32F2F);
  static const Color info = Color(0xFF1976D2);

  // Text — dark grays for readability on light backgrounds
  static const Color textPrimary = Color(0xFF1B2B1B);    // Near-black green tint
  static const Color textSecondary = Color(0xFF5F6B5F);  // Medium gray-green
  static const Color textMuted = Color(0xFF94A394);       // Light muted green-gray

  // Glass / overlay — used for subtle layering
  static const Color glassWhite = Color(0x1A2E7D32);     // Green tinted glass
  static const Color glassBorder = Color(0x1A000000);     // Subtle dark border

  // Disease severity
  static const Color severityLow = Color(0xFF388E3C);
  static const Color severityMedium = Color(0xFFF9A825);
  static const Color severityHigh = Color(0xFFD32F2F);
  static const Color severityCritical = Color(0xFFB71C1C);

  // Shadows for light theme
  static List<BoxShadow> get cardShadow => [
    BoxShadow(
      color: const Color(0xFF2E7D32).withOpacity(0.06),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> get softShadow => [
    BoxShadow(
      color: Colors.black.withOpacity(0.04),
      blurRadius: 8,
      offset: const Offset(0, 2),
    ),
  ];
}

class AppTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.bgLight,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primary,
        secondary: AppColors.accent,
        surface: AppColors.bgWhite,
        error: AppColors.error,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: AppColors.textPrimary,
      ),
      textTheme: GoogleFonts.poppinsTextTheme(
        ThemeData.light().textTheme,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.bgLight,
        elevation: 0,
        centerTitle: true,
        foregroundColor: AppColors.textPrimary,
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        titleTextStyle: GoogleFonts.poppins(
          color: AppColors.textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.bgWhite,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: GoogleFonts.poppins(
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.bgCardLight,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.bgWhite,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
      ),
    );
  }
}
