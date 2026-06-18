import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/database/data_seed_service.dart';
import 'package:malt_radar/features/flavor/presentation/providers/similar_flavor_provider.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:drift/native.dart';
import 'dart:io';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Similar Flavor calculates successfully', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    
    // Read the actual CSV file
    final file = File('assets/data/whisky_database_merged_max.csv');
    final csvString = await file.readAsString();
    
    await DataSeedService.seedDatabaseIfEmpty(db, testCsvString: csvString);
    
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
