import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'consent_controller.dart';
import 'cmp_preferences_dialog.dart';

/// Consent Management Platform (CMP) banner.
///
/// Renders a bottom-anchored card offering Accept all / Reject all /
/// Preferences until the user records an explicit decision, after which it
/// collapses to nothing. The decision flows to:
///   1. `window.updateGoogleConsent` (via [ConsentBridge]) for Consent Mode v2,
///   2. the local `UserSettings` store (so the banner stays dismissed), and
///   3. [analyticsServiceProvider] (via [consentControllerProvider]).
///
/// G6 boundary: no live telemetry is dispatched from here — it only records
/// the consent decision.
class CmpBanner extends ConsumerWidget {
  const CmpBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(consentControllerProvider);
    if (state.hasDecided) {
      return const SizedBox.shrink();
    }

    final isTr = ref.watch(localizationProvider) == 'tr';
    final title =
        isTr ? 'Gizliliğinize değer veriyoruz' : 'We value your privacy';
    final body = isTr
        ? 'Deneyiminizi iyileştirmek ve reklamları ölçmek için çerezler '
              'kullanıyoruz. Tercihlerinizi istediğiniz zaman değiştirebilirsiniz.'
        : 'We use cookies to improve your experience and measure ads. '
              'You can change your choices at any time.';

    return SafeArea(
      top: false,
      minimum: const EdgeInsets.all(12),
      child: Align(
        alignment: Alignment.bottomCenter,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 560),
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          decoration: BoxDecoration(
            color: AppTheme.surfaceElevated,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: AppTheme.primary.withValues(alpha: 0.3),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.4),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.privacy_tip_outlined,
                    color: AppTheme.primary,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                body,
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                alignment: WrapAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => showCmpPreferences(context),
                    child: Text(
                      isTr ? 'Tercihler' : 'Preferences',
                      style: const TextStyle(color: AppTheme.textMuted),
                    ),
                  ),
                  OutlinedButton(
                    onPressed: () => ref
                        .read(consentControllerProvider.notifier)
                        .denyAll(),
                    child: Text(
                      isTr ? 'Tümünü reddet' : 'Reject all',
                      style: const TextStyle(color: AppTheme.textSecondary),
                    ),
                  ),
                  ElevatedButton(
                    onPressed: () => ref
                        .read(consentControllerProvider.notifier)
                        .acceptAll(),
                    child: Text(isTr ? 'Tümünü kabul et' : 'Accept all'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
