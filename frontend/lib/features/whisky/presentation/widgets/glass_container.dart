import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

class GlassContainer extends StatelessWidget {
  final Widget child;
  final double blur;
  final double opacity;
  final BorderRadius? borderRadius;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Border? border;
  final Color? color;

  const GlassContainer({
    super.key,
    required this.child,
    this.blur = 10.0,
    this.opacity = 0.05,
    this.borderRadius,
    this.padding,
    this.margin,
    this.border,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveBorderRadius = borderRadius ?? BorderRadius.circular(20);
    
    return Container(
      margin: margin,
      child: ClipRRect(
        borderRadius: effectiveBorderRadius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              color: (color ?? AppThemeColors.parchment).withValues(alpha: opacity),
              borderRadius: effectiveBorderRadius,
              border: border ?? Border.all(
                color: AppThemeColors.parchment.withValues(alpha: 0.1),
                width: 1.0,
              ),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}
