import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'consent_controller.dart';
import 'consent_state.dart';

/// Granular consent preferences dialog, reachable from the CMP banner.
///
/// Two buckets only (mirroring the Consent Mode v2 bootstrap): analytics
/// (`analytics_storage`) and marketing (`ad_storage` / `ad_user_data` /
/// `ad_personalization`). Saving an explicit decision also hides the banner.
class CmpPreferencesDialog extends ConsumerStatefulWidget {
  const CmpPreferencesDialog({super.key});

  @override
  ConsumerState<CmpPreferencesDialog> createState() =>
      _CmpPreferencesDialogState();
}

class _CmpPreferencesDialogState extends ConsumerState<CmpPreferencesDialog> {
  late bool _analytics;
  late bool _marketing;

  @override
  void initState() {
    super.initState();
    final s = ref.read(consentControllerProvider);
    _analytics = s.isAnalyticsGranted;
    _marketing = s.isMarketingGranted;
  }

  void _apply(ConsentChoice analytics, ConsentChoice marketing) {
    ref
        .read(consentControllerProvider.notifier)
        .savePreferences(analytics: analytics, marketing: marketing);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final isTr = ref.watch(localizationProvider) == 'tr';

    return AlertDialog(
      backgroundColor: AppTheme.surface,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Text(isTr ? 'Çerez tercihleri' : 'Cookie preferences'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SwitchListTile(
            activeTrackColor: AppTheme.primary,
            contentPadding: EdgeInsets.zero,
            title: Text(isTr ? 'Analitik çerezler' : 'Analytics cookies'),
            subtitle: Text(
              isTr
                  ? 'Kullanımı anlamak ve iyileştirmek için anonim istatistikler.'
                  : 'Anonymous statistics to understand and improve usage.',
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 12,
                height: 1.4,
              ),
            ),
            value: _analytics,
            onChanged: (v) => setState(() => _analytics = v),
          ),
          SwitchListTile(
            activeTrackColor: AppTheme.primary,
            contentPadding: EdgeInsets.zero,
            title: Text(isTr ? 'Pazarlama çerezleri' : 'Marketing cookies'),
            subtitle: Text(
              isTr
                  ? 'Reklamların ölçülmesi ve kişiselleştirilmesi.'
                  : 'Measuring and personalising advertising.',
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 12,
                height: 1.4,
              ),
            ),
            value: _marketing,
            onChanged: (v) => setState(() => _marketing = v),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => _apply(ConsentChoice.denied, ConsentChoice.denied),
          child: Text(
            isTr ? 'Tümünü reddet' : 'Reject all',
            style: const TextStyle(color: AppTheme.textSecondary),
          ),
        ),
        TextButton(
          onPressed: () => _apply(ConsentChoice.granted, ConsentChoice.granted),
          child: Text(
            isTr ? 'Tümünü kabul et' : 'Accept all',
            style: const TextStyle(color: AppTheme.textSecondary),
          ),
        ),
        FilledButton(
          onPressed: () => _apply(
            _analytics ? ConsentChoice.granted : ConsentChoice.denied,
            _marketing ? ConsentChoice.granted : ConsentChoice.denied,
          ),
          style: FilledButton.styleFrom(backgroundColor: AppTheme.primary),
          child: Text(isTr ? 'Kaydet' : 'Save'),
        ),
      ],
    );
  }
}

/// Opens the consent preferences dialog from any [BuildContext].
void showCmpPreferences(BuildContext context) {
  showDialog<void>(
    context: context,
    builder: (_) => const CmpPreferencesDialog(),
  );
}
