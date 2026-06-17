import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:drift/drift.dart';
import 'package:csv/csv.dart';
import 'package:malt_radar/core/database/database.dart';

class DataSeedService {
  static const String _csvPath = 'assets/data/whisky_database_merged_max.csv';

  static Future<void> seedDatabaseIfEmpty(AppDatabase db, {String? testCsvString}) async {
    try {
      final countExp = db.whiskies.id.count();
      final query = db.selectOnly(db.whiskies)..addColumns([countExp]);
      final result = await query.getSingle();
      final count = result.read(countExp) ?? 0;

      if (count > 0) {
        return; // Already seeded
      }

      final csvString = testCsvString ?? await rootBundle.loadString(_csvPath);
      // Fallback to '\n' or '\r\n' is usually handled well by CsvToListConverter
      final List<List<dynamic>> csvTable = const CsvToListConverter(eol: '\n', fieldDelimiter: ',').convert(csvString);

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
        
        final globalScore = getDouble(userScoreIdx) ?? getDouble(metaCriticIdx);

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
