import 'package:flutter_test/flutter_test.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:malt_radar/core/database/database.dart';

void main() {
  late AppDatabase database;

  setUp(() {
    database = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() async {
    await database.close();
  });

  test('Database opens with schema v5 and creates UserLists and UserListItems tables', () async {
    expect(database.schemaVersion, 5);

    // Verify UserLists table exists by inserting a test list
    final listId = await database.into(database.userLists).insert(
      UserListsCompanion.insert(
        name: 'Test List',
        sortOrder: const Value(0),
        createdAt: DateTime.now().toIso8601String(),
        updatedAt: DateTime.now().toIso8601String(),
      ),
    );

    expect(listId, 1);

    // Verify UserListItems table exists and enforces unique constraints
    await database.into(database.userListItems).insert(
      UserListItemsCompanion.insert(
        listId: listId,
        whiskyId: 101,
        createdAt: DateTime.now().toIso8601String(),
      ),
    );

    // Fetch back
    final items = await database.select(database.userListItems).get();
    expect(items.length, 1);
    expect(items.first.whiskyId, 101);

    // Duplicate add should fail
    expect(
      () => database.into(database.userListItems).insert(
        UserListItemsCompanion.insert(
          listId: listId,
          whiskyId: 101, // Duplicate whisky in same list
          createdAt: DateTime.now().toIso8601String(),
        ),
      ),
      throwsA(isA<SqliteException>()),
    );
  });
}
