import 'package:flutter/material.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';

/// "Google ile devam et" (TR) / "Continue with Google" (EN) sign-in button.
///
/// Extracted into its own widget (with an injected [onPressed] + [isLoading])
/// so it can be unit-tested without binding the real `AuthController` /
/// `GoogleSignIn` plugin — the caller (AuthScreen) owns the loading state and
/// the controller call, keeping this widget pure and trivially testable.
class GoogleSignInButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final bool isLoading;
  final String label;

  const GoogleSignInButton({
    super.key,
    required this.onPressed,
    required this.isLoading,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton(
        key: const Key('google-sign-in-button'),
        onPressed: isLoading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: AppTheme.primary),
          foregroundColor: AppThemeColors.parchment,
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        child: isLoading
            ? const SizedBox(width: 20, height: 20, child: BrandSpinner())
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Inline "G" mark since no Google logo asset is bundled.
                  // Decorative: excluded from the semantics tree so screen
                  // readers announce only the real [label], never a bare "G".
                  const ExcludeSemantics(
                    child: Text(
                      'G',
                      style: TextStyle(
                        color: AppTheme.primary,
                        fontWeight: FontWeight.w700,
                        fontSize: 18,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
