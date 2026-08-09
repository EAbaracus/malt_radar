import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/data/repositories/db_whisky_repository_impl.dart';
import 'package:flutter/widgets.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;
  late DbWhiskyRepositoryImpl repository;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    repository = DbWhiskyRepositoryImpl(db, DbWhiskyApiClient());
  });

  tearDown(() async {
    await db.close();
  });

  test('clearReferenceWhisky removes only reference_whisky_id and reference_whisky_absolute_score', () async {
    // 1. Seed some mock data
    final id = await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        externalId: const Value('test-1'),
        name: 'Glenmorangie 10',
      ),
    );

    // Set settings
    await db.into(db.userSettings).insert(UserSettingsCompanion.insert(key: 'reference_whisky_id', value: id.toString()));
    await db.into(db.userSettings).insert(UserSettingsCompanion.insert(key: 'reference_whisky_absolute_score', value: '90'));
    await db.into(db.userSettings).insert(UserSettingsCompanion.insert(key: 'other_setting', value: 'some_value'));

    // 2. Call clearReferenceWhisky()
    await repository.clearReferenceWhisky();

    // 3. Verify settings table
    final settings = await db.select(db.userSettings).get();
    
    // Check that reference_whisky keys are deleted, but other_setting is preserved
    final hasRefId = settings.any((s) => s.key == 'reference_whisky_id');
    final hasRefScore = settings.any((s) => s.key == 'reference_whisky_absolute_score');
    final hasOther = settings.any((s) => s.key == 'other_setting');

    expect(hasRefId, isFalse, reason: 'reference_whisky_id must be deleted');
    expect(hasRefScore, isFalse, reason: 'reference_whisky_absolute_score must be deleted');
    expect(hasOther, isTrue, reason: 'other_setting must be preserved');

    // 4. Verify that whisky row itself is not deleted
    final whiskies = await db.select(db.whiskies).get();
    expect(whiskies.length, 1, reason: 'clearReferenceWhisky must not delete the actual whisky row');
  });
}
