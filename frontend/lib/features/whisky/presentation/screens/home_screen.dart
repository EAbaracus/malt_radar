import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import '../controllers/whisky_providers.dart';
import '../../domain/models/whisky.dart';
import 'detail_screen.dart';
import 'settings_screen.dart';
import '../widgets/glass_container.dart';

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
      backgroundColor: Colors.transparent,
      builder: (context) {
        return GlassContainer(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(30)),
          padding: EdgeInsets.only(
            left: 24, 
            right: 24, 
            top: 28, 
            bottom: MediaQuery.of(context).padding.bottom + 24
          ),
          opacity: 0.8,
          color: AppTheme.background,
          blur: 20,
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
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        color: AppTheme.primary,
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
                  style: const TextStyle(color: AppTheme.accent),
                ),
              const SizedBox(height: 20),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  if (whisky.country != null) _buildPreviewTag('Köken', whisky.country!),
                  if (whisky.age != null) _buildPreviewTag('Yaş', '${whisky.age} Yıl'),
                  if (whisky.abv != null) _buildPreviewTag('Alkol', '%${whisky.abv}'),
                  if (whisky.caskType != null) _buildPreviewTag('Fıçı', whisky.caskType!),
                ],
              ),
              if (whisky.tastingNotes.isNotEmpty) ...[
                const SizedBox(height: 24),
                Text('Tadım Notları', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: whisky.tastingNotes.take(4).map((n) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                    ),
                    child: Text(n, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13)),
                  )).toList(),
                ),
              ],
              const SizedBox(height: 36),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pop(context);
                    _addExternalWhisky(whisky);
                  },
                  icon: const Icon(Icons.add_circle_outline),
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
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.surfaceElevated.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold, fontSize: 13)),
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
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
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
      body: Container(
        // Modern gradient background
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(-0.8, -0.6),
            radius: 1.5,
            colors: [
              Color(0xFF1E1E2C), // A lighter hint at top left
              AppTheme.background,
              Color(0xFF040406),
            ],
          ),
        ),
        child: SafeArea(
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
                                letterSpacing: 3.0,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Kişisel Viski Kütüphanesi',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppTheme.textSecondary,
                              ),
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        IconButton(
                          icon: Icon(
                            isFavoritesOnly ? Icons.star : Icons.star_border,
                            color: AppTheme.primary,
                            size: 28,
                          ),
                          onPressed: () {
                            ref.read(favoritesOnlyProvider.notifier).state = !isFavoritesOnly;
                          },
                          tooltip: 'Sadece Favoriler',
                        ),
                        IconButton(
                          icon: const Icon(
                            Icons.settings_outlined,
                            color: AppTheme.textSecondary,
                            size: 28,
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
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                child: Autocomplete<Whisky>(
                  optionsBuilder: (TextEditingValue textEditingValue) async {
                    return _searchOnlineAutocomplete(textEditingValue.text);
                  },
                  displayStringForOption: (option) => option.name,
                  onSelected: (selection) {
                    _showWhiskyPreview(context, selection);
                  },
                  fieldViewBuilder: (context, controller, focusNode, onEditingComplete) {
                    return GlassContainer(
                      padding: EdgeInsets.zero,
                      blur: 15,
                      opacity: 0.1,
                      borderRadius: BorderRadius.circular(16),
                      child: TextField(
                        controller: controller,
                        focusNode: focusNode,
                        onChanged: (value) {
                          ref.read(searchQueryProvider.notifier).state = value;
                        },
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: 'Viski ara (Kütüphane & İnternet)...',
                          prefixIcon: const Icon(Icons.search, color: AppTheme.primary),
                          suffixIcon: controller.text.isNotEmpty
                              ? IconButton(
                                  icon: const Icon(Icons.clear, color: AppTheme.textSecondary),
                                  onPressed: () {
                                    controller.clear();
                                    ref.read(searchQueryProvider.notifier).state = '';
                                  },
                                )
                              : null,
                          filled: false,
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: const BorderSide(color: AppTheme.primary, width: 1.5),
                          ),
                        ),
                      ),
                    );
                  },
                  optionsViewBuilder: (context, onSelected, options) {
                    return Align(
                      alignment: Alignment.topLeft,
                      child: Container(
                        margin: const EdgeInsets.only(top: 8),
                        child: GlassContainer(
                          blur: 20,
                          opacity: 0.4,
                          color: AppTheme.surfaceElevated,
                          borderRadius: BorderRadius.circular(16),
                          child: ConstrainedBox(
                            constraints: BoxConstraints(
                              maxHeight: 320, 
                              maxWidth: MediaQuery.of(context).size.width - 48
                            ),
                            child: ListView.separated(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              shrinkWrap: true,
                              itemCount: options.length,
                              separatorBuilder: (context, index) => Divider(
                                color: Colors.white.withValues(alpha: 0.05),
                                height: 1,
                              ),
                              itemBuilder: (BuildContext context, int index) {
                                final option = options.elementAt(index);
                                return ListTile(
                                  leading: Container(
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: AppTheme.primary.withValues(alpha: 0.1),
                                      shape: BoxShape.circle,
                                    ),
                                    child: const Icon(Icons.public, color: AppTheme.primary, size: 20),
                                  ),
                                  title: Text(option.name, style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.bold)),
                                  subtitle: Text('${option.category ?? "Single Malt"} • ${option.country ?? "Scotland"}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                                  onTap: () => onSelected(option),
                                );
                              },
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),

              if (_isAdding)
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 24),
                  child: LinearProgressIndicator(color: AppTheme.primary, backgroundColor: Colors.transparent),
                ),

              // Whiskies List
              Expanded(
                child: whiskiesAsync.when(
                  data: (whiskies) {
                    if (whiskies.isEmpty) {
                      final query = ref.watch(searchQueryProvider);
                      return _buildEmptyState(context, isFavoritesOnly, query);
                    }
                    return ListView.builder(
                      physics: const BouncingScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(24, 4, 24, 24),
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
              size: 80,
              color: AppTheme.textMuted.withValues(alpha: 0.5),
            ),
            const SizedBox(height: 24),
            Text(
              isFavoritesOnly
                  ? 'Favori viskiniz bulunmuyor.'
                  : 'Kütüphanenizde eşleşen viski bulunamadı.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: AppTheme.textPrimary,
                  ),
            ),
            if (!isFavoritesOnly && query.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Lütfen aramaya devam edin.\nİnternet arama sonuçları üstteki menüde belirecektir.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 14),
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
        child: GlassContainer(
          blur: 10,
          opacity: 0.08,
          borderRadius: BorderRadius.circular(20),
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Gold/Amber Icon with glow
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppTheme.accent, AppTheme.primary],
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primary.withValues(alpha: 0.3),
                      blurRadius: 15,
                      offset: const Offset(0, 5),
                    )
                  ],
                ),
                child: const Icon(
                  Icons.local_bar,
                  color: AppTheme.background,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),

              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Hero(
                      tag: 'whisky-name-${whisky.id}',
                      child: Material(
                        color: Colors.transparent,
                        child: Text(
                          whisky.name,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                color: AppTheme.textPrimary,
                                fontSize: 19,
                              ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      whisky.category ?? 'Single Malt',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppTheme.secondary,
                            letterSpacing: 0.5,
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
                                color: Colors.white.withValues(alpha: 0.05),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
                              ),
                              child: Text(
                                note,
                                style: const TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 11,
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
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.15),
                        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.star, color: AppTheme.primary, size: 14),
                          const SizedBox(width: 4),
                          Text(
                            '$relativeScore',
                            style: const TextStyle(
                              color: AppTheme.primary,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    const Text(
                      'Puanlanmadı',
                      style: TextStyle(
                        color: AppTheme.textMuted,
                        fontStyle: FontStyle.italic,
                        fontSize: 12,
                      ),
                    ),
                  const SizedBox(height: 12),
                  // Favorite icon
                  Icon(
                    whisky.isFavorite ? Icons.star : Icons.star_border,
                    color: whisky.isFavorite ? AppTheme.accent : AppTheme.textMuted.withValues(alpha: 0.3),
                    size: 24,
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
