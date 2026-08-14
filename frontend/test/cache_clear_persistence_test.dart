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

  test('clearCache does not delete data (whiskies, favorites, scores, notes, settings)', () async {
    // 1. Seed some mock data
    final id = await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        externalId: const Value('test-1'),
        name: 'Glenmorangie 10',
      ),
    );

    // Add list, list items, settings, favorites, notes, scores
    await db.into(db.favorites).insert(FavoritesCompanion.insert(whiskyId: Value(id), addedAt: DateTime.now().toIso8601String()));
    await db.into(db.userWhiskyScores).insert(UserWhiskyScoresCompanion.insert(whiskyId: Value(id), score: 85, ratedAt: DateTime.now().toIso8601String()));
    await db.into(db.userNotes).insert(UserNotesCompanion.insert(whiskyId: Value(id), note: 'Great nose', updatedAt: DateTime.now().toIso8601String()));
    await db.into(db.userSettings).insert(UserSettingsCompanion.insert(key: 'reference_whisky_id', value: id.toString()));
    await db.into(db.userSettings).insert(UserSettingsCompanion.insert(key: 'reference_whisky_absolute_score', value: '90'));

    final listId = await db.into(db.userLists).insert(
      UserListsCompanion.insert(
        name: 'Tried List',
        sortOrder: const Value(0),
        createdAt: DateTime.now().toIso8601String(),
        updatedAt: DateTime.now().toIso8601String(),
      ),
    );
    await db.into(db.userListItems).insert(UserListItemsCompanion.insert(listId: listId, whiskyId: id, createdAt: DateTime.now().toIso8601String()));

    // 2. Call clearCache()
    await repository.clearCache();

    // 3. Verify counts
    final whiskies = await db.select(db.whiskies).get();
    expect(whiskies.length, 1, reason: 'Whiskies must not be deleted');

    final favorites = await db.select(db.favorites).get();
    expect(favorites.length, 1, reason: 'Favorites must not be deleted');

    final scores = await db.select(db.userWhiskyScores).get();
    expect(scores.length, 1, reason: 'Scores must not be deleted');

    final notes = await db.select(db.userNotes).get();
    expect(notes.length, 1, reason: 'Notes must not be deleted');

    final settings = await db.select(db.userSettings).get();
    expect(settings.length, 2, reason: 'Settings must not be deleted');

    final lists = await db.select(db.userLists).get();
    expect(lists.length, 1, reason: 'Lists must not be deleted');

    final listItems = await db.select(db.userListItems).get();
    expect(listItems.length, 1, reason: 'List items must not be deleted');
  });
}
