import 'package:flutter/foundation.dart';
import 'package:drift/drift.dart';
import 'package:csv/csv.dart';
import 'package:malt_radar/core/database/database.dart';

class DataSeedService {
  // NOTE (anti-scrape): the catalog CSV data is NOT bundled in the client. This
  // seeder is therefore driven exclusively by explicitly-provided CSV strings
  // (the backend is the single source of truth at runtime). The canonical CSV
  // files live under backend/data and are read by tests directly.
  static Future<void> seedDatabaseIfEmpty(
    AppDatabase db, {
    String? testCsvString,
    String? flavorCsvString,
  }) async {
    // No client-bundled catalog exists; without an explicit source there is
    // nothing to seed. This keeps the mobile/offline path honest: catalog data
    // comes from the backend, not from a shipped asset.
    if (testCsvString == null) {
      return;
    }
    try {
      final countExp = db.whiskies.id.count();
      final query = db.selectOnly(db.whiskies)..addColumns([countExp]);
      final result = await query.getSingle();
      final count = result.read(countExp) ?? 0;

      if (count > 0) {
        return; // Already seeded
      }

      // Load flavor profiles (optional companion data; keyed by whisky id).
      final Map<int, List<dynamic>> flavorMap = {};
      int fWhiskyIdIdx = -1;
      int fMatchScoreIdx = -1;
      int fFlavorVectorIdx = -1;
      int fFlavorProfileIdx = -1;
      int fFlavorTagsIdx = -1;
      int fFlavorSourceIdx = -1;

      if (flavorCsvString != null) {
        try {
          final flavorTable = const CsvToListConverter(eol: '\n', fieldDelimiter: ',')
              .convert(flavorCsvString);

          if (flavorTable.length > 1) {
            final fHeaders = flavorTable[0].map((e) => e.toString().trim()).toList();
            fWhiskyIdIdx = fHeaders.indexOf('whisky_id');
            fMatchScoreIdx = fHeaders.indexOf('match_score');
            fFlavorVectorIdx = fHeaders.indexOf('flavor_vector');
            fFlavorProfileIdx = fHeaders.indexOf('flavor_profile');
            fFlavorTagsIdx = fHeaders.indexOf('flavor_tags');
            fFlavorSourceIdx = fHeaders.indexOf('flavor_source');

            for (int i = 1; i < flavorTable.length; i++) {
              final fRow = flavorTable[i];
              if (fRow.isEmpty) continue;

              if (fWhiskyIdIdx >= 0 && fWhiskyIdIdx < fRow.length) {
                final idStr = fRow[fWhiskyIdIdx]?.toString().trim() ?? '';
                final match = RegExp(r'\d+').firstMatch(idStr);
                if (match != null) {
                  final idNum = int.tryParse(match.group(0)!);
                  if (idNum != null) {
                    flavorMap[idNum] = fRow;
                  }
                }
              }
            }
          }
        } catch (e) {
          debugPrint('Could not parse flavor_profiles CSV: $e');
        }
      }

      final csvString = testCsvString.replaceAll('\r\n', '\n');
      final List<List<dynamic>> csvTable =
          const CsvToListConverter(eol: '\n', fieldDelimiter: ',').convert(csvString);

      if (csvTable.length <= 1) {
        return; // Empty or only header
      }

      final headers = csvTable[0].map((e) => e.toString().trim()).toList();

      final recordIdIdx = headers.indexOf('record_id');
      final canonicalNameIdx = headers.indexOf('canonical_name');
      final whiskyNameIdx = headers.indexOf('whisky_name');
      final distilleryIdx = headers.indexOf('distillery');
      final countryIdx = headers.indexOf('country');
      final regionIdx = headers.indexOf('region');
      final typeIdx = headers.indexOf('type');
      final classIdx = headers.indexOf('class');
      final styleSimilarityIdx = headers.indexOf('style_similarity');
      final ageIdx = headers.indexOf('age_years');
      final abvIdx = headers.indexOf('abv_percent');
      final caskTypeIdx = headers.indexOf('cask_type');
      final noseNotesIdx = headers.indexOf('nose_notes');
      final palateNotesIdx = headers.indexOf('palate_notes');
      final finishNotesIdx = headers.indexOf('finish_notes');
      final userScoreIdx = headers.indexOf('user_score_100');
      final metaCriticIdx = headers.indexOf('meta_critic');

      final companions = <WhiskiesCompanion>[];

      for (int i = 1; i < csvTable.length; i++) {
        final row = csvTable[i];
        if (row.isEmpty) continue;

        String getStr(int idx) {
          if (idx < 0 || idx >= row.length) return '';
          return row[idx]?.toString().trim() ?? '';
        }

        double? getDouble(int idx) {
          final s = getStr(idx);
          if (s.isEmpty) return null;
          return double.tryParse(s);
        }

        int? getInt(int idx) {
          final s = getStr(idx);
          if (s.isEmpty || s.toUpperCase() == 'NAS') return null;
          return int.tryParse(s);
        }

        final recordId = getStr(recordIdIdx);
        final canonicalName = getStr(canonicalNameIdx);
        final whiskyName = getStr(whiskyNameIdx);
        final name = canonicalName.isNotEmpty ? canonicalName : whiskyName;

        if (name.isEmpty) continue; // Must have a name

        final typeStr = getStr(typeIdx);
        final classStr = getStr(classIdx);
        final category = classStr.isNotEmpty ? classStr : typeStr;

        final nose = getStr(noseNotesIdx);
        final palate = getStr(palateNotesIdx);
        final finish = getStr(finishNotesIdx);

        final notesList = <String>[];
        if (nose.isNotEmpty) notesList.add('Burun: $nose');
        if (palate.isNotEmpty) notesList.add('Damak: $palate');
        if (finish.isNotEmpty) notesList.add('Bitiş: $finish');

        final userScoreStr = getStr(userScoreIdx);
        final metaCriticStr = getStr(metaCriticIdx);

        double? globalScore;
        final userScore = double.tryParse(userScoreStr);
        final metaCritic = double.tryParse(metaCriticStr);

        if (userScore != null && userScore > 0) {
          globalScore = userScore;
        } else if (metaCritic != null && metaCritic > 0) {
          globalScore = metaCritic <= 10.0 ? metaCritic * 10.0 : metaCritic;
        }

        int? idNum;
        if (recordId.isNotEmpty) {
          final match = RegExp(r'\d+').firstMatch(recordId);
          if (match != null) {
            idNum = int.tryParse(match.group(0)!);
          }
        }

        String? flavorProfile;
        String? flavorVector;
        String? flavorTags;
        String? flavorSource;
        double? flavorMatchScore;

        if (idNum != null && flavorMap.containsKey(idNum)) {
          final fRow = flavorMap[idNum]!;

          String getFStr(int idx) {
            if (idx < 0 || idx >= fRow.length) return '';
            return fRow[idx]?.toString().trim() ?? '';
          }

          flavorProfile = getFStr(fFlavorProfileIdx);
          flavorVector = getFStr(fFlavorVectorIdx);
          flavorTags = getFStr(fFlavorTagsIdx);
          flavorSource = getFStr(fFlavorSourceIdx);

          final msStr = getFStr(fMatchScoreIdx);
          if (msStr.isNotEmpty) {
            flavorMatchScore = double.tryParse(msStr);
          }
        }

        companions.add(WhiskiesCompanion.insert(
          externalId: Value(recordId.isNotEmpty ? recordId : null),
          name: name,
          distillery: Value(getStr(distilleryIdx).isNotEmpty ? getStr(distilleryIdx) : null),
          country: Value(getStr(countryIdx).isNotEmpty ? getStr(countryIdx) : null),
          region: Value(getStr(regionIdx).isNotEmpty ? getStr(regionIdx) : null),
          category: Value(category.isNotEmpty ? category : null),
          age: Value(getInt(ageIdx)),
          abv: Value(getDouble(abvIdx)),
          caskType: Value(getStr(caskTypeIdx).isNotEmpty ? getStr(caskTypeIdx) : null),
          tastingNotes: Value(notesList.join(', ')),
          globalScore: Value(globalScore),
          flavorProfile: Value(flavorProfile?.isNotEmpty == true ? flavorProfile : null),
          flavorVector: Value(flavorVector?.isNotEmpty == true ? flavorVector : null),
          flavorTags: Value(flavorTags?.isNotEmpty == true ? flavorTags : null),
          flavorSource: Value(flavorSource?.isNotEmpty == true ? flavorSource : null),
          flavorMatchScore: Value(flavorMatchScore),
          type: Value(getStr(typeIdx).isNotEmpty ? getStr(typeIdx) : null),
          styleSimilarity: Value(styleSimilarityIdx >= 0 && getStr(styleSimilarityIdx).isNotEmpty ? getStr(styleSimilarityIdx) : null),
        ));
      }

      if (companions.isNotEmpty) {
        await db.batch((batch) {
          batch.insertAll(db.whiskies, companions);
        });
        debugPrint('DataSeedService: Seeded ${companions.length} whiskies.');
      }
    } catch (e, st) {
      debugPrint('DataSeedService Error: $e\n$st');
      // Intentionally not rethrowing to allow app to start even if seed fails
    }
  }
}
