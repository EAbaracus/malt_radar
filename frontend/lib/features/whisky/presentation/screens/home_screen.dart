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
  final _searchController = TextEditingController();
  List<Whisky> _onlineResults = [];
  bool _isSearchingOnline = false;
  bool _hasSearchedOnline = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _searchOnline(String query) async {
    if (query.isEmpty) return;
    setState(() {
      _isSearchingOnline = true;
      _hasSearchedOnline = true;
    });

    final repository = ref.read(whiskyRepositoryProvider);
    final results = await repository.searchExternalWhiskies(query);

    setState(() {
      _onlineResults = results;
      _isSearchingOnline = false;
    });
  }

  void _clearOnlineSearch() {
    setState(() {
      _onlineResults = [];
      _hasSearchedOnline = false;
    });
  }

  void _addExternalWhisky(Whisky whisky) async {
    setState(() {
      _isSearchingOnline = true;
    });
    
    final repository = ref.read(whiskyRepositoryProvider);
    final localId = await repository.addWhiskyToLibrary(whisky);

    setState(() {
      _isSearchingOnline = false;
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

            // Search Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: TextField(
                controller: _searchController,
                onChanged: (value) {
                  ref.read(searchQueryProvider.notifier).state = value;
                  _clearOnlineSearch();
                },
                decoration: InputDecoration(
                  hintText: 'Kütüphanenizde arayın...',
                  prefixIcon: const Icon(Icons.search, color: AppTheme.textSecondary),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, color: AppTheme.textSecondary),
                          onPressed: () {
                            _searchController.clear();
                            ref.read(searchQueryProvider.notifier).state = '';
                            _clearOnlineSearch();
                          },
                        )
                      : null,
                ),
              ),
            ),

            // Online Search Indicator
            if (_isSearchingOnline)
              const LinearProgressIndicator(color: AppTheme.primary, backgroundColor: AppTheme.background),

            // Whiskies List / Online results
            Expanded(
              child: _hasSearchedOnline
                  ? _buildOnlineResultsSection(referenceScore)
                  : whiskiesAsync.when(
                      data: (whiskies) {
                        if (whiskies.isEmpty) {
                          return _buildEmptyState(context, isFavoritesOnly);
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

  Widget _buildEmptyState(BuildContext context, bool isFavoritesOnly) {
    final query = _searchController.text.trim();
    
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
                    color: AppTheme.textSecondary,
                    fontSize: 16,
                  ),
            ),
            if (!isFavoritesOnly && query.length >= 2) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () => _searchOnline(query),
                icon: const Icon(Icons.cloud_download),
                label: const Text('İNTERNETTE ARA'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildOnlineResultsSection(int referenceScore) {
    if (_onlineResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, size: 64, color: AppTheme.textMuted),
            const SizedBox(height: 16),
            const Text(
              'İnternette de eşleşen sonuç bulunamadı.',
              style: TextStyle(color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 16),
            TextButton(
              onPressed: _clearOnlineSearch,
              child: const Text('Kütüphaneme Geri Dön', style: TextStyle(color: AppTheme.primary)),
            )
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'İnternet Arama Sonuçları',
                style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.secondary, fontSize: 16),
              ),
              TextButton(
                onPressed: _clearOnlineSearch,
                child: const Text('Kapat', style: TextStyle(color: AppTheme.textSecondary)),
              )
            ],
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
            itemCount: _onlineResults.length,
            itemBuilder: (context, index) {
              final whisky = _onlineResults[index];
              return Card(
                child: ListTile(
                  leading: const Icon(Icons.public, color: AppTheme.primary),
                  title: Text(whisky.name),
                  subtitle: Text('${whisky.country ?? "Scotland"} • ${whisky.defaultPrice} ${whisky.currency}'),
                  trailing: IconButton(
                    icon: const Icon(Icons.add_circle_outline, color: AppTheme.primary, size: 28),
                    onPressed: () => _addExternalWhisky(whisky),
                    tooltip: 'Kütüphaneme Ekle',
                  ),
                ),
              );
            },
          ),
        ),
      ],
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
