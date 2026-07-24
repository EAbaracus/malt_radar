import 'package:flutter/material.dart';
import 'package:malt_radar/core/theme/app_theme.dart';

class TastingChip extends StatelessWidget {
  final String label;
  final VoidCallback? onTap;
  final bool isSelected;

  const TastingChip({
    super.key,
    required this.label,
    this.onTap,
    this.isSelected = false,
  });

  @override
  Widget build(BuildContext context) {
    final chipWidget = Container(
      margin: const EdgeInsets.only(right: 6),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: isSelected
            ? AppTheme.primary.withValues(alpha: 0.25)
            : Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isSelected
              ? AppTheme.primary
              : Colors.white.withValues(alpha: 0.10),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: isSelected ? Colors.white : AppTheme.textSecondary,
                  fontWeight: isSelected ? FontWeight.bold : null,
                ),
          ),
          if (isSelected && onTap != null) ...[
            const SizedBox(width: 4),
            const Icon(
              Icons.close,
              size: 12,
              color: Colors.white70,
            ),
          ],
        ],
      ),
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: chipWidget,
      );
    }

    return chipWidget;
  }
}
