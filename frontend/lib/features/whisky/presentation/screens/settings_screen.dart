import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import '../controllers/whisky_providers.dart';
import '../../domain/models/whisky.dart';

import '../../../../core/localization/localization_provider.dart';
import 'package:malt_radar/features/compliance/presentation/age_gate_providers.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _isLoading = false;

  void _clearCache() async {
    final tr = ref.read(trProvider);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: Text(tr('clear_cache')),
        content: Text(tr('clear_cache_confirm')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(tr('cancel')),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(
              tr('clear_cache'),
              style: const TextStyle(color: AppTheme.error),
            ),
          ),
        ],
      ),
    );

    if (confirm != true || !mounted) return;

    setState(() {
      _isLoading = true;
    });

    final repository = ref.read(whiskyRepositoryProvider);
    await repository.clearCache();

    setState(() {
      _isLoading = false;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(tr('cache_cleared')),
          backgroundColor: AppTheme.primary,
        ),
      );
    }
  }

  void _clearReferenceWhisky() async {
    final tr = ref.read(trProvider);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: Text(tr('remove_reference_whisky_confirm_title')),
        content: Text(tr('remove_reference_whisky_confirm_message')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(tr('cancel')),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(
              tr('remove'),
              style: const TextStyle(color: AppTheme.error),
            ),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      setState(() {
        _isLoading = true;
      });

      final repository = ref.read(whiskyRepositoryProvider);
      await repository.clearReferenceWhisky();

      // Invalidate provider state
      ref.invalidate(referenceSettingsStreamProvider);
      ref.invalidate(referenceWhiskyModelProvider);

      setState(() {
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(tr('reference_whisky_removed')),
            backgroundColor: AppTheme.primary,
          ),
        );
      }
    }
  }

  void _changeReferenceWhisky() async {
    final repository = ref.read(whiskyRepositoryProvider);
    final db = ref.read(appDatabaseProvider);
    final tr = ref.read(trProvider);

    final list = await db.select(db.whiskies).get();
    final localWhiskies = list
        .map((e) => Whisky.fromEntities(whisky: e))
        .toList();

    if (localWhiskies.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(tr('add_whisky_first'))));
      }
      return;
    }

    if (mounted) {
      showModalBottomSheet(
        context: context,
        backgroundColor: AppTheme.surface,
        builder: (context) {
          int tempScore = 100;
          return StatefulBuilder(
            builder: (context, setModalState) {
              return Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      tr('select_new_reference'),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primary,
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: ListView.builder(
                        itemCount: localWhiskies.length,
                        itemBuilder: (context, index) {
                          final w = localWhiskies[index];
                          return ListTile(
                            title: Text(w.name),
                            trailing: const Icon(
                              Icons.check_circle_outline,
                              color: AppTheme.primary,
                            ),
                            onTap: () {
                              showDialog(
                                context: context,
                                builder: (context) {
                                  return StatefulBuilder(
                                    builder: (context, setDialogState) {
                                      return AlertDialog(
                                        backgroundColor: AppTheme.surface,
                                        title: Text(tr('set_reference_score')),
                                        content: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Text(
                                              w.name,
                                              style: const TextStyle(
                                                fontWeight: FontWeight.bold,
                                                color: AppTheme.primary,
                                              ),
                                            ),
                                            const SizedBox(height: 16),
                                            Text(
                                              tr('reference_absolute_score', [
                                                tempScore,
                                              ]),
                                            ),
                                            Slider(
                                              value: tempScore.toDouble(),
                                              min: 50,
                                              max: 100,
                                              divisions: 50,
                                              onChanged: (val) {
                                                setDialogState(() {
                                                  tempScore = val.round();
                                                });
                                              },
                                            ),
                                          ],
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () =>
                                                Navigator.pop(context),
                                            child: Text(tr('cancel')),
                                          ),
                                          ElevatedButton(
                                            onPressed: () async {
                                              await repository
                                                  .setReferenceWhisky(
                                                    w.id,
                                                    tempScore,
                                                  );
                                              await repository
                                                  .updatePersonalScore(
                                                    w.id,
                                                    tempScore,
                                                  );

                                              if (context.mounted) {
                                                Navigator.pop(context);
                                                Navigator.pop(context);

                                                ScaffoldMessenger.of(
                                                  context,
                                                ).showSnackBar(
                                                  SnackBar(
                                                    content: Text(
                                                      tr('reference_updated', [
                                                        w.name,
                                                      ]),
                                                    ),
                                                  ),
                                                );
                                              }
                                            },
                                            child: Text(tr('save')),
                                          ),
                                        ],
                                      );
                                    },
                                  );
                                },
                              );
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              );
            },
          );
        },
      );
    }
  }

  void _reverifyAge() async {
    final isTr = ref.read(localizationProvider) == 'tr';
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: Text(isTr ? 'Yaş doğrulamasını yenile' : 'Re-verify age'),
        content: Text(
          isTr
              ? 'Yaş doğrulaması sıfırlanacak ve uygulama bir sonraki açılışta yeniden soracak. Devam etmek istiyor musunuz?'
              : 'This clears the age verification; you will be asked again on the next launch. Continue?',
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(isTr ? 'İPTAL' : 'CANCEL'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(isTr ? 'YENİLE' : 'RE-VERIFY'),
          ),
        ],
      ),
    );
    if (confirm == true && mounted) {
      // Clearing resets the provider to `notConsented`; main.dart then swaps
      // the entry screen to the age gate automatically.
      ref.read(ageGateProvider.notifier).reset();
    }
  }

  void _openAuth() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => const AuthScreen()));
  }

  Future<void> _syncNow() async {
    final isTr = ref.read(localizationProvider) == 'tr';
    try {
      final pushRes = await ref.read(syncServiceProvider).push();
      await ref.read(syncServiceProvider).pull();
      final counts = pushRes['counts'] as Map<String, dynamic>? ?? const {};
      final total = counts.values.fold<int>(
        0,
        (a, b) => a + ((b as num?)?.toInt() ?? 0),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isTr
                  ? 'Senkronize edildi ($total öğe yüklendi)'
                  : 'Synced ($total items pushed)',
            ),
            backgroundColor: AppTheme.primary,
          ),
        );
      }
      await ref.read(authControllerProvider.notifier).refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isTr ? 'Senkronizasyon başarısız: $e' : 'Sync failed: $e',
            ),
            backgroundColor: AppTheme.error,
          ),
        );
      }
    }
  }

  Future<void> _signOut() async {
    final isTr = ref.read(localizationProvider) == 'tr';
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: Text(isTr ? 'Çıkış yap' : 'Sign out'),
        content: Text(
          isTr
              ? 'Bu cihazdan çıkış yapılacak. Sunucuda saklanan veriler korunur.'
              : 'Sign out from this device. Data stored on the server is kept.',
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(isTr ? 'İPTAL' : 'CANCEL'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(isTr ? 'ÇIKIŞ' : 'SIGN OUT'),
          ),
        ],
      ),
    );
    if (confirm == true && mounted) {
      await ref.read(authControllerProvider.notifier).logout();
    }
  }

  Widget _buildAccountCard(String langCode) {
    final auth = ref.watch(authControllerProvider);
    final loggedIn = auth.isLoggedIn;
    final user = auth.user;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.account_circle_outlined,
                  color: AppTheme.primary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    loggedIn
                        ? (user?.email ?? 'user')
                        : (langCode == 'tr'
                              ? 'Giriş yapılmadı'
                              : 'Not signed in'),
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (!loggedIn)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _openAuth,
                  icon: const Icon(Icons.login, color: AppTheme.primary),
                  label: Text(
                    langCode == 'tr'
                        ? 'Giriş Yap / Kayıt Ol'
                        : 'Sign in / Create account',
                    style: const TextStyle(color: AppTheme.primary),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.primary),
                  ),
                ),
              )
            else ...[
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _syncNow,
                  icon: const Icon(Icons.sync, color: AppTheme.primary),
                  label: Text(
                    langCode == 'tr' ? 'Şimdi senkronize et' : 'Sync now',
                    style: const TextStyle(color: AppTheme.primary),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.primary),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _signOut,
                  icon: const Icon(Icons.logout, color: AppTheme.error),
                  label: Text(
                    langCode == 'tr' ? 'Çıkış yap' : 'Sign out',
                    style: const TextStyle(color: AppTheme.error),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppTheme.error),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);
    final refWhiskyAsync = ref.watch(referenceWhiskyModelProvider);
    final tr = ref.watch(trProvider);
    final langCode = ref.watch(localizationProvider);
    final age = ref.watch(ageGateProvider);

    final settings = settingsAsync.value ?? {};
    final referenceScore =
        settings['reference_whisky_absolute_score'] as int? ?? 100;
    final refWhisky = refWhiskyAsync.value;

    return Scaffold(
      appBar: AppBar(title: Text(tr('settings'))),
      body: SingleChildScrollView(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            24,
            24,
            24,
            MediaQuery.paddingOf(context).bottom + 100,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Language Selection Card
              _buildSectionHeader(tr('language')),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Icon(Icons.language, color: AppTheme.primary),
                      DropdownButton<String>(
                        value: langCode,
                        dropdownColor: AppTheme.surfaceElevated,
                        underline: const SizedBox(),
                        items: [
                          DropdownMenuItem(
                            value: 'tr',
                            child: Text(tr('turkish')),
                          ),
                          DropdownMenuItem(
                            value: 'en',
                            child: Text(tr('english')),
                          ),
                        ],
                        onChanged: (String? newValue) {
                          if (newValue != null) {
                            ref
                                .read(localizationProvider.notifier)
                                .setLanguage(newValue);
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Account (sign in / sync / sign out)
              _buildSectionHeader(langCode == 'tr' ? 'Hesap' : 'Account'),
              const SizedBox(height: 12),
              _buildAccountCard(langCode),
              const SizedBox(height: 32),

              // Reference Configuration Card
              _buildSectionHeader(tr('settings_100_pt_ref')),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (refWhisky == null)
                        Text(
                          tr('no_reference_selected'),
                          style: const TextStyle(color: AppTheme.textSecondary),
                        )
                      else ...[
                        Text(
                          refWhisky.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                            color: AppTheme.primary,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          tr('reference_absolute_value', [referenceScore]),
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _changeReferenceWhisky,
                          icon: const Icon(
                            Icons.swap_horiz,
                            color: AppTheme.primary,
                          ),
                          label: Text(
                            tr('change_reference_whisky'),
                            style: const TextStyle(color: AppTheme.primary),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: AppTheme.primary),
                          ),
                        ),
                      ),
                      if (refWhisky != null) ...[
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: OutlinedButton.icon(
                            onPressed: _isLoading
                                ? null
                                : _clearReferenceWhisky,
                            icon: const Icon(
                              Icons.delete_outline,
                              color: AppTheme.error,
                            ),
                            label: Text(
                              tr('remove_reference_whisky'),
                              style: const TextStyle(color: AppTheme.error),
                            ),
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: AppTheme.error),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Cache settings
              _buildSectionHeader(tr('cache_management')),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        tr('cache_desc'),
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _isLoading ? null : _clearCache,
                          icon: const Icon(Icons.delete_sweep),
                          label: Text(tr('clear_cache')),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.error,
                            foregroundColor: AppThemeColors.parchment,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Legal & Age verification
              _buildSectionHeader(
                langCode == 'tr' ? 'Yasal / Yaş Doğrulaması' : 'Legal / Age',
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.verified_user,
                            color: AppTheme.primary,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              age.isAllowed
                                  ? (langCode == 'tr'
                                        ? 'Ülke: ${age.country}  ·  Asgari yasal yaş: ${age.minAge}'
                                        : 'Country: ${age.country}  ·  Minimum legal age: ${age.minAge}')
                                  : (langCode == 'tr'
                                        ? 'Doğrulama bekleniyor'
                                        : 'Verification pending'),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                color: AppTheme.textPrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        langCode == 'tr'
                            ? 'Uygulama yalnızca ülkesinin yasal içki yaşını doldurmuş yetişkinlere yöneliktir. Ölçülü ve sorumlu tüketim esastır.'
                            : 'App is intended for adults of legal drinking age in their country. Drink responsibly.',
                        style: const TextStyle(
                          color: AppTheme.textMuted,
                          fontSize: 12,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _reverifyAge,
                          icon: const Icon(
                            Icons.refresh,
                            color: AppTheme.primary,
                          ),
                          label: Text(
                            langCode == 'tr'
                                ? 'Yeniden doğrula'
                                : 'Re-verify age',
                            style: const TextStyle(color: AppTheme.primary),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: AppTheme.primary),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontWeight: FontWeight.bold,
        fontSize: 16,
        color: AppTheme.secondary,
      ),
    );
  }
}
