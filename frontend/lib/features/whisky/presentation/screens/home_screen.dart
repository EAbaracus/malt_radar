import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import '../controllers/whisky_providers.dart';
import '../controllers/catalog_pagination.dart';
import '../../domain/models/whisky.dart';
import 'catalog_scroll_trigger.dart';
import '../../../../core/localization/localization_provider.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import 'detail_screen.dart';
import '../widgets/glass_container.dart';
import '../../../../core/presentation/widgets/cask_card.dart';
import '../../../../core/presentation/widgets/tasting_chip.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final ScrollController _scrollController = ScrollController();
  TextEditingController? _searchFieldController;

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  /// Header ("MALT RADAR") tap: return to the pristine home state —
  /// clear search, filters and favorites-only, scroll back to the top, and
  /// pop any pushed screens (detail etc.) above the home tab.
  void _resetToHome() {
    _searchFieldController?.clear();
    ref.read(searchQueryProvider.notifier).state = '';
    ref.read(selectedFiltersProvider.notifier).state = [];
    ref.read(favoritesOnlyProvider.notifier).state = false;
    // If a detail/setup screen was pushed on top of the tab shell, close it
    // so the user lands back on the searchable home catalog.
    Navigator.of(context).popUntil((route) => route.isFirst);
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        0,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
      );
    }
  }

  Future<Iterable<Whisky>> _searchOnlineAutocomplete(String query) async {
    final trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) return const Iterable<Whisky>.empty();

    final repository = ref.read(whiskyRepositoryProvider);
    try {
      // Search backend (includes both library and external). No debounce:
      // every keystroke gets a fresh future — Autocomplete drops stale
      // futures itself, and a cancelled debounce would leave the dropdown
      // stuck waiting on a completer that never completes.
      return await repository.searchBackend(trimmedQuery);
    } catch (e) {
      debugPrint('search autocomplete failed: $e');
      return const Iterable<Whisky>.empty();
    }
  }

  void _showWhiskyPreview(BuildContext context, Whisky whisky) {
    // BUGFIX (2026-08-10): DbWhiskyMapper API sonuçlarına SENTEZ lokal id atar
    // (whiskyId.hashCode % 1000000) — "id > 0" kontrolü her arama sonucunda
    // true dönüp backendId'siz DetailScreen açıyordu; sentez id lokal DB'de
    // olmadığından "whisky not found" üretiyordu.
    // Gerçek lokal kayıt yalnızca externalId'sizdir (lokal DB kökenli).
    if (whisky.id > 0 && whisky.externalId == null) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => DetailScreen(whiskyId: whisky.id)),
      );
      return;
    }

    // API sonucu: backendId ile doğrudan detail — radar/evidence canlı API'den
    // (kart yolundaki _buildWhiskyCard davranışıyla tutarlı).
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => DetailScreen(
          whiskyId: whisky.id,
          backendId: whisky.externalId,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    final whiskiesAsync = ref.watch(whiskiesStreamProvider);
    final isFavoritesOnly = ref.watch(favoritesOnlyProvider);
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);

    final settings = settingsAsync.value ?? {};
    final referenceScore = settings['reference_whisky_absolute_score'] as int? ?? 100;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(-0.8, -0.6),
            radius: 1.5,
            colors: [
              AppTheme.surfaceElevated,
              AppTheme.background,
              AppTheme.surface,
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    // Brand header: tapping it resets to the pristine home
                    // state (clear search/filters/favorites, scroll to top).
                    GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: _resetToHome,
                      child: Column(
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
                            tr('whisky_library'),
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: AppTheme.textSecondary,
                                ),
                          ),
                        ],
                      ),
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
                          tooltip: tr('favorites_only'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                child: Autocomplete<Whisky>(
                  optionsBuilder: (TextEditingValue textEditingValue) async {
                    return _searchOnlineAutocomplete(textEditingValue.text);
                  },
                  displayStringForOption: (option) => option.name,
                  onSelected: (selection) {
                    // Autocomplete returns external whiskies (not in library yet).
                    // Show preview modal with "Add to Library" button.
                    _showWhiskyPreview(context, selection);
                  },
                  fieldViewBuilder: (context, controller, focusNode, onEditingComplete) {
                    _searchFieldController = controller;
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
                        style: const TextStyle(color: AppThemeColors.parchment),
                        decoration: InputDecoration(
                          hintText: tr('search_whisky'),
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
                                color: AppThemeColors.parchment.withValues(alpha: 0.05),
                                height: 1,
                              ),
                              itemBuilder: (BuildContext context, int index) {
                                final option = options.elementAt(index);
                                return Material(
                                  color: Colors.transparent,
                                  child: ListTile(
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
                                  ),
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

              // Filter Chips UI
              SizedBox(
                height: 40,
                child: Consumer(
                  builder: (context, ref, child) {
                    final selectedFilters = ref.watch(selectedFiltersProvider);
                    const supportedFilters = [
                      'Single Malt',
                      'Blended',
                      'Bourbon',
                      'Rye',
                      'Speyside',
                      'Islay',
                      'Highland',
                      'Campbeltown',
                      'Peated',
                      'Smoky',
                      'Sherry',
                      'Sweet',
                      'Fruity',
                    ];

                    return ListView.builder(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      itemCount: supportedFilters.length,
                      itemBuilder: (context, index) {
                        final filter = supportedFilters[index];
                        final isSelected = selectedFilters.contains(filter);
                        return TastingChip(
                          label: filter,
                          isSelected: isSelected,
                          onTap: () {
                            final current = ref.read(selectedFiltersProvider);
                            if (current.contains(filter)) {
                              ref.read(selectedFiltersProvider.notifier).state =
                                  current.where((x) => x != filter).toList();
                            } else {
                              ref.read(selectedFiltersProvider.notifier).state =
                                  [...current, filter];
                            }
                          },
                        );
                      },
                    );
                  },
                ),
              ),
              const SizedBox(height: 8),

              Expanded(
                child: whiskiesAsync.when(
                  data: (whiskies) {
                    if (whiskies.isEmpty) {
                      final query = ref.watch(searchQueryProvider);
                      return _buildEmptyState(context, isFavoritesOnly, query);
                    }
                    return NotificationListener<ScrollNotification>(
                      onNotification: (notification) {
                        // Near-bottom trigger (H1 Task 2): once the user
                        // scrolls within ~400px of the end, ask the paginated
                        // catalog for the next page. The notifier's own
                        // guards (loadingMore / exhausted /
                        // temporarilyUnavailable) make repeat notifications
                        // cheap no-ops; hasValue keeps the very first scroll
                        // (before page 0 finishes loading) from racing build.
                        if (notification is ScrollUpdateNotification &&
                            shouldLoadMoreCatalog(notification.metrics)) {
                          final catalog = ref.read(catalogPaginationProvider);
                          if (catalog.hasValue) {
                            ref
                                .read(catalogPaginationProvider.notifier)
                                .loadMore();
                          }
                        }
                        return false;
                      },
                      child: ListView.builder(
                        controller: _scrollController,
                        physics: const BouncingScrollPhysics(),
                        padding: EdgeInsets.fromLTRB(
                          24,
                          4,
                          24,
                          MediaQuery.viewInsetsOf(context).bottom +
                          MediaQuery.paddingOf(context).bottom +
                          (MediaQuery.viewInsetsOf(context).bottom > 0 ? 96.0 : 96.0)
                        ),
                        itemCount: whiskies.length,
                        itemBuilder: (context, index) {
                          final whisky = whiskies[index];
                          return _buildWhiskyCard(context, ref, whisky, referenceScore);
                        },
                      ),
                    );
                  },
                  loading: () => const Center(
                    child: BrandSpinner(),
                  ),
                  error: (error, stackTrace) => Center(
                      child: Text(
                        tr('db_error', [error]),
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
    final tr = ref.read(trProvider);
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
                  ? tr('no_favorites')
                  : tr('no_whisky_found'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: AppTheme.textPrimary,
                  ),
            ),
            if (query.length > 2 && !isFavoritesOnly)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                child: Text(
                  tr('search_web_prompt_multiline'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppTheme.textMuted, fontSize: 13),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildWhiskyCard(BuildContext context, WidgetRef ref, Whisky whisky, int referenceScore) {
    final tr = ref.read(trProvider);
    int? relativeScore;
    if (whisky.personalScore > 0 && referenceScore > 0) {
      relativeScore = ((whisky.personalScore / referenceScore) * 100).round();
    }

    return CaskCard(
      title: whisky.name,
      subtitle: '${whisky.category ?? "Single Malt"} • ${whisky.country ?? "Scotland"}',
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => DetailScreen(
              whiskyId: whisky.id,
              // Web/mobile are force-backend: pass the backend id so the
              // detail screen fetches radar/evidence from /api/db instead of
              // the (anti-scrape-empty) local DB.
              backendId: whisky.externalId,
            ),
          ),
        );
      },
      iconOrImage: Container(
        width: 60,
        height: 60,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppTheme.accent, AppTheme.primary],
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Medallion(
          size: 32,
          level: MedallionLevel.micro,
        ),
      ),
      tags: whisky.tastingNotes.take(3).map((note) => TastingChip(label: note)).toList(),
      trailing: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
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
            Text(
              tr('not_scored'),
              style: const TextStyle(
                color: AppTheme.textMuted,
                fontStyle: FontStyle.italic,
                fontSize: 12,
              ),
            ),
          const SizedBox(height: 12),
          Icon(
            whisky.isFavorite ? Icons.star : Icons.star_border,
            color: whisky.isFavorite ? AppTheme.accent : AppTheme.textMuted.withValues(alpha: 0.3),
            size: 24,
          ),
        ],
      ),
    );
  }
}
