import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

class AppTheme {
  static ThemeData infantilTheme() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primary,
        background: AppColors.backgroundInfantil,
      ),
      textTheme: GoogleFonts.nunitoTextTheme().copyWith(
        bodyLarge: GoogleFonts.nunito(fontSize: 20, fontWeight: FontWeight.bold),
        bodyMedium: GoogleFonts.nunito(fontSize: 18),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        ),
      ),
    );
  }

  static ThemeData adultoTheme() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primary,
        background: AppColors.backgroundAdulto,
      ),
      textTheme: GoogleFonts.interTextTheme().copyWith(
        bodyLarge: GoogleFonts.inter(fontSize: 16),
        bodyMedium: GoogleFonts.inter(fontSize: 14),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        centerTitle: true,
      ),
    );
  }
}
