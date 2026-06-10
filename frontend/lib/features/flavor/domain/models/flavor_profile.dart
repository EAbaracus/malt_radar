import 'dart:convert';

class FlavorProfile {
  final int whiskyId;
  final String bottleName;
  final int matchScore;
  final Map<String, dynamic> flavorVector;
  final Map<String, dynamic> profile;
  final List<String> tags;

  FlavorProfile({
    required this.whiskyId,
    required this.bottleName,
    required this.matchScore,
    required this.flavorVector,
    required this.profile,
    required this.tags,
  });

  factory FlavorProfile.fromCsvRow(List<dynamic> row, List<String> header) {
    int getInt(String key) {
      final idx = header.indexOf(key);
      if (idx == -1) return 0;
      final val = row[idx];
      if (val is int) return val;
      if (val is double) return val.toInt();
      if (val is String) return int.tryParse(val) ?? 0;
      return 0;
    }

    String getString(String key) {
      final idx = header.indexOf(key);
      if (idx == -1) return '';
      return row[idx]?.toString() ?? '';
    }

    Map<String, dynamic> getJsonMap(String key) {
      final str = getString(key);
      if (str.isEmpty) return {};
      try {
        return json.decode(str) as Map<String, dynamic>;
      } catch (e) {
        return {};
      }
    }

    List<String> getJsonList(String key) {
      final str = getString(key);
      if (str.isEmpty) return [];
      try {
        final decoded = json.decode(str);
        if (decoded is List) {
          return decoded.map((e) => e.toString()).toList();
        }
        return [];
      } catch (e) {
        return [];
      }
    }

    return FlavorProfile(
      whiskyId: getInt('whisky_id'),
      bottleName: getString('production_bottle_name'),
      matchScore: getInt('match_score'),
      flavorVector: getJsonMap('flavor_vector'),
      profile: getJsonMap('flavor_profile'),
      tags: getJsonList('flavor_tags'),
    );
  }
}
