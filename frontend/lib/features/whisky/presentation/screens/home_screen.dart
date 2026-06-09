import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import '../controllers/whisky_providers.dart';
import '../../domain/models/whisky.dart';
import 'detail_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _isAdding = false;
  Timer? _debounce;
  String _lastQuery = '';
  Iterable<Whisky> _lastOptions = [];

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<Iterable<Whisky>> _searchOnlineAutocomplete(String query) async {
    final trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) return const Iterable<Whisky>.empty();
    
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    
    final completer = Completer<Iterable<Whisky>>();
    
    _debounce = Timer(const Duration(milliseconds: 500), () async {
      if (trimmedQuery == _lastQuery) {
        completer.complete(_lastOptions);
        return;
      }
      
      final repository = ref.read(whiskyRepositoryProvider);
      try {
        final results = await repository.searchExternalWhiskies(trimmedQuery);
        _lastQuery = trimmedQuery;
        _lastOptions = results;
        completer.complete(results);
      } catch (e) {
        completer.complete(const Iterable<Whisky>.empty());
      }
    });
    
    return completer.future;
  }

  void _showWhiskyPreview(BuildContext context, Whisky whisky) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            left: 24, 
            right: 24, 
            top: 24, 
            bottom: MediaQuery.of(context).padding.bottom + 24
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      whisky.name,
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: AppTheme.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: AppTheme.textSecondary),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (whisky.category != null || whisky.region != null)
                Text(
                  '${whisky.category ?? ''} ${whisky.region != null ? "• ${whisky.region}" : ""}',
                  style: const TextStyle(color: AppTheme.secondary),
                ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (whisky.country != null) _buildPreviewTag('Köken', whisky.country!),
                  if (whisky.age != null) _buildPreviewTag('Yaş', '${whisky.age} Yıl'),
                  if (whisky.abv != null) _buildPreviewTag('Alkol', '%${whisky.abv}'),
                  if (whisky.caskType != null) _buildPreviewTag('Fıçı', whisky.caskType!),
                  if (whisky.defaultPrice != null && whisky.defaultPrice! > 0) 
                    _buildPreviewTag('Fiyat', '${whisky.defaultPrice} ${whisky.currency}'),
                ],
              ),
              if (whisky.tastingNotes.isNotEmpty) ...[
                const SizedBox(height: 16),
                const Text('Tadım Notları', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primary)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: whisky.tastingNotes.take(4).map((n) => Chip(
                    label: Text(n, style: const TextStyle(fontSize: 12)),
                    visualDensity: VisualDensity.compact,
                  )).toList(),
                ),
              ],
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pop(context);
                    _addExternalWhisky(whisky);
                  },
                  icon: const Icon(Icons.add),
                  label: const Text('KÜTÜPHANEME EKLE'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPreviewTag(String label, String value) {
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

  void _addExternalWhisky(Whisky whisky) async {
    setState(() {
      _isAdding = true;
    });
    
    final repository = ref.read(whiskyRepositoryProvider);
    final localId = await repository.addWhiskyToLibrary(whisky);

    setState(() {
      _isAdding = false;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${whisky.name} kütüphaneye eklendi.'),
          backgroundColor: AppTheme.primary,
          duration: const Duration(seconds: 2),
        ),
      );
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => DetailScreen(whiskyId: localId)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final whiskiesAsync = ref.watch(whiskiesStreamProvider);
    final isFavoritesOnly = ref.watch(favoritesOnlyProvider);
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);

    final settings = settingsAsync.value ?? {};
    final referenceScore = settings['reference_whisky_absolute_score'] as int? ?? 100;

    return Scaffold(
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header / App Title
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'MALT RADAR',
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                              color: AppTheme.primary,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 2.0,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Kişisel Viski Kütüphanesi',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppTheme.textSecondary,
                            ),
                      ),
                    ],
                  ),
                  // Header Actions (Favorites + Settings)
                  Row(
                    children: [
                      IconButton(
                        icon: Icon(
                          isFavoritesOnly ? Icons.star : Icons.star_border,
                          color: AppTheme.primary,
                          size: 26,
                        ),
                        onPressed: () {
                          ref.read(favoritesOnlyProvider.notifier).state = !isFavoritesOnly;
                        },
                        tooltip: 'Sadece Favoriler',
                      ),
                      IconButton(
                        icon: const Icon(
                          Icons.settings,
                          color: AppTheme.textSecondary,
                          size: 26,
                        ),
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (context) => const SettingsScreen()),
                          );
                        },
                        tooltip: 'Ayarlar',
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Search Bar (Autocomplete)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: Autocomplete<Whisky>(
                optionsBuilder: (TextEditingValue textEditingValue) async {
                  return _searchOnlineAutocomplete(textEditingValue.text);
                },
                displayStringForOption: (option) => option.name,
                onSelected: (selection) {
                  _showWhiskyPreview(context, selection);
                },
                fieldViewBuilder: (context, controller, focusNode, onEditingComplete) {
                  return TextField(
                    controller: controller,
                    focusNode: focusNode,
                    onChanged: (value) {
                      ref.read(searchQueryProvider.notifier).state = value;
                    },
                    decoration: InputDecoration(
                      hintText: 'Viski ara (Kütüphane & İnternet)...',
                      prefixIcon: const Icon(Icons.search, color: AppTheme.textSecondary),
                      suffixIcon: controller.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear, color: AppTheme.textSecondary),
                              onPressed: () {
                                controller.clear();
                                ref.read(searchQueryProvider.notifier).state = '';
                              },
                            )
                          : null,
                    ),
                  );
                },
                optionsViewBuilder: (context, onSelected, options) {
                  return Align(
                    alignment: Alignment.topLeft,
                    child: Material(
                      elevation: 8.0,
                      borderRadius: BorderRadius.circular(12),
                      color: AppTheme.surfaceElevated,
                      child: ConstrainedBox(
                        constraints: BoxConstraints(
                          maxHeight: 300, 
                          maxWidth: MediaQuery.of(context).size.width - 48
                        ),
                        child: ListView.builder(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          shrinkWrap: true,
                          itemCount: options.length,
                          itemBuilder: (BuildContext context, int index) {
                            final option = options.elementAt(index);
                            return ListTile(
                              leading: const Icon(Icons.public, color: AppTheme.primary),
                              title: Text(option.name, style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold)),
                              subtitle: Text('${option.category ?? "Single Malt"} • ${option.country ?? "Scotland"}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                              onTap: () => onSelected(option),
                            );
                          },
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),

            if (_isAdding)
              const LinearProgressIndicator(color: AppTheme.primary, backgroundColor: AppTheme.background),

            // Whiskies List
            Expanded(
              child: whiskiesAsync.when(
                data: (whiskies) {
                  if (whiskies.isEmpty) {
                    final query = ref.watch(searchQueryProvider);
                    return _buildEmptyState(context, isFavoritesOnly, query);
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
                    itemCount: whiskies.length,
                    itemBuilder: (context, index) {
                      final whisky = whiskies[index];
                      return _buildWhiskyCard(context, ref, whisky, referenceScore);
                    },
                  );
                },
                loading: () => const Center(
                  child: CircularProgressIndicator(color: AppTheme.primary),
                ),
                error: (error, stackTrace) => Center(
                  child: Text(
                    'Veritabanı hatası: $error',
                    style: const TextStyle(color: AppTheme.error),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, bool isFavoritesOnly, String query) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isFavoritesOnly ? Icons.star_border : Icons.search_off,
              size: 64,
              color: AppTheme.textMuted,
            ),
            const SizedBox(height: 16),
            Text(
              isFavoritesOnly
                  ? 'Favori viskiniz bulunmuyor.'
                  : 'Kütüphanenizde eşleşen viski bulunamadı.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppTheme.textPrimary,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
            ),
            if (!isFavoritesOnly && query.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Lütfen aramaya devam edin.\nİnternet arama sonuçları üstteki açılır menüde (dropdown) belirecektir.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildWhiskyCard(BuildContext context, WidgetRef ref, Whisky whisky, int referenceScore) {
    // Relative score calculation
    int? relativeScore;
    if (whisky.personalScore > 0 && referenceScore > 0) {
      relativeScore = ((whisky.personalScore / referenceScore) * 100).round();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: GestureDetector(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => DetailScreen(whiskyId: whisky.id),
            ),
          );
        },
        child: Card(
          clipBehavior: Clip.antiAlias,
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppTheme.surface,
                  AppTheme.surfaceElevated.withValues(alpha: 0.4),
                ],
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  // Gold/Amber Icon
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.primary.withValues(alpha: 0.2)),
                    ),
                    child: const Icon(
                      Icons.local_bar,
                      color: AppTheme.primary,
                      size: 26,
                    ),
                  ),
                  const SizedBox(width: 16),

                  // Info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          whisky.name,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                color: AppTheme.textPrimary,
                                fontSize: 18,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          whisky.category ?? 'Single Malt',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: AppTheme.secondary,
                              ),
                        ),
                        const SizedBox(height: 8),
                        // Tasting notes tags
                        if (whisky.tastingNotes.isNotEmpty)
                          SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: whisky.tastingNotes.take(3).map((note) {
                                return Container(
                                  margin: const EdgeInsets.only(right: 6),
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppTheme.background,
                                    borderRadius: BorderRadius.circular(6),
                                    border: Border.all(color: AppTheme.textMuted.withValues(alpha: 0.2)),
                                  ),
                                  child: Text(
                                    note,
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          color: AppTheme.textSecondary,
                                          fontSize: 10,
                                        ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                      ],
                    ),
                  ),

                  // Score
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      // Relative Score Badge
                      if (relativeScore != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppTheme.primary,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.star, color: AppTheme.background, size: 12),
                              const SizedBox(width: 2),
                              Text(
                                '$relativeScore',
                                style: const TextStyle(
                                  color: AppTheme.background,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        Text(
                          'Puanlanmadı',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                fontStyle: FontStyle.italic,
                              ),
                        ),
                      const SizedBox(height: 12),
                      // Favorite icon
                      Icon(
                        whisky.isFavorite ? Icons.star : Icons.star_border,
                        color: whisky.isFavorite ? AppTheme.primary : AppTheme.textMuted.withValues(alpha: 0.4),
                        size: 22,
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
