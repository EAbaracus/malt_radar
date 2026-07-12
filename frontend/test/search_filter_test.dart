import 'package:flutter_test/flutter_test.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/api/api_client.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/whisky/data/repositories/whisky_repository_impl.dart';
import 'package:malt_radar/features/whisky/domain/repositories/whisky_repository.dart';

void main() {
  late AppDatabase db;
  late WhiskyRepository repo;

  setUp(() async {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    repo = WhiskyRepositoryImpl(db, ApiClient());

    // Seed test whiskies directly into db
    await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        externalId: const Value('W1'),
        name: 'Lagavulin 16',
        country: const Value('Scotland'),
        region: const Value('Islay'),
        category: const Value('Scotch'),
        type: const Value('Malt'),
        flavorProfile: const Value('{"smoky_peaty": 8.0, "fruity": 2.0, "sweet": 3.0}'),
        caskType: const Value('Sherry Oak'),
      ),
    );

    await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        externalId: const Value('W2'),
        name: 'Macallan 12',
        country: const Value('Scotland'),
        region: const Value('Speyside'),
        category: const Value('Scotch'),
        type: const Value('Malt'),
        flavorProfile: const Value('{"smoky_peaty": 0.0, "fruity": 6.0, "sweet": 7.0}'),
        caskType: const Value('Sherry Cask'),
      ),
    );

    await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        externalId: const Value('W3'),
        name: 'Buffalo Trace',
        country: const Value('USA'),
        region: const Value('Kentucky'),
        category: const Value('Bourbon'),
        type: const Value('Bourbon'),
        flavorProfile: const Value('{"smoky_peaty": 0.0, "fruity": 3.0, "sweet": 8.0}'),
        caskType: const Value('Oak Cask'),
      ),
    );
  });

  tearDown(() async {
    await db.close();
  });

  test('Clicking region chip filters results', () async {
    final speysideList = await repo.watchLocalWhiskies(filters: ['Speyside']).first;
    expect(speysideList.length, 1);
    expect(speysideList.first.name, 'Macallan 12');

    final islayList = await repo.watchLocalWhiskies(filters: ['Islay']).first;
    expect(islayList.length, 1);
    expect(islayList.first.name, 'Lagavulin 16');
  });

  test('Clicking flavor chip filters results', () async {
    final peatedList = await repo.watchLocalWhiskies(filters: ['Peated']).first;
    expect(peatedList.length, 1);
    expect(peatedList.first.name, 'Lagavulin 16');

    final sweetList = await repo.watchLocalWhiskies(filters: ['Sweet']).first;
    expect(sweetList.length, 3);
  });

  test('Multiple chips combine correctly (AND)', () async {
    final list = await repo.watchLocalWhiskies(filters: ['Islay', 'Peated']).first;
    expect(list.length, 1);
    expect(list.first.name, 'Lagavulin 16');

    final list2 = await repo.watchLocalWhiskies(filters: ['Speyside', 'Peated']).first;
    expect(list2.length, 0);
  });

  test('Removing chip restores previous result set', () async {
    final initial = await repo.watchLocalWhiskies().first;
    expect(initial.length, 3);

    final filtered = await repo.watchLocalWhiskies(filters: ['Islay']).first;
    expect(filtered.length, 1);

    final restored = await repo.watchLocalWhiskies(filters: []).first;
    expect(restored.length, 3);
  });

  test('No -like values exist in primary taxonomy', () async {
    final list = await repo.watchLocalWhiskies().first;
    for (final w in list) {
      expect(w.category, isNot(contains('-like')));
    }
  });
}
