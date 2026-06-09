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

@DriftDatabase(tables: [
  Whiskies,
  UserSettings,
  UserWhiskyScores,
  Favorites,
  UserNotes,
  WhiskyPrices,
  ExternalSources
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(
    name: 'malt_radar_v2',
    web: DriftWebOptions(
      sqlite3Wasm: Uri.parse('sqlite3.wasm'),
      driftWorker: Uri.parse('drift_worker.js'),
    ),
  ));

  @override
  int get schemaVersion => 1;
}
