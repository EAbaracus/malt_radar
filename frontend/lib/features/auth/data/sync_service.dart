import 'package:drift/drift.dart' hide Column;
import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/lists/data/repositories/user_lists_repository_impl.dart';
import 'auth_repository.dart';

/// Uploads the device's local personal data (favorites, scores, notes, lists)
/// to the account, and applies the server's snapshot for the simple per-whisky
/// relations back onto the local Drift store.
///
/// Sync keys on the whisky's stable backend `externalId` when present, falling
/// back to the local integer id. List-item graph merging is intentionally
/// server-side first: list rows are pushed and returned, but not blindly
/// over-written locally to avoid clobbering newer device edits.
class SyncService {
  final AppDatabase db;
  final AuthApi api;
  final AuthRepository repo;

  SyncService(this.db, this.api, this.repo);

  Future<String> _token() async {
    final t = await repo.loadToken();
    if (t == null) throw AuthApiException('Not signed in');
    return t;
  }

  Future<Map<String, dynamic>> push() async {
    final token = await _token();

    final whiskyRows = await (db.select(db.whiskies)).get();
    String keyFor(int localId) {
      for (final w in whiskyRows) {
        if (w.id == localId &&
            w.externalId != null &&
            w.externalId!.isNotEmpty) {
          return w.externalId!;
        }
      }
      return localId.toString();
    }

    final favs = await (db.select(db.favorites)).get();
    final scores = await (db.select(db.userWhiskyScores)).get();
    final notes = await (db.select(db.userNotes)).get();
    final lists = await (db.select(db.userLists)).get();
    final items = await (db.select(db.userListItems)).get();

    final payload = <String, List<Map<String, dynamic>>>{
      'favorites': [
        for (final f in favs)
          {'whisky_id': keyFor(f.whiskyId), 'updated_at': f.addedAt},
      ],
      'scores': [
        for (final s in scores)
          {
            'whisky_id': keyFor(s.whiskyId),
            'score': s.score,
            'updated_at': s.ratedAt,
          },
      ],
      'notes': [
        for (final n in notes)
          {
            'whisky_id': keyFor(n.whiskyId),
            'note': n.note,
            'updated_at': n.updatedAt,
          },
      ],
      'lists': [
        for (final l in lists)
          {
            'list_id': 'L${l.id}',
            'name': l.name,
            'default_type': l.defaultType,
            'sort_order': l.sortOrder,
            'updated_at': l.updatedAt,
          },
      ],
      'items': [
        for (final i in items)
          {
            'list_id': 'L${i.listId}',
            'whisky_id': keyFor(i.whiskyId),
            'sort_order': i.sortOrder,
            'note': i.note,
            'updated_at': i.createdAt,
          },
      ],
    };

    return await api.syncPush(token, payload);
  }

  /// Pulls the server snapshot and applies favorites / scores / notes / lists /
  /// list-items where the whisky maps to a local row. Returns the raw server
  /// snapshot for the UI.
  Future<Map<String, dynamic>> pull() async {
    final token = await _token();
    final server = await api.syncPull(token);

    final whiskyRows = await (db.select(db.whiskies)).get();
    final byExternal = <String, int>{};
    for (final w in whiskyRows) {
      if (w.externalId != null && w.externalId!.isNotEmpty) {
        byExternal[w.externalId!] = w.id;
      }
    }

    int? localId(dynamic ext) {
      if (ext == null) return null;
      final key = ext.toString();
      return byExternal.containsKey(key) ? byExternal[key] : null;
    }

    final now = DateTime.now().toIso8601String();

    // --- favorites ---
    final favList = (server['favorites'] as List?) ?? const [];
    for (final raw in favList) {
      final m = raw as Map<String, dynamic>;
      final id = localId(m['whisky_id']);
      if (id == null) continue;
      await db
          .into(db.favorites)
          .insertOnConflictUpdate(
            FavoritesCompanion.insert(
              whiskyId: Value(id),
              addedAt: (m['updated_at'] as String?) ?? now,
            ),
          );
    }

    // --- scores ---
    final scoreList = (server['scores'] as List?) ?? const [];
    for (final raw in scoreList) {
      final m = raw as Map<String, dynamic>;
      final id = localId(m['whisky_id']);
      if (id == null) continue;
      await db
          .into(db.userWhiskyScores)
          .insertOnConflictUpdate(
            UserWhiskyScoresCompanion.insert(
              whiskyId: Value(id),
              score: (m['score'] as num).toInt(),
              ratedAt: (m['updated_at'] as String?) ?? now,
            ),
          );
    }

    // --- notes ---
    final noteList = (server['notes'] as List?) ?? const [];
    for (final raw in noteList) {
      final m = raw as Map<String, dynamic>;
      final id = localId(m['whisky_id']);
      if (id == null) continue;
      await db
          .into(db.userNotes)
          .insertOnConflictUpdate(
            UserNotesCompanion.insert(
              whiskyId: Value(id),
              note: (m['note'] as String?) ?? '',
              updatedAt: (m['updated_at'] as String?) ?? now,
            ),
          );
    }

    // --- lists (system + custom) ---
    // Ensure default system lists exist locally (they are created lazily on
    // first UI interaction, but pull may run before any list screen is shown).
    final repo = UserListsRepositoryImpl(db);
    await repo.ensureDefaultLists();

    final serverLists = (server['lists'] as List?) ?? const [];
    final localLists = await (db.select(db.userLists)).get();
    final existingDefaultTypes = <String>{};
    for (final l in localLists) {
      if (l.defaultType != null) existingDefaultTypes.add(l.defaultType!);
    }
    for (final raw in serverLists) {
      final m = raw as Map<String, dynamic>;
      final defaultType = m['default_type'] as String?;
      final name = m['name'] as String? ?? 'List';
      final sortOrder = m['sort_order'] as int? ?? 0;
      final updatedAt = (m['updated_at'] as String?) ?? now;

      // System default lists are identified by default_type and already exist
      // locally — only update their metadata. Custom lists are matched by
      // the server list_id (L<n>). Since local ids are autoincrement and may
      // differ across devices, we key custom lists by name to avoid dupes.
      if (defaultType != null && existingDefaultTypes.contains(defaultType)) {
        final localList = localLists.firstWhere(
          (l) => l.defaultType == defaultType,
          orElse: () => throw StateError('unreachable'),
        );
        await (db.update(db.userLists)..where((tbl) => tbl.id.equals(localList.id))).write(
          UserListsCompanion(
            name: Value(name),
            description: const Value.absent(),
            sortOrder: Value(sortOrder),
            updatedAt: Value(updatedAt),
            isSystemDefault: const Value(true),
          ),
        );
      } else {
        await db.into(db.userLists).insert(
          UserListsCompanion.insert(
            name: name,
            defaultType: Value(defaultType),
            sortOrder: Value(sortOrder),
            createdAt: now,
            updatedAt: updatedAt,
            isSystemDefault: Value(defaultType != null),
          ),
          mode: InsertMode.insertOrIgnore,
        );
      }
    }

    // --- list items (sync_list_items -> user_list_items) ---
    // The server stores list_id as 'L<n>' (the pushing device's local autoinc
    // id), which is NOT reliable cross-device. We resolve the local list via the
    // server-side list definition: for system defaults, match by default_type;
    // for custom lists, match by name.
    final serverItems = (server['items'] as List?) ?? const [];
    final freshLocalLists = await (db.select(db.userLists)).get();

    // Build server list_id -> server list row mapping (for default_type / name lookup)
    final serverListRows = (server['lists'] as List?) ?? const [];
    final serverListByServerId = <String, Map<String, dynamic>>{};
    for (final raw in serverListRows) {
      final m = raw as Map<String, dynamic>;
      final sid = m['list_id']?.toString();
      if (sid != null) serverListByServerId[sid] = m;
    }

    // Build default_type -> local id and name -> local id for resolution
    final localByDefaultType = <String, int>{};
    final localByName = <String, int>{};
    for (final l in freshLocalLists) {
      if (l.defaultType != null) localByDefaultType[l.defaultType!] = l.id;
      localByName[l.name] = l.id;
    }

    for (final raw in serverItems) {
      final m = raw as Map<String, dynamic>;
      final serverListId = m['list_id']?.toString();
      final whiskyKey = m['whisky_id']?.toString();
      final localWhiskyId = localId(whiskyKey);
      if (localWhiskyId == null) continue; // whisky not in local DB

      int? listId;
      // Try to resolve the server list_id to a local list
      final serverListRow = serverListByServerId[serverListId];
      if (serverListRow != null) {
        final dt = serverListRow['default_type'] as String?;
        if (dt != null && localByDefaultType.containsKey(dt)) {
          listId = localByDefaultType[dt];
        } else {
          // Custom list: match by name
          final nm = serverListRow['name'] as String?;
          if (nm != null && localByName.containsKey(nm)) {
            listId = localByName[nm];
          }
        }
      }
      if (listId == null) continue;

      final sortOrderVal = m['sort_order'] as int? ?? 0;
      final noteVal = m['note'] as String?;
      final createdAt = (m['updated_at'] as String?) ?? now;

      await db.into(db.userListItems).insert(
        UserListItemsCompanion.insert(
          listId: listId,
          whiskyId: localWhiskyId,
          note: Value(noteVal),
          sortOrder: Value(sortOrderVal),
          createdAt: createdAt,
        ),
        mode: InsertMode.insertOrIgnore,
      );
    }

    return server;
  }
}
