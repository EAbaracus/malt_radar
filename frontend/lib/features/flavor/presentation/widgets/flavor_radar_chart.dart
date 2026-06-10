import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';

class FlavorRadarChart extends StatelessWidget {
  final String flavorProfileJson;

  const FlavorRadarChart({super.key, required this.flavorProfileJson});

  @override
  Widget build(BuildContext context) {
    Map<String, dynamic> profile = {};
    try {
      profile = json.decode(flavorProfileJson) as Map<String, dynamic>;
    } catch (e) {
      return const SizedBox();
    }

    // 7 Main Flavor Categories
    final categories = [
      'fruity',
      'sweet',
      'spicy',
      'smoky_peaty',
      'oak_cask',
      'malty_cereal',
      'floral_herbal'
    ];

    final displayNames = [
      'Fruity',
      'Sweet',
      'Spicy',
      'Smoky',
      'Oak/Cask',
      'Malty',
      'Floral'
    ];

    List<RadarDataSet> dataSets = [
      RadarDataSet(
        fillColor: AppTheme.accent.withOpacity(0.3),
        borderColor: AppTheme.accent,
        entryRadius: 3,
        dataEntries: categories.map((c) {
          final val = (profile[c] as num?)?.toDouble() ?? 0.0;
          return RadarEntry(value: val);
        }).toList(),
      )
    ];

    double maxVal = 0;
    for (var cat in categories) {
      final val = (profile[cat] as num?)?.toDouble() ?? 0.0;
      if (val > maxVal) maxVal = val;
    }
    
    // Scale appropriately (minimum 10 so the chart doesn't look squashed if all values are tiny)
    maxVal = maxVal > 10 ? maxVal : 10;

    return AspectRatio(
      aspectRatio: 1.3,
      child: RadarChart(
        RadarChartData(
          radarShape: RadarShape.polygon,
          radarBackgroundColor: Colors.transparent,
          radarBorderData: const BorderSide(color: Colors.white24, width: 1.5),
          titlePositionMultiplierPercentage: 0.15,
          tickCount: 3,
          ticksTextStyle: const TextStyle(color: Colors.transparent, fontSize: 10),
          tickBorderData: const BorderSide(color: Colors.white12),
          gridBorderData: const BorderSide(color: Colors.white12, width: 1.5),
          getTitle: (index, angle) {
            return RadarChartTitle(
              text: displayNames[index],
              angle: 0,
              positionPercentageOffset: 0.1,
            );
          },
          titleTextStyle: const TextStyle(
            color: AppTheme.textSecondary,
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
          dataSets: dataSets,
          radarTouchData: RadarTouchData(enabled: false),
        ),
        swapAnimationDuration: const Duration(milliseconds: 150),
      ),
    );
  }
}
