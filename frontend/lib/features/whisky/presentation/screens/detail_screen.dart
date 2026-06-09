import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import '../controllers/whisky_providers.dart';

class DetailScreen extends ConsumerStatefulWidget {
  final int whiskyId;
  const DetailScreen({super.key, required this.whiskyId});

  @override
  ConsumerState<DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends ConsumerState<DetailScreen> {
  final _notesController = TextEditingController();
  int _score = 0;
  bool _initialized = false;
  List<Map<String, dynamic>> _prices = [];
  bool _isLoadingPrices = true;

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _loadPrices();
  }

  void _loadPrices() async {
    final repository = ref.read(whiskyRepositoryProvider);
    final whisky = await repository.getWhiskyById(widget.whiskyId);
    if (whisky != null) {
      final list = await repository.getWhiskyPrices(widget.whiskyId, whisky.externalId);
      setState(() {
        _prices = list;
        _isLoadingPrices = false;
      });
    }
  }

  void _saveNotesAndScore() async {
    final repository = ref.read(whiskyRepositoryProvider);
    await repository.updatePersonalNotes(widget.whiskyId, _notesController.text);
    await repository.updatePersonalScore(widget.whiskyId, _score);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Değerlendirme başarıyla kaydedildi.'),
          backgroundColor: AppTheme.primary,
        ),
      );
    }
  }

  void _showAddPriceDialog() {
    final priceController = TextEditingController();
    final sourceController = TextEditingController(text: 'Kişisel Takip');
    final sourceUrlController = TextEditingController(text: 'manuel');
    String selectedCurrency = 'TL';
    String selectedCountry = 'Türkiye';

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: AppTheme.surface,
          title: const Text('Fiyat Kaydı Ekle', style: TextStyle(color: AppTheme.primary)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: priceController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Fiyat'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: selectedCurrency,
                  decoration: const InputDecoration(labelText: 'Para Birimi'),
                  dropdownColor: AppTheme.surfaceElevated,
                  items: ['TL', 'USD', 'EUR', 'GBP'].map((c) {
                    return DropdownMenuItem(value: c, child: Text(c));
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) selectedCurrency = val;
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: selectedCountry,
                  decoration: const InputDecoration(labelText: 'Ülke'),
                  dropdownColor: AppTheme.surfaceElevated,
                  items: ['Türkiye', 'İskoçya', 'İngiltere', 'ABD', 'Japonya'].map((c) {
                    return DropdownMenuItem(value: c, child: Text(c));
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) selectedCountry = val;
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: sourceController,
                  decoration: const InputDecoration(labelText: 'Kaynak Mağaza/Site'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('İPTAL', style: TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () async {
                final double? pVal = double.tryParse(priceController.text);
                if (pVal == null || pVal <= 0) return;

                final repository = ref.read(whiskyRepositoryProvider);
                await repository.addManualPrice(
                  whiskyId: widget.whiskyId,
                  price: pVal,
                  currency: selectedCurrency,
                  country: selectedCountry,
                  sourceName: sourceController.text,
                  sourceUrl: sourceUrlController.text,
                );

                if (context.mounted) {
                  Navigator.pop(context);
                }
                _loadPrices();
              },
              child: const Text('EKLE'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final whiskyAsync = ref.watch(whiskyDetailProvider(widget.whiskyId));
    final allWhiskiesAsync = ref.watch(whiskiesStreamProvider);
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);
    final refWhiskyAsync = ref.watch(referenceWhiskyModelProvider);

    final settings = settingsAsync.value ?? {};
    final referenceScore = settings['reference_whisky_absolute_score'] as int? ?? 100;
    final referenceId = settings['reference_whisky_id'] as int?;
    final refWhisky = refWhiskyAsync.value;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Viski Detayı'),
        actions: [
          whiskyAsync.maybeWhen(
            data: (whisky) => whisky != null
                ? IconButton(
                    icon: Icon(
                      whisky.isFavorite ? Icons.star : Icons.star_border,
                      color: AppTheme.primary,
                      size: 28,
                    ),
                    onPressed: () {
                      ref.read(whiskyRepositoryProvider).toggleFavorite(whisky.id);
                    },
                  )
                : const SizedBox.shrink(),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
      body: whiskyAsync.when(
        data: (whisky) {
          if (whisky == null) {
            return const Center(child: Text('Viski bulunamadı.'));
          }

          if (!_initialized) {
            _notesController.text = whisky.personalNotes;
            _score = whisky.personalScore;
            _initialized = true;
            
            // Auto-fetch details if missing
            if (whisky.tastingNotes.isEmpty && whisky.externalId != null) {
              Future.microtask(() => ref.read(whiskyRepositoryProvider).fetchAndUpdateDetails(whisky.id, whisky.externalId!));
            }
          }

          final isReferenceWhisky = whisky.id == referenceId;
          
          // Calculate relative score based on global scores
          double? automatedRelativeScore;
          if (refWhisky != null && refWhisky.globalScore != null && refWhisky.globalScore! > 0 && whisky.globalScore != null) {
            automatedRelativeScore = (whisky.globalScore! / refWhisky.globalScore!) * referenceScore;
          }

          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title
                  Text(
                    whisky.name,
                    style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                          color: AppTheme.textPrimary,
                        ),
                  ),
                  const SizedBox(height: 16),

                  // Metadata tags in Grid/Wrap
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if (whisky.country != null) _buildMetaTag('Köken', whisky.country!),
                      if (whisky.region != null) _buildMetaTag('Bölge', whisky.region!),
                      if (whisky.category != null) _buildMetaTag('Kategori', whisky.category!),
                      if (whisky.age != null) _buildMetaTag('Yaş', '${whisky.age} Yıl'),
                      if (whisky.abv != null) _buildMetaTag('Alkol', '%${whisky.abv}'),
                      if (whisky.caskType != null) _buildMetaTag('Fıçı', whisky.caskType!),
                    ],
                  ),
                  const SizedBox(height: 32),

                  // Tasting Notes Section
                  if (whisky.tastingNotes.isNotEmpty) ...[
                    _buildSectionHeader(context, 'Tadım Notları', Icons.bubble_chart),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: whisky.tastingNotes.map((note) {
                        return Chip(
                          label: Text(note),
                          backgroundColor: AppTheme.surfaceElevated,
                          side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.2)),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 32),
                  ],

                  // Companion Suggestions Section
                  if (whisky.companionSuggestions.isNotEmpty) ...[
                    _buildSectionHeader(context, 'Eşlikçi Önerileri', Icons.restaurant),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: whisky.companionSuggestions.map((suggestion) {
                        return Chip(
                          label: Text(suggestion),
                          backgroundColor: AppTheme.surfaceElevated,
                          side: BorderSide(color: AppTheme.secondary.withValues(alpha: 0.2)),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 32),
                  ],

                  // Price History Section
                  _buildSectionHeader(context, 'Fiyat Bilgileri', Icons.sell),
                  const SizedBox(height: 12),
                  _isLoadingPrices
                      ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                      : Column(
                          children: [
                            if (_prices.isEmpty)
                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 8),
                                child: Text('Kayıtlı fiyat bulunmuyor.', style: TextStyle(color: AppTheme.textMuted)),
                              )
                            else
                              ListView.builder(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: _prices.length,
                                itemBuilder: (context, index) {
                                  final priceItem = _prices[index];
                                  final isManual = priceItem['is_manual'] as bool? ?? false;
                                  return Card(
                                    color: AppTheme.surfaceElevated,
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: ListTile(
                                      leading: Icon(
                                        isManual ? Icons.edit : Icons.sync,
                                        color: isManual ? AppTheme.secondary : AppTheme.primary,
                                      ),
                                      title: Text(
                                        '${priceItem['price']} ${priceItem['currency']}',
                                        style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                                      ),
                                      subtitle: Text(
                                        'Kaynak: ${priceItem['source_name']} (${priceItem['country']})',
                                        style: const TextStyle(fontSize: 12),
                                      ),
                                      trailing: Text(
                                        priceItem['fetched_at'].toString().split('T')[0],
                                        style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            const SizedBox(height: 8),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Expanded(
                                  child: Text(
                                    '* Fiyatlar tahmini veya internet kaynaklıdır.',
                                    style: TextStyle(color: AppTheme.textMuted, fontSize: 10, fontStyle: FontStyle.italic),
                                  ),
                                ),
                                TextButton.icon(
                                  onPressed: _showAddPriceDialog,
                                  icon: const Icon(Icons.add, size: 16),
                                  label: const Text('Fiyat Kaydı Ekle', style: TextStyle(fontSize: 12)),
                                  style: TextButton.styleFrom(foregroundColor: AppTheme.primary),
                                )
                              ],
                            ),
                          ],
                        ),
                  const SizedBox(height: 32),

                  // Divider
                  Divider(color: AppTheme.textMuted.withValues(alpha: 0.2)),
                  const SizedBox(height: 24),

                  // Similar Whiskies (Bunu Sevdiyseniz...)
                  allWhiskiesAsync.maybeWhen(
                    data: (allWhiskies) {
                      final similar = allWhiskies.where((w) => 
                        w.id != whisky.id && 
                        ((w.category != null && w.category == whisky.category) || 
                         (w.region != null && w.region == whisky.region))
                      ).take(3).toList();
                      
                      if (similar.isEmpty) return const SizedBox.shrink();
                      
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildSectionHeader(context, 'Bunu Sevdiyseniz...', Icons.recommend),
                          const SizedBox(height: 12),
                          const Text(
                            'Kütüphanenizdeki benzer kategorideki/bölgedeki viskiler:',
                            style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                          ),
                          const SizedBox(height: 8),
                          ...similar.map((sim) => Card(
                            color: AppTheme.surfaceElevated,
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              leading: const Icon(Icons.local_bar, color: AppTheme.primary),
                              title: Text(sim.name, style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                              subtitle: Text('${sim.category ?? ''} ${sim.region ?? ''}'),
                              onTap: () {
                                Navigator.pushReplacement(
                                  context,
                                  MaterialPageRoute(builder: (context) => DetailScreen(whiskyId: sim.id)),
                                );
                              },
                            ),
                          )),
                          const SizedBox(height: 24),
                          Divider(color: AppTheme.textMuted.withValues(alpha: 0.2)),
                          const SizedBox(height: 24),
                        ],
                      );
                    },
                    orElse: () => const SizedBox.shrink(),
                  ),

                  // Evaluation Section
                  _buildSectionHeader(context, 'Kişisel Değerlendirmeniz', Icons.edit_note),
                  const SizedBox(height: 24),

                  if (isReferenceWhisky) ...[
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
                      ),
                      child: Text(
                        'Bu viski sizin 100 puanlık referans viskinizdir.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: AppTheme.primary,
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],

                  // Ratings
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Mutlak Puanınız:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      Text(
                        _score > 0 ? '$_score / 100' : 'Puanlanmadı',
                        style: const TextStyle(fontSize: 18, color: AppTheme.secondary, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Slider(
                    value: _score.toDouble(),
                    min: 0,
                    max: 100,
                    divisions: 100,
                    label: _score.toString(),
                    onChanged: (val) {
                      setState(() {
                        _score = val.round();
                      });
                    },
                  ),

                  if (!isReferenceWhisky && automatedRelativeScore != null) ...[
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Otomatik Göreli Puan:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        Text(
                          '${automatedRelativeScore.toStringAsFixed(1)} / 100',
                          style: const TextStyle(fontSize: 22, color: AppTheme.primary, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Hesaplama: (Bu Viski Genel Puanı: ${whisky.globalScore} / Referans: ${refWhisky?.name} Genel Puanı: ${refWhisky?.globalScore}) * $referenceScore',
                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 11, fontStyle: FontStyle.italic),
                    ),
                  ] else if (!isReferenceWhisky && refWhisky != null) ...[
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Otomatik Göreli Puan:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                        const Text(
                          'Veri Yok',
                          style: TextStyle(fontSize: 18, color: AppTheme.textMuted, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Bu viskinin veya referansın genel puan verisi bulunmuyor.',
                      style: TextStyle(color: AppTheme.textMuted, fontSize: 11, fontStyle: FontStyle.italic),
                    ),
                  ],
                  const SizedBox(height: 24),

                  // Notes text field
                  const Text('Tadım ve Kişisel Notlar:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _notesController,
                    maxLines: 5,
                    decoration: const InputDecoration(
                      hintText: 'Koku, damak, bitiş notlarınızı yazın...',
                      alignLabelWithHint: true,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Save Button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _saveNotesAndScore,
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.save),
                          SizedBox(width: 8),
                          Text('DEĞERLENDİRMEYİ KAYDET'),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          );
        },
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppTheme.primary),
        ),
        error: (error, stackTrace) => Center(
          child: Text('Hata: $error', style: const TextStyle(color: AppTheme.error)),
        ),
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: AppTheme.primary, size: 20),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _buildMetaTag(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.textMuted.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$label: ', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
          Text(value, style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold, fontSize: 11)),
        ],
      ),
    );
  }
}
