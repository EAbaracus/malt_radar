import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import '../controllers/whisky_providers.dart';
import '../../domain/models/whisky.dart';

import '../../../../core/localization/localization_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _isLoading = false;

  void _clearCache() async {
    setState(() {
      _isLoading = true;
    });

    final repository = ref.read(whiskyRepositoryProvider);
    await repository.clearCache();

    setState(() {
      _isLoading = false;
    });

    if (mounted) {
      final tr = ref.read(trProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(tr('cache_cleared')),
          backgroundColor: AppTheme.primary,
        ),
      );
    }
  }

  void _changeReferenceWhisky() async {
    final repository = ref.read(whiskyRepositoryProvider);
    final db = ref.read(appDatabaseProvider);
    final tr = ref.read(trProvider);
    
    final list = await db.select(db.whiskies).get();
    final localWhiskies = list.map((e) => Whisky.fromEntities(whisky: e)).toList();

    if (localWhiskies.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('add_whisky_first'))),
        );
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
                      style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary, fontSize: 18),
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: ListView.builder(
                        itemCount: localWhiskies.length,
                        itemBuilder: (context, index) {
                          final w = localWhiskies[index];
                          return ListTile(
                            title: Text(w.name),
                            trailing: const Icon(Icons.check_circle_outline, color: AppTheme.primary),
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
                                            Text(w.name, style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary)),
                                            const SizedBox(height: 16),
                                            Text(tr('reference_absolute_score', [tempScore])),
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
                                            onPressed: () => Navigator.pop(context),
                                            child: Text(tr('cancel')),
                                          ),
                                          ElevatedButton(
                                            onPressed: () async {
                                              await repository.setReferenceWhisky(w.id, tempScore);
                                              await repository.updatePersonalScore(w.id, tempScore);
                                              
                                              if (context.mounted) {
                                                Navigator.pop(context);
                                                Navigator.pop(context);
                                                
                                                ScaffoldMessenger.of(context).showSnackBar(
                                                  SnackBar(content: Text(tr('reference_updated', [w.name]))),
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

  @override
  Widget build(BuildContext context) {
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);
    final refWhiskyAsync = ref.watch(referenceWhiskyModelProvider);
    final tr = ref.watch(trProvider);
    final langCode = ref.watch(localizationProvider);

    final settings = settingsAsync.value ?? {};
    final referenceScore = settings['reference_whisky_absolute_score'] as int? ?? 100;
    final refWhisky = refWhiskyAsync.value;

    return Scaffold(
      appBar: AppBar(
        title: Text(tr('settings')),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
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
                          DropdownMenuItem(value: 'tr', child: Text(tr('turkish'))),
                          DropdownMenuItem(value: 'en', child: Text(tr('english'))),
                        ],
                        onChanged: (String? newValue) {
                          if (newValue != null) {
                            ref.read(localizationProvider.notifier).setLanguage(newValue);
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
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
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.primary),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          tr('reference_absolute_value', [referenceScore]),
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                        ),
                      ],
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _changeReferenceWhisky,
                          icon: const Icon(Icons.swap_horiz, color: AppTheme.primary),
                          label: Text(tr('change_reference_whisky'), style: const TextStyle(color: AppTheme.primary)),
                          style: OutlinedButton.styleFrom(side: const BorderSide(color: AppTheme.primary)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Data Providers Section
              _buildSectionHeader(tr('data_sources')),
              const SizedBox(height: 12),
              Card(
                color: AppTheme.surface,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      _SourceTile(name: 'WhiskyHunter API', status: tr('active_mock')),
                      const Divider(),
                      _SourceTile(name: 'WhiskyEdition API', status: tr('active_mock')),
                      const Divider(),
                      _SourceTile(name: tr('manual_entry_module'), status: tr('active')),
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
                        style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _isLoading ? null : _clearCache,
                          icon: const Icon(Icons.delete_sweep),
                          label: Text(tr('clear_cache')),
                          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error, foregroundColor: Colors.white),
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
      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.secondary),
    );
  }
}

class _SourceTile extends StatelessWidget {
  final String name;
  final String status;
  const _SourceTile({required this.name, required this.status});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(name, style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.success.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppTheme.success.withValues(alpha: 0.2)),
            ),
            child: Text(
              status,
              style: const TextStyle(color: AppTheme.success, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          )
        ],
      ),
    );
  }
}
