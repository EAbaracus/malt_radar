import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import '../../whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/core/database/database.dart';

/// A pre-gate-safe whisky DTO: contains ONLY identifying/brand fields that are
/// not age-gated (no tasting notes, no abv, no scores, no prices, no flavor
/// profiles). Safe to display before the user confirms legal drinking age.
class PreGateWhisky {
  final int id;
  final String name;
  final String? country;
  final String? region;
  final String? type;
  final String? distillery;
  final int? age;

  PreGateWhisky({
    required this.id,
    required this.name,
    this.country,
    this.region,
    this.type,
    this.distillery,
    this.age,
  });

  factory PreGateWhisky.fromEntity(WhiskyEntity e) => PreGateWhisky(
        id: e.id,
        name: e.name,
        country: e.country,
        region: e.region,
        // Drift `category` maps to the type/category display label.
        // NOT copied: abv, defaultPrice, currency, tastingNotes,
        //   companionSuggestions, globalScore, flavorProfile, flavorVector,
        //   flavorTags, flavorSource, flavorMatchScore, sourceName, sourceUrl
        type: e.category,
        distillery: e.distillery,
        age: e.age,
      );

  /// Returns a subtitle line safe for pre-gate display.
  String? get subtitle {
    final parts = <String>[];
    if (type != null) parts.add(type!);
    if (country != null) parts.add(country!);
    if (region != null) parts.add(region!);
    return parts.isNotEmpty ? parts.join(' • ') : null;
  }
}

/// Streams a page of age-gate-safe whisky identity data (no tasting notes,
/// no scores, no abv, no prices) for the pre-gate public discovery shell.
final preGateWhiskiesProvider = StreamProvider<List<PreGateWhisky>>((ref) {
  final db = ref.watch(appDatabaseProvider);
  // Read name/country/region/category/distillery/age only — Drift's typed
  // columns enforce this at compile time. No age-gated columns (tastingNotes,
  // abv, defaultPrice, globalScore, flavor*) are selected.
  return (db.select(db.whiskies)..limit(24))
      .watch()
      .map((entities) =>
          entities.map(PreGateWhisky.fromEntity).toList(growable: false));
});

/// A lightweight public discovery shell rendered beneath the age gate.
///
/// Per the Malt Radar architecture decision (audit 359e028c, 2026-08-16):
/// pre-gate users must see real, browsable whisky identity content before
/// passing the age gate. This shell shows only age-gate-safe fields.
class PreGateDiscoveryShell extends ConsumerWidget {
  const PreGateDiscoveryShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = ref.watch(trProvider);
    final whiskiesAsync = ref.watch(preGateWhiskiesProvider);

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
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'MALT RADAR',
                          style: TextStyle(
                            color: AppTheme.primary,
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 3.0,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          tr('whisky_library'),
                          style: const TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
                child: Text(
                  tr('age_gate_preview_prompt'),
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
              ),
              Expanded(
                child: whiskiesAsync.when(
                  data: (whiskies) {
                    if (whiskies.isEmpty) {
                      return const Center(
                        child: Text(
                          'Whisky library loading...',
                          style: TextStyle(color: AppTheme.textSecondary),
                        ),
                      );
                    }
                    return ListView.separated(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      itemCount: whiskies.length,
                      separatorBuilder: (context, index) =>
                          const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final w = whiskies[index];
                        return _PreGateCard(whisky: w);
                      },
                    );
                  },
                  loading: () => const Center(
                    child: SizedBox(
                      width: 40,
                      height: 40,
                      child: CircularProgressIndicator(
                        color: AppTheme.primary,
                        strokeWidth: 2,
                      ),
                    ),
                  ),
                  error: (e, st) => Center(
                    child: Text(
                      'Unable to load preview: $e',
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
}

class _PreGateCard extends StatelessWidget {
  final PreGateWhisky whisky;

  const _PreGateCard({required this.whisky});

  @override
  Widget build(BuildContext context) {
    return Opacity(
      // Visual softening to signal "preview only" — full detail requires gate.
      opacity: 0.6,
      child: Container(
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: AppThemeColors.parchment.withValues(alpha: 0.08),
            width: 1,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppTheme.accent, AppTheme.primary],
                  ),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Center(
                  child: Medallion(
                    size: 28,
                    level: MedallionLevel.micro,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      whisky.name,
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (whisky.subtitle != null) ...[
                      const SizedBox(height: 3),
                      Text(
                        whisky.subtitle!,
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontSize: 12,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (whisky.age != null) ...[
                      const SizedBox(height: 3),
                      Text(
                        '${whisky.age} years old',
                        style: const TextStyle(
                          color: AppTheme.textMuted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const Icon(
                Icons.lock_outline,
                color: AppTheme.textMuted,
                size: 16,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
