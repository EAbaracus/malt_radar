import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'database.g.dart';

@DataClassName('WhiskyEntity')
class Whiskies extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get externalId => text().nullable()();
  TextColumn get name => text().withLength(min: 1, max: 100)();
  TextColumn get country => text().nullable()();
  TextColumn get region => text().nullable()();
  TextColumn get category => text().nullable()();
  TextColumn get distillery => text().nullable()();
  IntColumn get age => integer().nullable()();
  RealColumn get abv => real().nullable()();
  TextColumn get caskType => text().nullable()();
  RealColumn get defaultPrice => real().nullable()();
  TextColumn get currency => text().nullable()();
  TextColumn get sourceName => text().nullable()();
  TextColumn get sourceUrl => text().nullable()();
  TextColumn get fetchedAt => text().nullable()();
  TextColumn get tastingNotes => text().withDefault(const Constant(''))();
  TextColumn get companionSuggestions => text().withDefault(const Constant(''))();
  RealColumn get globalScore => real().nullable()();
  
  // Flavor attributes
  TextColumn get flavorProfile => text().nullable()();
  TextColumn get flavorVector => text().nullable()();
  TextColumn get flavorTags => text().nullable()();
  TextColumn get flavorSource => text().nullable()();
  RealColumn get flavorMatchScore => real().nullable()();
  TextColumn get type => text().nullable()();
  TextColumn get styleSimilarity => text().nullable()();
}

class UserSettings extends Table {
  TextColumn get key => text()();
  TextColumn get value => text()();
  @override
  Set<Column> get primaryKey => {key};
}

class UserWhiskyScores extends Table {
  IntColumn get whiskyId => integer()();
  IntColumn get score => integer()();
  TextColumn get ratedAt => text()();
  @override
  Set<Column> get primaryKey => {whiskyId};
}

class Favorites extends Table {
  IntColumn get whiskyId => integer()();
  TextColumn get addedAt => text()();
  @override
  Set<Column> get primaryKey => {whiskyId};
}

class UserNotes extends Table {
  IntColumn get whiskyId => integer()();
  TextColumn get note => text()();
  TextColumn get updatedAt => text()();
  @override
  Set<Column> get primaryKey => {whiskyId};
}

class WhiskyPrices extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get whiskyId => integer()();
  TextColumn get sourceName => text()();
  RealColumn get price => real()();
  TextColumn get currency => text()();
  TextColumn get country => text()();
  TextColumn get sourceUrl => text()();
  TextColumn get fetchedAt => text()();
  BoolColumn get isManual => boolean().withDefault(const Constant(false))();
}

class ExternalSources extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get whiskyId => integer()();
  TextColumn get sourceName => text()();
  TextColumn get sourceUrl => text()();
  TextColumn get externalId => text()();
  TextColumn get fetchedAt => text()();
}

@DataClassName('UserListEntity')
class UserLists extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1, max: 100)();
  TextColumn get description => text().nullable()();
  TextColumn get defaultType => text().nullable()();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  TextColumn get createdAt => text()();
  TextColumn get updatedAt => text()();
  BoolColumn get isSystemDefault => boolean().withDefault(const Constant(false))();
}

@DataClassName('UserListItemEntity')
class UserListItems extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get listId => integer()();
  IntColumn get whiskyId => integer()();
  TextColumn get note => text().nullable()();
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  TextColumn get createdAt => text()();

  @override
  List<Set<Column>> get uniqueKeys => [{listId, whiskyId}];
}

@DriftDatabase(tables: [
  Whiskies,
  UserSettings,
  UserWhiskyScores,
  Favorites,
  UserNotes,
  WhiskyPrices,
  ExternalSources,
  UserLists,
  UserListItems
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(
    name: 'malt_radar_v2',
    web: DriftWebOptions(
      sqlite3Wasm: Uri.parse('sqlite3.wasm'),
      driftWorker: Uri.parse('drift_worker.js'),
    ),
  ));

  AppDatabase.forTesting(super.e);

  @override
  int get schemaVersion => 6;

  @override
  MigrationStrategy get migration {
    return MigrationStrategy(
      onCreate: (Migrator m) async {
        await m.createAll();
      },
      onUpgrade: (Migrator m, int from, int to) async {
        if (from < 2) {
          await m.addColumn(whiskies, whiskies.globalScore);
        }
        if (from < 3) {
          await m.addColumn(whiskies, whiskies.distillery);
        }
        if (from < 4) {
          await m.addColumn(whiskies, whiskies.flavorProfile);
          await m.addColumn(whiskies, whiskies.flavorVector);
          await m.addColumn(whiskies, whiskies.flavorTags);
          await m.addColumn(whiskies, whiskies.flavorSource);
          await m.addColumn(whiskies, whiskies.flavorMatchScore);
        }
        if (from < 5) {
          await m.createTable(userLists);
          await m.createTable(userListItems);

          await customStatement('''
            INSERT INTO user_lists (name, default_type, sort_order, created_at, updated_at, is_system_default)
            VALUES ('Favorites', 'favorites', 0, datetime('now'), datetime('now'), 1),
                   ('Wishlist', 'wishlist', 1, datetime('now'), datetime('now'), 1),
                   ('Tried', 'tried', 2, datetime('now'), datetime('now'), 1),
                   ('Collection', 'collection', 3, datetime('now'), datetime('now'), 1);
          ''');

          await customStatement('''
            INSERT INTO user_list_items (list_id, whisky_id, sort_order, created_at)
            SELECT (SELECT id FROM user_lists WHERE default_type = 'favorites'), whisky_id, 0, added_at
            FROM favorites;
          ''');
        }
        if (from < 6) {
          await m.addColumn(whiskies, whiskies.type);
          await m.addColumn(whiskies, whiskies.styleSimilarity);
        }
      },
    );
  }
}
