import 'dart:convert';
import 'package:malt_radar/core/database/database.dart';
import '../domain/auth_user.dart';

/// Persists the account session in the local Drift `UserSettings` key-value
/// store (same mechanism as the age gate / language; no new dependency).
class AuthRepository {
  final AppDatabase db;
  static const _tokenKey = 'auth_token';
  static const _userKey = 'auth_user';

  AuthRepository(this.db);

  Future<String?> loadToken() async {
    final row = await (db.select(
      db.userSettings,
    )..where((t) => t.key.equals(_tokenKey))).getSingleOrNull();
    return row?.value;
  }

  Future<AuthUser?> loadUser() async {
    final row = await (db.select(
      db.userSettings,
    )..where((t) => t.key.equals(_userKey))).getSingleOrNull();
    if (row == null || row.value.isEmpty) return null;
    try {
      return AuthUser.fromJson(jsonDecode(row.value) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<void> saveSession(String token, AuthUser user) async {
    await db
        .into(db.userSettings)
        .insertOnConflictUpdate(
          UserSettingsCompanion.insert(key: _tokenKey, value: token),
        );
    await db
        .into(db.userSettings)
        .insertOnConflictUpdate(
          UserSettingsCompanion.insert(
            key: _userKey,
            value: jsonEncode(user.toJson()),
          ),
        );
  }

  Future<void> clearSession() async {
    await (db.delete(
      db.userSettings,
    )..where((t) => t.key.isIn([_tokenKey, _userKey]))).go();
  }
}
