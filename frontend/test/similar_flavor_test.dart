import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/database/data_seed_service.dart';
import 'package:malt_radar/features/flavor/presentation/providers/similar_flavor_provider.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:csv/csv.dart';
import 'package:drift/drift.dart' show Value;
import 'package:drift/native.dart';
import 'dart:io';

/// Bilinçli kapsam genişletmesi (2026-08-16): seedDatabaseIfEmpty artık
/// flavorCsvString kabul etmiyor (d5b3fd7, anti-scrape; flavor CSV asset'ten
/// geliyor ama pubspec'te yorumlu). Flavor profilini fixture'tan name-join ile
/// doğrudan lokal DB'ye bağlar — eski seed yolunun semantik eşdeğeri.
Future<void> _attachFlavorProfilesByName(AppDatabase db, String flavorCsv) async {
  final flavorTable =
      const CsvToListConverter(eol: '\n', fieldDelimiter: ',').convert(flavorCsv);
  if (flavorTable.length <= 1) return;
  final fHeaders = flavorTable[0].map((e) => e.toString().trim()).toList();
  final nameIdx = fHeaders.indexOf('whisky_name');
  final profileIdx = fHeaders.indexOf('flavor_profile');
  if (nameIdx < 0 || profileIdx < 0) return;

  final byName = <String, String>{};
  for (var i = 1; i < flavorTable.length; i++) {
    final r = flavorTable[i];
    if (r.isEmpty || nameIdx >= r.length || profileIdx >= r.length) continue;
    final n = (r[nameIdx] ?? '').toString().trim();
    if (n.isNotEmpty) byName[n] = (r[profileIdx] ?? '').toString();
  }

  final all = await (db.select(db.whiskies)).get();
  for (final w in all) {
    final profile = byName[w.name];
    if (profile != null) {
      await (db.update(db.whiskies)..where((t) => t.id.equals(w.id)))
          .write(WhiskiesCompanion(flavorProfile: Value(profile)));
    }
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Similar Flavor calculates successfully', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());

    // Read the schema-accurate fixture CSVs (NOT the real backend data dir —
    // real catalog CSVs are gitignored and never shipped to clients. Fixtures
    // are synthetic, schema-accurate rows so logic is verified against a
    // representative parse surface without shipping catalog data).
    final file = File('test/fixtures/whisky_database_merged_max.csv');
    final csvString = await file.readAsString();
    final flavorFile = File('test/fixtures/flavor_profiles.csv');
    final flavorCsv = await flavorFile.readAsString();

    await DataSeedService.seedDatabaseIfEmpty(db, testCsvString: csvString);
    await _attachFlavorProfilesByName(db, flavorCsv);
    
    final whiskiesWithFlavor = await (db.select(db.whiskies)..where((t) => t.flavorProfile.isNotNull())).get();
    
    expect(whiskiesWithFlavor.length, greaterThan(0), reason: 'Flavor profile should have been seeded');
    debugPrint('Found ${whiskiesWithFlavor.length} whiskies with flavor profile.');

    // Pick one
    final target = whiskiesWithFlavor.first;
    debugPrint('Testing similar flavor for: ${target.name} (ID: ${target.id})');
    
    final container = ProviderContainer(
      overrides: [
        appDatabaseProvider.overrideWithValue(db),
      ],
    );
    
    // Read the provider
    final resultAsync = await container.read(similarFlavorWhiskiesProvider(target.id).future);
    
    debugPrint('Similar whiskies count: ${resultAsync.length}');
    
    expect(resultAsync.length, greaterThan(0), reason: 'Should return at least 1 similar whisky');
    
    // Ensure the target is not in the list
    final hasTarget = resultAsync.any((w) => w.id == target.id);
    expect(hasTarget, isFalse, reason: 'Similar list should not include the target whisky itself');
    
    await db.close();
  });
}
