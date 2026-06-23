import 'package:flutter/material.dart';
import 'package:malt_radar/core/theme/app_theme.dart';

class SectionHeader extends StatelessWidget {
  final String title;
  final IconData? icon;

  const SectionHeader({
    super.key,
    required this.title,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (icon != null) ...[
          Icon(icon, color: AppTheme.primary, size: 24),
          const SizedBox(width: 12),
        ],
        Text(
          title,
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                color: AppTheme.primary,
                fontSize: 22,
              ),
        ),
      ],
    );
  }
}
