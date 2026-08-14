import 'package:drift/drift.dart' hide Column;
import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/database/database.dart';
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

  /// Pulls the server snapshot and applies favorites / scores / notes where the
  /// whisky maps to a local row. Returns the raw server snapshot for the UI.
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

    return server;
  }
}
