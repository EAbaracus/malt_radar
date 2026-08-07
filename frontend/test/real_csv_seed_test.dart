import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/database/data_seed_service.dart';
import 'package:flutter/foundation.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';

void main() {
  test('DataSeedService reads real CSV', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    
    // Read the canonical CSV file from the backend data dir (the client must
    // NOT bundle catalog data; tests read the single canonical source).
    final file = File('../backend/data/whisky_database_merged_max.csv');
    expect(file.existsSync(), isTrue);
    
    final csvString = await file.readAsString();
    
    await DataSeedService.seedDatabaseIfEmpty(db, testCsvString: csvString);
    
    final countExp = db.whiskies.id.count();
    final query = db.selectOnly(db.whiskies)..addColumns([countExp]);
    final result = await query.getSingle();
    final count = result.read(countExp) ?? 0;
    
    debugPrint('Seeded count: $count');
    expect(count, greaterThan(0));
    
    await db.close();
  });
}
