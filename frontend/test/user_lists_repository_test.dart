import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';
import 'package:drift/drift.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/lists/data/repositories/user_lists_repository_impl.dart';

void main() {
  late AppDatabase db;
  late UserListsRepositoryImpl repository;

  setUp(() async {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    repository = UserListsRepositoryImpl(db);

    // Insert dummy whiskies for testing foreign key constraints
    await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        id: const Value(1),
        name: 'Test Whisky 1',
        globalScore: const Value(85),
      ),
    );
    await db.into(db.whiskies).insert(
      WhiskiesCompanion.insert(
        id: const Value(2),
        name: 'Test Whisky 2',
        globalScore: const Value(90),
      ),
    );
  });

  tearDown(() async {
    await db.close();
  });

  test('ensureDefaultLists creates 4 defaults and is idempotent', () async {
    await repository.ensureDefaultLists();
    var lists = await repository.getLists();
    expect(lists.length, 4);

    // Calling it again should not duplicate
    await repository.ensureDefaultLists();
    lists = await repository.getLists();
    expect(lists.length, 4);
    
    // Check names
    final names = lists.map((l) => l.name).toSet();
    expect(names.contains('Favorites'), isTrue);
    expect(names.contains('Wishlist'), isTrue);
    expect(names.contains('Tried'), isTrue);
    expect(names.contains('Collection'), isTrue);
  });

  test('create and update custom list', () async {
    final listId = await repository.createList('My List', description: 'desc');
    expect(listId, greaterThan(0));

    var lists = await repository.getLists();
    expect(lists.length, 1);
    expect(lists.first.name, 'My List');
    expect(lists.first.description, 'desc');

    await repository.updateList(listId, name: 'Updated Name');
    lists = await repository.getLists();
    expect(lists.first.name, 'Updated Name');
    expect(lists.first.description, 'desc'); // unchanged
  });

  test('prevent deleting system default list', () async {
    await repository.ensureDefaultLists();
    final lists = await repository.getLists();
    final defaultListId = lists.firstWhere((l) => l.isSystemDefault).id;

    expect(() => repository.deleteList(defaultListId), throwsException);
  });

  test('delete custom list removes items', () async {
    final listId = await repository.createList('My List');
    await repository.addWhiskyToList(listId, 1);
    
    expect((await repository.getListItems(listId)).length, 1);

    await repository.deleteList(listId);

    expect((await repository.getLists()).length, 0);
    // Since we join, getListItems won't find the list, but strictly we can also query DB directly to see items are gone
    final itemsInDb = await db.select(db.userListItems).get();
    expect(itemsInDb.isEmpty, isTrue);
  });

  test('add, toggle, remove whisky in list', () async {
    final listId = await repository.createList('My List');

    await repository.addWhiskyToList(listId, 1);
    var items = await repository.getListItems(listId);
    expect(items.length, 1);
    expect(items.first.whiskyId, 1);

    // Duplicate add should be ignored due to InsertMode.insertOrIgnore
    await repository.addWhiskyToList(listId, 1);
    items = await repository.getListItems(listId);
    expect(items.length, 1);

    // Toggle should remove
    await repository.toggleWhiskyInList(listId, 1);
    items = await repository.getListItems(listId);
    expect(items.isEmpty, isTrue);

    // Toggle should add
    await repository.toggleWhiskyInList(listId, 1);
    items = await repository.getListItems(listId);
    expect(items.length, 1);
  });

  test('getListsForWhisky returns correct lists', () async {
    final listId1 = await repository.createList('List 1');
    final listId2 = await repository.createList('List 2');
    
    await repository.addWhiskyToList(listId1, 1);
    await repository.addWhiskyToList(listId2, 1);

    final listsForWhisky = await repository.getListsForWhisky(1);
    expect(listsForWhisky.length, 2);
    
    final names = listsForWhisky.map((l) => l.name).toSet();
    expect(names.contains('List 1'), isTrue);
    expect(names.contains('List 2'), isTrue);
  });
}
