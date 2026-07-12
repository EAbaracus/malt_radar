import 'package:flutter_test/flutter_test.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/core/database/data_seed_service.dart';
import 'package:flutter/widgets.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;

  const mockCsv = '''record_id,record_type,canonical_name,whisky_name,distillery,brand_or_company,country,region,origin_raw,type,class,age_years,age_raw,abv_percent,bottle_size,cask_type,finish_type,smoke_level,peat_level,sweetness,spiciness,body,aroma_tags,nose_notes,palate_notes,finish_notes,pairing_notes,general_notes,user_score_100,meta_critic,style_similarity
WDB-00001,whisky_product,Test Whisky,wname,Test Distillery,brand,Scotland,Speyside,origin,Malt,Scotch,12,12y,40,70cl,Bourbon Cask,finish,smoke,peat,sweet,spice,body,aroma,Apple,Honey,Oak,pairing,general,85,90,"{""style"": ""Single Malt Style"", ""confidence"": 0.9}"
WDB-00002,whisky_product,Test Whisky 2,wname2,Test Distillery 2,brand2,Scotland,Islay,origin2,Malt,Scotch,NAS,nas,46,70cl,Sherry Cask,finish2,smoke2,peat2,sweet2,spice2,body2,aroma2,Smoke,Peat,Ash,pairing2,general2,90,95,"{""style"": ""Single Malt Style"", ""confidence"": 0.9}"
''';

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  test('Database is initially empty', () async {
    final countExp = db.whiskies.id.count();
    final query = db.selectOnly(db.whiskies)..addColumns([countExp]);
    final result = await query.getSingle();
    final count = result.read(countExp) ?? 0;
    
    expect(count, 0);
  });

  test('DataSeedService reads mock CSV and populates DB', () async {
    await DataSeedService.seedDatabaseIfEmpty(db, testCsvString: mockCsv);
    
    final whiskies = await db.select(db.whiskies).get();
    expect(whiskies.length, 2);
    
    final first = whiskies.firstWhere((w) => w.externalId == 'WDB-00001');
    expect(first.name, 'Test Whisky');
    expect(first.distillery, 'Test Distillery');
    expect(first.country, 'Scotland');
    expect(first.region, 'Speyside');
    expect(first.category, 'Scotch');
    expect(first.type, 'Malt');
    expect(first.styleSimilarity, contains('Single Malt Style'));
    expect(first.age, 12);
    expect(first.abv, 40.0);
    expect(first.caskType, 'Bourbon Cask');
    expect(first.tastingNotes, contains('Burun: Apple'));
    expect(first.tastingNotes, contains('Damak: Honey'));
    expect(first.tastingNotes, contains('Bitiş: Oak'));
    expect(first.globalScore, 85.0);
  });

  test('DataSeedService is idempotent', () async {
    await DataSeedService.seedDatabaseIfEmpty(db, testCsvString: mockCsv);
    final countExp = db.whiskies.id.count();
    var query = db.selectOnly(db.whiskies)..addColumns([countExp]);
    var result = await query.getSingle();
    var count = result.read(countExp) ?? 0;
    expect(count, 2);

    // Call it again
    await DataSeedService.seedDatabaseIfEmpty(db, testCsvString: mockCsv);
    
    query = db.selectOnly(db.whiskies)..addColumns([countExp]);
    result = await query.getSingle();
    count = result.read(countExp) ?? 0;
    // Count should still be 2, because it returns early
    expect(count, 2);
  });
}
