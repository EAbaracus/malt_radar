import 'package:drift/drift.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';
import 'package:malt_radar/features/lists/domain/models/user_list.dart';
import 'package:malt_radar/features/lists/domain/models/user_list_item.dart';
import 'package:malt_radar/features/lists/domain/repositories/user_lists_repository.dart';

class UserListsRepositoryImpl implements UserListsRepository {
  final AppDatabase _db;

  UserListsRepositoryImpl(this._db);

  @override
  Future<void> ensureDefaultLists() async {
    // Check if defaults exist
    final count = await _db.customSelect(
      'SELECT COUNT(*) AS c FROM user_lists WHERE is_system_default = 1'
    ).map((row) => row.read<int>('c')).getSingle();

    if (count > 0) return; // Assume already seeded

    await _db.into(_db.userLists).insert(
      UserListsCompanion.insert(
        name: 'Favorites',
        defaultType: const Value('favorites'),
        sortOrder: const Value(0),
        isSystemDefault: const Value(true),
        createdAt: DateTime.now().toIso8601String(),
        updatedAt: DateTime.now().toIso8601String(),
      ),
      mode: InsertMode.insertOrIgnore,
    );

    await _db.into(_db.userLists).insert(
      UserListsCompanion.insert(
        name: 'Wishlist',
        defaultType: const Value('wishlist'),
        sortOrder: const Value(1),
        isSystemDefault: const Value(true),
        createdAt: DateTime.now().toIso8601String(),
        updatedAt: DateTime.now().toIso8601String(),
      ),
      mode: InsertMode.insertOrIgnore,
    );

    await _db.into(_db.userLists).insert(
      UserListsCompanion.insert(
        name: 'Tried',
        defaultType: const Value('tried'),
        sortOrder: const Value(2),
        isSystemDefault: const Value(true),
        createdAt: DateTime.now().toIso8601String(),
        updatedAt: DateTime.now().toIso8601String(),
      ),
      mode: InsertMode.insertOrIgnore,
    );

    await _db.into(_db.userLists).insert(
      UserListsCompanion.insert(
        name: 'Collection',
        defaultType: const Value('collection'),
        sortOrder: const Value(3),
        isSystemDefault: const Value(true),
        createdAt: DateTime.now().toIso8601String(),
        updatedAt: DateTime.now().toIso8601String(),
      ),
      mode: InsertMode.insertOrIgnore,
    );
  }

  @override
  Future<int> createList(String name, {String? description}) async {
    final now = DateTime.now().toIso8601String();
    
    // Get max sort order
    final maxSortOrderResult = await _db.customSelect(
      'SELECT MAX(sort_order) AS m FROM user_lists'
    ).map((row) => row.read<int?>('m') ?? 0).getSingle();

    return await _db.into(_db.userLists).insert(
      UserListsCompanion.insert(
        name: name,
        description: Value(description),
        sortOrder: Value(maxSortOrderResult + 1),
        createdAt: now,
        updatedAt: now,
      )
    );
  }

  @override
  Future<void> updateList(int id, {String? name, String? description, int? sortOrder}) async {
    final now = DateTime.now().toIso8601String();
    
    await (_db.update(_db.userLists)..where((tbl) => tbl.id.equals(id))).write(
      UserListsCompanion(
        name: name != null ? Value(name) : const Value.absent(),
        description: description != null ? Value(description) : const Value.absent(),
        sortOrder: sortOrder != null ? Value(sortOrder) : const Value.absent(),
        updatedAt: Value(now),
      )
    );
  }

  @override
  Future<void> deleteList(int id) async {
    final list = await (_db.select(_db.userLists)..where((tbl) => tbl.id.equals(id))).getSingleOrNull();
    if (list == null) return;

    if (list.isSystemDefault) {
      throw Exception('Cannot delete a system default list');
    }

    await _db.transaction(() async {
      await (_db.delete(_db.userListItems)..where((tbl) => tbl.listId.equals(id))).go();
      await (_db.delete(_db.userLists)..where((tbl) => tbl.id.equals(id))).go();
    });
  }

  @override
  Stream<List<UserList>> watchLists() {
    final query = _db.select(_db.userLists).join([
      leftOuterJoin(
        _db.userListItems,
        _db.userListItems.listId.equalsExp(_db.userLists.id),
      ),
    ])
      ..orderBy([OrderingTerm.asc(_db.userLists.sortOrder)]);

    return query.watch().map((rows) {
      final listMap = <int, UserList>{};
      
      for (final row in rows) {
        final listEntity = row.readTable(_db.userLists);
        final itemEntity = row.readTableOrNull(_db.userListItems);

        if (!listMap.containsKey(listEntity.id)) {
          listMap[listEntity.id] = UserList.fromEntity(listEntity, itemCount: 0);
        }

        if (itemEntity != null) {
          final currentList = listMap[listEntity.id]!;
          listMap[listEntity.id] = currentList.copyWith(itemCount: currentList.itemCount + 1);
        }
      }

      return listMap.values.toList();
    });
  }

  @override
  Future<List<UserList>> getLists() async {
    final query = _db.select(_db.userLists).join([
      leftOuterJoin(
        _db.userListItems,
        _db.userListItems.listId.equalsExp(_db.userLists.id),
      ),
    ])
      ..orderBy([OrderingTerm.asc(_db.userLists.sortOrder)]);

    final rows = await query.get();
    
    final listMap = <int, UserList>{};
    for (final row in rows) {
      final listEntity = row.readTable(_db.userLists);
      final itemEntity = row.readTableOrNull(_db.userListItems);

      if (!listMap.containsKey(listEntity.id)) {
        listMap[listEntity.id] = UserList.fromEntity(listEntity, itemCount: 0);
      }

      if (itemEntity != null) {
        final currentList = listMap[listEntity.id]!;
        listMap[listEntity.id] = currentList.copyWith(itemCount: currentList.itemCount + 1);
      }
    }

    return listMap.values.toList();
  }

  @override
  Stream<List<UserListItem>> watchListItems(int listId) {
    final query = _db.select(_db.userListItems).join([
      leftOuterJoin(
        _db.whiskies,
        _db.whiskies.id.equalsExp(_db.userListItems.whiskyId),
      ),
    ])
      ..where(_db.userListItems.listId.equals(listId))
      ..orderBy([OrderingTerm.asc(_db.userListItems.sortOrder), OrderingTerm.desc(_db.userListItems.createdAt)]);

    return query.watch().map((rows) {
      return rows.map((row) {
        final itemEntity = row.readTable(_db.userListItems);
        final whiskyEntity = row.readTableOrNull(_db.whiskies);
        return UserListItem.fromEntity(
          itemEntity,
          whisky: whiskyEntity != null
              ? Whisky.fromEntities(whisky: whiskyEntity)
              : null,
        );
      }).toList();
    });
  }

  @override
  Future<List<UserListItem>> getListItems(int listId) async {
    final query = _db.select(_db.userListItems).join([
      leftOuterJoin(
        _db.whiskies,
        _db.whiskies.id.equalsExp(_db.userListItems.whiskyId),
      ),
    ])
      ..where(_db.userListItems.listId.equals(listId))
      ..orderBy([OrderingTerm.asc(_db.userListItems.sortOrder), OrderingTerm.desc(_db.userListItems.createdAt)]);

    final rows = await query.get();

    return rows.map((row) {
      final itemEntity = row.readTable(_db.userListItems);
      final whiskyEntity = row.readTableOrNull(_db.whiskies);
      return UserListItem.fromEntity(
        itemEntity,
        whisky: whiskyEntity != null
            ? Whisky.fromEntities(whisky: whiskyEntity)
            : null,
      );
    }).toList();
  }

  @override
  Future<void> addWhiskyToList(int listId, int whiskyId, {String? note}) async {
    final now = DateTime.now().toIso8601String();
    
    // Get max sort order
    final maxSortOrderResult = await _db.customSelect(
      'SELECT MAX(sort_order) AS m FROM user_list_items WHERE list_id = ?',
      variables: [Variable.withInt(listId)]
    ).map((row) => row.read<int?>('m') ?? 0).getSingle();

    await _db.into(_db.userListItems).insert(
      UserListItemsCompanion.insert(
        listId: listId,
        whiskyId: whiskyId,
        note: Value(note),
        sortOrder: Value(maxSortOrderResult + 1),
        createdAt: now,
      ),
      mode: InsertMode.insertOrIgnore, // Prevent duplicates
    );
  }

  @override
  Future<void> removeWhiskyFromList(int listId, int whiskyId) async {
    await (_db.delete(_db.userListItems)
      ..where((tbl) => tbl.listId.equals(listId) & tbl.whiskyId.equals(whiskyId))
    ).go();
  }

  @override
  Future<bool> isWhiskyInList(int listId, int whiskyId) async {
    final query = _db.select(_db.userListItems)
      ..where((tbl) => tbl.listId.equals(listId) & tbl.whiskyId.equals(whiskyId));
    
    final item = await query.getSingleOrNull();
    return item != null;
  }

  @override
  Future<void> toggleWhiskyInList(int listId, int whiskyId) async {
    final isInList = await isWhiskyInList(listId, whiskyId);
    if (isInList) {
      await removeWhiskyFromList(listId, whiskyId);
    } else {
      await addWhiskyToList(listId, whiskyId);
    }
  }

  @override
  Future<List<UserList>> getListsForWhisky(int whiskyId) async {
    final query = _db.select(_db.userLists).join([
      innerJoin(
        _db.userListItems,
        _db.userListItems.listId.equalsExp(_db.userLists.id),
      ),
    ])
      ..where(_db.userListItems.whiskyId.equals(whiskyId));

    final rows = await query.get();
    
    return rows.map((row) {
      final listEntity = row.readTable(_db.userLists);
      // Item count isn't needed here typically, or we could leave it 0
      return UserList.fromEntity(listEntity, itemCount: 0); 
    }).toList();
  }
}
