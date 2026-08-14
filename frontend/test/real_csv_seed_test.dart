import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/database/data_seed_service.dart';
import 'package:flutter/foundation.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';

void main() {
  test('DataSeedService reads fixture CSV', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    
    // Schema-accurate synthetic fixture (real catalog CSVs are gitignored and
    // never shipped to clients; the fixture exercises the same parse surface).
    final file = File('test/fixtures/whisky_database_merged_max.csv');
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
