import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import '../controllers/whisky_providers.dart';
import '../../domain/models/whisky.dart';

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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Arama önbelleği temizlendi. Puan ve favorileriniz korundu.'),
          backgroundColor: AppTheme.primary,
        ),
      );
    }
  }

  void _changeReferenceWhisky() async {
    // Show a dialog/bottom sheet to select a new reference from local database
    final repository = ref.read(whiskyRepositoryProvider);
    final db = ref.read(appDatabaseProvider);
    
    // Fetch all local whiskies
    final list = await db.select(db.whiskies).get();
    final localWhiskies = list.map((e) => Whisky.fromEntities(whisky: e)).toList();

    if (localWhiskies.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Önce kütüphanenize bir viski ekleyin.')),
        );
      }
      return;
    }

    if (mounted) {
      showModalBottomSheet(
        context: context,
        backgroundColor: AppTheme.surface,
        builder: (context) {
          int tempScore = 90;
          return StatefulBuilder(
            builder: (context, setModalState) {
              return Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Yeni Referans Viski Seçin',
                      style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary, fontSize: 18),
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
                              // Show score configuration
                              showDialog(
                                context: context,
                                builder: (context) {
                                  return StatefulBuilder(
                                    builder: (context, setDialogState) {
                                      return AlertDialog(
                                        backgroundColor: AppTheme.surface,
                                        title: const Text('Referans Puanı Ayarla'),
                                        content: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Text(w.name, style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary)),
                                            const SizedBox(height: 16),
                                            Text('Mutlak Puan: $tempScore / 100'),
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
                                            child: const Text('İPTAL'),
                                          ),
                                          ElevatedButton(
                                            onPressed: () async {
                                              await repository.setReferenceWhisky(w.id, tempScore);
                                              // Ensure score matches in scores table
                                              await repository.updatePersonalScore(w.id, tempScore);
                                              
                                              if (context.mounted) {
                                                Navigator.pop(context); // Close dialog
                                                Navigator.pop(context); // Close bottom sheet
                                                
                                                ScaffoldMessenger.of(context).showSnackBar(
                                                  SnackBar(content: Text('Referans viski ${w.name} olarak güncellendi.')),
                                                );
                                              }
                                            },
                                            child: const Text('KAYDET'),
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

    final settings = settingsAsync.value ?? {};
    final referenceScore = settings['reference_whisky_absolute_score'] as int? ?? 100;
    final refWhisky = refWhiskyAsync.value;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Ayarlar'),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Reference Configuration Card
              _buildSectionHeader('100 Puan Referansı'),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (refWhisky == null)
                        const Text(
                          'Referans viski seçilmemiş.',
                          style: TextStyle(color: AppTheme.textSecondary),
                        )
                      else ...[
                        Text(
                          refWhisky.name,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.primary),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Referans Mutlak Değeri: $referenceScore / 100 (Bu viski 100 puan kabul edilir)',
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                        ),
                      ],
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _changeReferenceWhisky,
                          icon: const Icon(Icons.swap_horiz, color: AppTheme.primary),
                          label: const Text('REFERANS VİSKİYİ DEĞİŞTİR', style: TextStyle(color: AppTheme.primary)),
                          style: OutlinedButton.styleFrom(side: const BorderSide(color: AppTheme.primary)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Data Providers Section
              _buildSectionHeader('Veri Kaynakları (Backend API)'),
              const SizedBox(height: 12),
              const Card(
                color: AppTheme.surface,
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    children: [
                      _SourceTile(name: 'WhiskyHunter API', status: 'Aktif (Mock)'),
                      Divider(),
                      _SourceTile(name: 'WhiskyEdition API', status: 'Aktif (Mock)'),
                      Divider(),
                      _SourceTile(name: 'Manuel Girdi Modülü', status: 'Aktif'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Cache settings
              _buildSectionHeader('Önbellek ve Veri Yönetimi'),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'İnternetten aradığınız ve kütüphaneye kaydetmediğiniz viskilerin önbelleğini temizleyin. Puanladığınız ve favorilere eklediğiniz veriler korunur.',
                        style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _isLoading ? null : _clearCache,
                          icon: const Icon(Icons.delete_sweep),
                          label: const Text('ÖNBELLEĞİ TEMİZLE'),
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
