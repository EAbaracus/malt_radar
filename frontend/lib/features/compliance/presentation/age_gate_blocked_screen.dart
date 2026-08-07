import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/core/theme/app_theme.dart';

/// Shown when the user declared they are under the legal drinking age.
/// No product content is rendered and no way back is offered in-app.
class AgeGateBlockedScreen extends ConsumerWidget {
  const AgeGateBlockedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isTr = ref.watch(localizationProvider) == 'tr';
    final title = isTr ? 'Erişim yalnızca yetişkinlere' : 'Adults only';
    final message = isTr
        ? 'Bu uygulama yalnızca ülkesinin yasal içki yaşını doldurmuş '
              'yetişkinlere yöneliktir. Reşit olmayanların erişimi engellenmiştir.'
        : 'This application is available only to adults of legal drinking '
              'age. Access by minors is blocked.';
    final footer = isTr
        ? 'Ölçülü ve sorumlu tüketim esastır.'
        : 'Drink responsibly.';

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.error.withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.block,
                    color: AppTheme.error,
                    size: 44,
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: AppTheme.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 15,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 32),
                Text(
                  footer,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
