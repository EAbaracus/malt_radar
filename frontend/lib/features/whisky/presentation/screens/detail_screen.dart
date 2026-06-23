import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import '../controllers/whisky_providers.dart';
import '../../../../core/localization/localization_provider.dart';
import '../widgets/glass_container.dart';
import '../../../flavor/presentation/widgets/flavor_radar_chart.dart';
import '../../../flavor/presentation/widgets/similar_flavor_whiskies.dart';

import 'package:malt_radar/features/lists/presentation/widgets/add_to_list_sheet.dart';
import 'package:malt_radar/features/lists/presentation/controllers/user_lists_providers.dart';
import 'package:malt_radar/core/localization/flavor_tag_translator.dart';
import '../../../../core/presentation/widgets/section_header.dart';
import '../../../../core/presentation/widgets/tasting_chip.dart';

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
      final list = await repository.getWhiskyPrices(
        widget.whiskyId,
        whisky.externalId,
      );
      setState(() {
        _prices = list;
        _isLoadingPrices = false;
      });
    }
  }

  void _saveNotesAndScore() async {
    final repository = ref.read(whiskyRepositoryProvider);
    final tr = ref.read(trProvider);
    await repository.updatePersonalNotes(
      widget.whiskyId,
      _notesController.text,
    );
    await repository.updatePersonalScore(widget.whiskyId, _score);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(tr('evaluation_saved')),
          backgroundColor: AppTheme.primary,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      );
    }
  }

  void _showAddPriceDialog() {
    final tr = ref.read(trProvider);
    final formKey = GlobalKey<FormState>();
    final priceController = TextEditingController();
    final sourceController = TextEditingController();
    final sourceUrlController = TextEditingController(text: 'manuel');
    String selectedCurrency = 'TL';
    String selectedCountry = 'Türkiye';

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: AppTheme.surfaceElevated,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          title: Text(
            tr('add_price_record'),
            style: const TextStyle(color: AppTheme.primary),
          ),
          content: SingleChildScrollView(
            child: Form(
              key: formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: priceController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: InputDecoration(labelText: tr('price')),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return tr('price_required');
                      }
                      final pVal = double.tryParse(value);
                      if (pVal == null || pVal <= 0) {
                        return tr('invalid_price');
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: selectedCurrency,
                    decoration: InputDecoration(labelText: tr('currency')),
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
                    decoration: InputDecoration(
                      labelText: tr('price_record_country'),
                    ), // using country for this dropdown
                    dropdownColor: AppTheme.surfaceElevated,
                    items: ['Türkiye', 'İskoçya', 'İngiltere', 'ABD', 'Japonya']
                        .map((c) {
                          return DropdownMenuItem(value: c, child: Text(c));
                        })
                        .toList(),
                    onChanged: (val) {
                      if (val != null) selectedCountry = val;
                    },
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: sourceController,
                    decoration: InputDecoration(
                      labelText: tr('store'),
                      hintText: tr('store_optional'),
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(
                tr('cancel'),
                style: const TextStyle(color: AppTheme.textSecondary),
              ),
            ),
            ElevatedButton(
              onPressed: () async {
                if (!formKey.currentState!.validate()) return;
                final double pVal = double.parse(priceController.text);

                final storeName = sourceController.text.trim().isNotEmpty
                    ? sourceController.text.trim()
                    : 'Kişisel Takip';

                final repository = ref.read(whiskyRepositoryProvider);
                await repository.addManualPrice(
                  whiskyId: widget.whiskyId,
                  price: pVal,
                  currency: selectedCurrency,
                  country: selectedCountry,
                  sourceName: storeName,
                  sourceUrl: sourceUrlController.text,
                );

                if (context.mounted) {
                  Navigator.pop(context);
                }
                _loadPrices();
              },
              child: Text(tr('save')),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    final langCode = ref.watch(localizationProvider);
    final whiskyAsync = ref.watch(whiskyDetailProvider(widget.whiskyId));
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);
    final refWhiskyAsync = ref.watch(referenceWhiskyModelProvider);

    final settings = settingsAsync.value ?? {};
    final referenceScore =
        settings['reference_whisky_absolute_score'] as int? ?? 100;
    final referenceId = settings['reference_whisky_id'] as int?;
    final refWhisky = refWhiskyAsync.value;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.8),
            radius: 1.5,
            colors: [Color(0xFF1E1E2C), AppTheme.background, Color(0xFF040406)],
          ),
        ),
        child: whiskyAsync.when(
          data: (whisky) {
            if (whisky == null) {
              return Center(child: Text(tr('whisky_not_found')));
            }

            if (!_initialized) {
              _notesController.text = whisky.personalNotes;
              _score = whisky.personalScore;
              _initialized = true;

              if (whisky.tastingNotes.isEmpty && whisky.externalId != null) {
                Future.microtask(
                  () => ref
                      .read(whiskyRepositoryProvider)
                      .fetchAndUpdateDetails(whisky.id, whisky.externalId!),
                );
              }
            }

            final isReferenceWhisky = whisky.id == referenceId;

            double? automatedRelativeScore;
            if (refWhisky != null &&
                refWhisky.globalScore != null &&
                refWhisky.globalScore! > 0 &&
                whisky.globalScore != null) {
              automatedRelativeScore =
                  (whisky.globalScore! / refWhisky.globalScore!) *
                  referenceScore;
            }

            return CustomScrollView(
              physics: const BouncingScrollPhysics(),
              slivers: [
                // Premium SliverAppBar
                SliverAppBar(
                  expandedHeight: 280.0,
                  floating: false,
                  pinned: true,
                  backgroundColor: Colors.transparent,
                  flexibleSpace: FlexibleSpaceBar(
                    titlePadding: const EdgeInsets.only(
                      left: 24,
                      bottom: 16,
                      right: 24,
                    ),
                    title: Hero(
                      tag: 'whisky-name-${whisky.id}',
                      child: Material(
                        color: Colors.transparent,
                        child: Text(
                          whisky.name,
                          style: Theme.of(context).textTheme.headlineMedium
                              ?.copyWith(
                                color: Colors.white,
                                fontSize: 24,
                                shadows: [
                                  Shadow(
                                    offset: const Offset(0, 2),
                                    blurRadius: 4.0,
                                    color: Colors.black.withValues(alpha: 0.8),
                                  ),
                                ],
                              ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    background: Stack(
                      fit: StackFit.expand,
                      children: [
                        // Abstract glow instead of missing image
                        Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                AppTheme.primary.withValues(alpha: 0.2),
                                Colors.transparent,
                              ],
                            ),
                          ),
                        ),
                        Center(
                          child: Icon(
                            Icons.local_bar,
                            size: 120,
                            color: AppTheme.primary.withValues(alpha: 0.15),
                          ),
                        ),
                        // Bottom gradient for text readability
                        const DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [Colors.transparent, AppTheme.background],
                              stops: [0.5, 1.0],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  actions: [
                    IconButton(
                      icon: const Icon(
                        Icons.playlist_add,
                        color: Colors.white,
                        size: 28,
                      ),
                      onPressed: () {
                        AddToListSheet.show(context, whisky.id);
                      },
                    ),
                    IconButton(
                      icon: Icon(
                        whisky.isFavorite ? Icons.star : Icons.star_border,
                        color: whisky.isFavorite
                            ? AppTheme.accent
                            : Colors.white,
                        size: 28,
                        shadows: [
                          Shadow(
                            offset: const Offset(0, 2),
                            blurRadius: 4.0,
                            color: Colors.black.withValues(alpha: 0.5),
                          ),
                        ],
                      ),
                      onPressed: () async {
                        final repo = ref.read(whiskyRepositoryProvider);
                        final listRepo = ref.read(userListsRepositoryProvider);

                        await repo.toggleFavorite(whisky.id);

                        // Sync with new Favorites list
                        try {
                          final lists = await listRepo.getLists();
                          final favList = lists.firstWhere(
                            (l) => l.defaultType == 'favorites',
                          );
                          final isInFavList = await listRepo.isWhiskyInList(
                            favList.id,
                            whisky.id,
                          );
                          final isNowFavorite =
                              !whisky.isFavorite; // since we toggled it

                          if (isNowFavorite && !isInFavList) {
                            await listRepo.addWhiskyToList(
                              favList.id,
                              whisky.id,
                            );
                          } else if (!isNowFavorite && isInFavList) {
                            await listRepo.removeWhiskyFromList(
                              favList.id,
                              whisky.id,
                            );
                          }
                          ref.invalidate(getListsForWhiskyProvider(whisky.id));
                        } catch (_) {}

                        ref.invalidate(whiskyDetailProvider(whisky.id));
                      },
                    ),
                  ],
                ),

                // Body content
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Meta tags
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            if (whisky.country != null)
                              _buildMetaTag(tr('origin'), whisky.country!),
                            if (whisky.region != null)
                              _buildMetaTag(tr('region'), whisky.region!),
                            if (whisky.category != null)
                              _buildMetaTag(
                                tr('category'),
                                whisky.category!.replaceAll(
                                  'SingleMalt-like',
                                  'Single malt-like',
                                ),
                              ),
                            if (whisky.age != null)
                              _buildMetaTag(
                                tr('age'),
                                '${whisky.age} ${tr('age_years')}',
                              ),
                            if (whisky.abv != null)
                              _buildMetaTag(
                                tr('preview_abv'),
                                '%${whisky.abv}',
                              ),
                            if (whisky.caskType != null)
                              _buildMetaTag(
                                tr('preview_cask'),
                                whisky.caskType!,
                              ),
                          ],
                        ),
                        const SizedBox(height: 36),

                        // Tasting Notes
                        if (whisky.tastingNotes.isNotEmpty) ...[
                          SectionHeader(
                            title: tr('tasting_notes'),
                            icon: Icons.bubble_chart,
                          ),
                          const SizedBox(height: 16),
                          GlassContainer(
                            padding: const EdgeInsets.all(16),
                            child: Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: whisky.tastingNotes.map((note) {
                                return TastingChip(
                                  label: localizeTastingNote(note, langCode),
                                );
                              }).toList(),
                            ),
                          ),
                          const SizedBox(height: 36),
                        ],

                        // Malt Radar (Flavor Profile)
                        const SectionHeader(title: 'Malt Radar', icon: Icons.radar),
                        const SizedBox(height: 16),
                        if (whisky.flavorProfile != null) ...[
                          GlassContainer(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              children: [
                                FlavorRadarChart(
                                  flavorProfileJson: whisky.flavorProfile!,
                                ),
                                if (whisky.flavorTags != null) ...[
                                  const SizedBox(height: 16),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children:
                                        (jsonDecode(whisky.flavorTags!)
                                                as List<dynamic>)
                                            .take(5)
                                            .map((tag) {
                                              return Container(
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                      horizontal: 10,
                                                      vertical: 6,
                                                    ),
                                                decoration: BoxDecoration(
                                                  color: AppTheme.accent
                                                      .withValues(alpha: 0.1),
                                                  borderRadius:
                                                      BorderRadius.circular(12),
                                                  border: Border.all(
                                                    color: AppTheme.accent
                                                        .withValues(alpha: 0.3),
                                                  ),
                                                ),
                                                child: Text(
                                                  localizeTastingNote(
                                                    tag.toString(),
                                                    langCode,
                                                  ),
                                                  style: const TextStyle(
                                                    color: AppTheme.accent,
                                                    fontSize: 12,
                                                  ),
                                                ),
                                              );
                                            })
                                            .toList(),
                                  ),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(height: 24),
                          SimilarFlavorWhiskies(
                            whiskyId: whisky.id,
                            onWhiskyTap: (w) {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => DetailScreen(whiskyId: w.id),
                                ),
                              );
                            },
                          ),
                        ] else ...[
                          GlassContainer(
                            padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
                            child: Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.radar, size: 48, color: AppTheme.textMuted.withValues(alpha: 0.3)),
                                  const SizedBox(height: 16),
                                  Text(
                                    tr('no_flavor_profile'),
                                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                        const SizedBox(height: 36),

                        // Prices
                        SectionHeader(
                          title: tr('price_info'),
                          icon: Icons.sell,
                        ),
                        const SizedBox(height: 16),
                        _isLoadingPrices
                            ? const Center(
                                child: CircularProgressIndicator(
                                  color: AppTheme.primary,
                                ),
                              )
                            : GlassContainer(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (_prices.isEmpty)
                                      Text(
                                        tr('no_price_record'),
                                        style: const TextStyle(
                                          color: AppTheme.textMuted,
                                        ),
                                      )
                                    else
                                      ..._prices.map((priceItem) {
                                        final isManual =
                                            priceItem['is_manual'] as bool? ??
                                            false;
                                        return Container(
                                          margin: const EdgeInsets.only(
                                            bottom: 8,
                                          ),
                                          padding: const EdgeInsets.all(12),
                                          decoration: BoxDecoration(
                                            color: Colors.white.withValues(
                                              alpha: 0.05,
                                            ),
                                            borderRadius: BorderRadius.circular(
                                              12,
                                            ),
                                          ),
                                          child: Row(
                                            children: [
                                              Icon(
                                                isManual
                                                    ? Icons.edit
                                                    : Icons.sync,
                                                color: isManual
                                                    ? AppTheme.accent
                                                    : AppTheme.primary,
                                                size: 20,
                                              ),
                                              const SizedBox(width: 12),
                                              Expanded(
                                                child: Column(
                                                  crossAxisAlignment:
                                                      CrossAxisAlignment.start,
                                                  children: [
                                                    Text(
                                                      '${priceItem['price']} ${priceItem['currency']}',
                                                      style: const TextStyle(
                                                        fontWeight:
                                                            FontWeight.bold,
                                                        color: AppTheme
                                                            .textPrimary,
                                                        fontSize: 16,
                                                      ),
                                                    ),
                                                    const SizedBox(height: 2),
                                                    Text(
                                                      '${tr('price_source')}: ${priceItem['source_name']} (${priceItem['country']})',
                                                      style: const TextStyle(
                                                        fontSize: 12,
                                                        color: AppTheme
                                                            .textSecondary,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                              Text(
                                                priceItem['fetched_at']
                                                    .toString()
                                                    .split('T')[0],
                                                style: const TextStyle(
                                                  color: AppTheme.textMuted,
                                                  fontSize: 11,
                                                ),
                                              ),
                                            ],
                                          ),
                                        );
                                      }),
                                    const SizedBox(height: 12),
                                    SizedBox(
                                      width: double.infinity,
                                      child: OutlinedButton.icon(
                                        onPressed: _showAddPriceDialog,
                                        icon: const Icon(Icons.add),
                                        label: Text(tr('add_price_record')),
                                        style: OutlinedButton.styleFrom(
                                          foregroundColor: AppTheme.primary,
                                          side: const BorderSide(
                                            color: AppTheme.primary,
                                          ),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(
                                              12,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                        const SizedBox(height: 36),

                        // Evaluation
                        SectionHeader(
                          title: tr('personal_evaluation'),
                          icon: Icons.star,
                        ),
                        const SizedBox(height: 16),
                        GlassContainer(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (isReferenceWhisky) ...[
                                Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(12),
                                  margin: const EdgeInsets.only(bottom: 24),
                                  decoration: BoxDecoration(
                                    color: AppTheme.primary.withValues(
                                      alpha: 0.1,
                                    ),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: AppTheme.primary.withValues(
                                        alpha: 0.3,
                                      ),
                                    ),
                                  ),
                                  child: Text(
                                    tr('is_reference_whisky'),
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                      color: AppTheme.primary,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                              if (whisky.globalScore != null) ...[
                                Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      tr('global_average_score'),
                                      style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        fontSize: 14,
                                      ),
                                    ),
                                    Text(
                                      '${whisky.globalScore!.toStringAsFixed(0)} / 100',
                                      style: const TextStyle(
                                        fontSize: 22,
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                Divider(
                                  color: Colors.white.withValues(alpha: 0.1),
                                ),
                                const SizedBox(height: 16),
                              ],
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    tr('personal_score'),
                                    style: const TextStyle(
                                      color: AppTheme.textSecondary,
                                      fontSize: 14,
                                    ),
                                  ),
                                  Text(
                                    _score > 0 ? '$_score' : '-',
                                    style: const TextStyle(
                                      fontSize: 32,
                                      color: AppTheme.primary,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              SliderTheme(
                                data: SliderTheme.of(context).copyWith(
                                  trackHeight: 8,
                                  thumbShape: const RoundSliderThumbShape(
                                    enabledThumbRadius: 12,
                                  ),
                                ),
                                child: Slider(
                                  value: _score.toDouble(),
                                  min: 0,
                                  max: 100,
                                  divisions: 100,
                                  onChanged: (val) {
                                    setState(() {
                                      _score = val.round();
                                    });
                                  },
                                ),
                              ),
                              const SizedBox(height: 24),
                              if (automatedRelativeScore != null) ...[
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(
                                        Icons.auto_awesome,
                                        color: AppTheme.accent,
                                        size: 20,
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              tr('auto_relative_score'),
                                              style: const TextStyle(
                                                color: AppTheme.textSecondary,
                                                fontSize: 12,
                                              ),
                                            ),
                                            Text(
                                              '${automatedRelativeScore.toStringAsFixed(1)} / 100',
                                              style: const TextStyle(
                                                color: AppTheme.textPrimary,
                                                fontWeight: FontWeight.bold,
                                                fontSize: 16,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 24),
                              ],
                              Text(
                                tr('personal_notes'),
                                style: const TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 8),
                              TextField(
                                controller: _notesController,
                                maxLines: 4,
                                style: const TextStyle(color: Colors.white),
                                decoration: InputDecoration(
                                  hintText: tr('notes_hint'),
                                ),
                              ),
                              const SizedBox(height: 24),
                              SizedBox(
                                width: double.infinity,
                                child: ElevatedButton.icon(
                                  onPressed: _saveNotesAndScore,
                                  icon: const Icon(Icons.save),
                                  label: Text(tr('save')),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 32),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
          loading: () => const Center(
            child: CircularProgressIndicator(color: AppTheme.primary),
          ),
          error: (error, stackTrace) => Center(
            child: Text(
              '${tr('error')}: $error',
              style: const TextStyle(color: AppTheme.error),
            ),
          ),
        ),
      ),
    );
  }



  Widget _buildMetaTag(String label, String value) {
    return GlassContainer(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      borderRadius: BorderRadius.circular(12),
      opacity: 0.05,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
