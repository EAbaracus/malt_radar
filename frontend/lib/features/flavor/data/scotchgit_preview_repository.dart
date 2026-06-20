import 'dart:convert';
import 'package:csv/csv.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:malt_radar/core/config/app_config.dart';
import 'scotchgit_preview_profile.dart';

class ScotchGitPreviewRepository {
  static const String _assetPath = 'assets/data/scotchgit_flavor_preview_import.csv';

  List<ScotchGitPreviewProfile>? _cachedProfiles;

  /// Loads and parses the preview CSV if the feature flag is enabled.
  /// Returns an empty list if the flag is disabled or if parsing fails.
  Future<List<ScotchGitPreviewProfile>> getPreviewProfiles() async {
    if (!AppConfig.enableFlavorPreviewMode) {
      return [];
    }

    if (_cachedProfiles != null) {
      return _cachedProfiles!;
    }

    try {
      final String csvString = await rootBundle.loadString(_assetPath);
      final List<List<dynamic>> rows = const CsvToListConverter().convert(
        csvString,
        eol: '\n',
        shouldParseNumbers: false, // Keep everything as strings initially
      );

      if (rows.isEmpty || rows.length == 1) {
        return [];
      }

      final header = rows.first.map((e) => e.toString().trim()).toList();
      final idIdx = header.indexOf('matched_master_whisky_id');
      final nameIdx = header.indexOf('product_name');
      final conflictIdx = header.indexOf('conflict_status');
      final priorityIdx = header.indexOf('scotchgit_priority');

      // Flavor mapping (Map ScotchGit axes to Malt Radar 7 axes)
      final smokyIdx = header.indexOf('smoky');
      final sweetIdx = header.indexOf('sweet');
      final fruityIdx = header.indexOf('fruity');
      final spicyIdx = header.indexOf('spicy');
      final woodyIdx = header.indexOf('woody');
      // Note: malt_radar has 'malty_cereal' and 'floral_herbal', which ScotchGit might not map 1:1.
      // We will inject the ones we have.
      // ScotchGit axes: smoky, sweet, fruity, spicy, woody, maritime, sherry
      final sherryIdx = header.indexOf('sherry');

      if (idIdx == -1 || priorityIdx == -1) {
        return [];
      }

      final List<ScotchGitPreviewProfile> profiles = [];

      for (var i = 1; i < rows.length; i++) {
        final row = rows[i];
        if (row.length <= idIdx) continue;

        final whiskyId = row[idIdx].toString().trim();
        final productName = nameIdx != -1 ? row[nameIdx].toString().trim() : '';
        final conflictStatus = conflictIdx != -1 ? row[conflictIdx].toString().trim() : 'no_conflict';
        final priority = row[priorityIdx].toString().trim();

        // Build the flavor profile JSON
        final Map<String, double> flavorMap = {};
        
        void addVal(String targetAxis, int srcIdx) {
          if (srcIdx != -1 && srcIdx < row.length) {
            final valStr = row[srcIdx].toString().trim();
            final val = double.tryParse(valStr);
            if (val != null && val > 0) {
               // Scale up since ScotchGit ranges might be 0.0-1.0
               // App normalizer scales 0-1 values automatically, but we can store raw.
               flavorMap[targetAxis] = val;
            }
          }
        }

        addVal('smoky_peaty', smokyIdx);
        addVal('sweet', sweetIdx);
        addVal('fruity', fruityIdx);
        addVal('spicy', spicyIdx);
        addVal('oak_cask', woodyIdx); // woody -> oak_cask
        
        // Add additional axes as mock values based on others or zero out
        if (sherryIdx != -1 && sherryIdx < row.length) {
          final s = double.tryParse(row[sherryIdx].toString().trim()) ?? 0;
          if (s > 0) {
            flavorMap['fruity'] = (flavorMap['fruity'] ?? 0) + (s * 0.5); // Boost fruity slightly for sherry
          }
        }

        final profileJson = jsonEncode(flavorMap);

        profiles.add(ScotchGitPreviewProfile(
          whiskyId: whiskyId,
          productName: productName,
          conflictStatus: conflictStatus,
          priority: priority,
          flavorProfileJson: profileJson,
        ));
      }

      _cachedProfiles = profiles;
      return _cachedProfiles!;
    } catch (e) {
      debugPrint('Failed to load ScotchGit preview profiles: $e');
      return []; // No crash on error
    }
  }

  /// Returns the preview profile for a specific whisky if available.
  Future<ScotchGitPreviewProfile?> getPreviewForWhisky(String whiskyId) async {
    final profiles = await getPreviewProfiles();
    try {
      return profiles.firstWhere((p) => p.whiskyId == whiskyId);
    } catch (_) {
      return null;
    }
  }
}
