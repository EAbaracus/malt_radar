import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import '../domain/legal_age.dart';
import 'age_gate_providers.dart';

/// Age-verification gate shown at first launch and never again once the user
/// confirms they are of legal drinking age for their selected country.
///
/// Compliance posture (Turkey-alcohol rules + global best practice):
///  - Underage users are locked out entirely (no content is rendered).
///  - Copy is neutral, informational and non-incentivizing.
///  - No price data is ever displayed on this screen.
///  - Short responsible-drinking notice is shown.
class AgeGateScreen extends ConsumerStatefulWidget {
  const AgeGateScreen({super.key});

  @override
  ConsumerState<AgeGateScreen> createState() => _AgeGateScreenState();
}

class _AgeGateScreenState extends ConsumerState<AgeGateScreen> {
  late final List<LegalEntry> _entries;
  LegalEntry? _selected;
  bool _confirmed = false;

  @override
  void initState() {
    super.initState();
    _entries = sortedEntries();
    // Default to the device locale's country when present, else the relaxed
    // majority default (18). The user can change it at any time.
    final localeCountry =
        WidgetsBinding.instance.platformDispatcher.locale.countryCode;
    if (localeCountry != null && localeCountry.isNotEmpty) {
      for (final e in _entries) {
        if (e.code == localeCountry) {
          _selected = e;
          break;
        }
      }
    }
    _selected ??= _entries.first;
  }

  void _confirm() {
    if (_selected == null || !_confirmed) return;
    ref.read(ageGateProvider.notifier).consent(_selected!.code);
    // No navigation is needed: main.dart rebuilds `home` from the stream once
    // the provider flips to `consented`.
  }

  void _declareUnderage() {
    ref.read(ageGateProvider.notifier).block();
  }

  @override
  Widget build(BuildContext context) {
    final isTr = ref.watch(localizationProvider) == 'tr';
    final warning = isTr
        ? 'Bu uygulama alkollü içeceklere ilişkin bilgi içerir.\nYalnızca ülkenizin yasal içki yaşını doldurmuş yetişkinler içindir.'
        : 'This application contains information about alcoholic '
              'beverages.\nIt is intended for adults of legal drinking age in '
              'their country.';
    final minAge = _selected?.minAge ?? defaultMinAge;
    final confirmLabel = isTr
        ? '$minAge yaşını doldurduğumu ve ülkemdeki yasal içki yaşına uygun olduğumu onaylıyorum.'
        : 'I confirm that I am $minAge years of age or older and of legal '
              'drinking age in my country.';
    final responsible = isTr
        ? 'Ölçülü ve sorumlu tüketim esastır. Reşit olmayanlara sunulmaz.'
        : 'Drink responsibly. Not for minors.';

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 8),
                  Center(
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withValues(alpha: 0.08),
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: AppTheme.primary.withValues(alpha: 0.2),
                              width: 1.5,
                            ),
                          ),
                          child: const Medallion(
                            size: 40,
                            level: MedallionLevel.icon,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          'MALT RADAR',
                          style: Theme.of(context)
                              .textTheme
                              .headlineMedium
                              ?.copyWith(
                                color: AppTheme.primary,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 2.0,
                              ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    warning,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 14,
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 28),
                  DropdownButtonFormField<LegalEntry>(
                    initialValue: _selected,
                    isExpanded: true,
                    decoration: InputDecoration(
                      labelText: isTr ? 'Ülke' : 'Country',
                      prefixIcon: const Icon(
                        Icons.public,
                        color: AppTheme.primary,
                      ),
                    ),
                    items: _entries
                        .map(
                          (e) => DropdownMenuItem(
                            value: e,
                            child: Text(
                              e.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (v) => setState(() => _selected = v),
                  ),
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: AppTheme.primary.withValues(alpha: 0.25),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.verified_user,
                          color: AppTheme.primary,
                          size: 20,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            isTr
                                ? '${_selected?.name ?? ''} için asgari yasal içki yaşı: $minAge'
                                : 'Minimum legal drinking age in '
                                      '${_selected?.name ?? ''}: $minAge',
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      IgnorePointer(
                        // Cannot be un-ticked once confirmed (compliance):
                        // a wrong tap is only reversible through the country
                        // picker, which keeps the confirmation explicit.
                        ignoring: _confirmed,
                        child: Checkbox(
                          value: _confirmed,
                          activeColor: AppTheme.primary,
                          onChanged: (v) =>
                              setState(() => _confirmed = v ?? false),
                        ),
                      ),
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: Text(
                            confirmLabel,
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 14,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _confirmed ? _confirm : null,
                    child: Text(
                      _confirmed && _selected != null
                          ? (isTr ? 'DEVAM ET' : 'CONTINUE')
                          : (isTr
                                ? 'Onaylamak için kutucuğu işaretleyin'
                                : 'Confirm to continue'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: _confirmed ? null : _declareUnderage,
                    child: Text(
                      isTr ? 'Reşit değilim' : 'I am under the legal age',
                      style: const TextStyle(
                        color: AppTheme.textMuted,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.auto_graph,
                        color: AppTheme.secondary,
                        size: 16,
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          responsible,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: AppTheme.textMuted,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
