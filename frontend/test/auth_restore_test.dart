// Unit tests for the session-restore flow (A3): a valid persisted token
// restores the session, while a stale/revoked token (HTTP 401 from
// /api/auth/me) clears the persisted session and falls back to silent
// anonymous browsing — no login-screen trap, no splash hang. Uses a fake API +
// an in-memory Drift DB — no network, no widgets.

import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:malt_radar/core/api/auth_api.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/auth/data/auth_repository.dart';
import 'package:malt_radar/features/auth/domain/auth_user.dart';
import 'package:malt_radar/features/auth/presentation/auth_controller.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

/// Fake [AuthApi] that scripts the `/api/auth/me` call made during restore:
/// return a valid user (session kept) or throw a 401 [AuthApiException]
/// (stale token) / a statusCode-less [AuthApiException] (offline blip).
class RestoreFakeAuthApi extends AuthApi {
  final Object? meError;
  final Map<String, dynamic>? meUser;
  int meCallCount = 0;

  RestoreFakeAuthApi({this.meError, this.meUser});

  @override
  Future<Map<String, dynamic>> me(String token) async {
    meCallCount++;
    if (meError != null) throw meError!;
    return meUser ?? _user();
  }

  static Map<String, dynamic> _user() => {
        'id': 1,
        'email': 'user@example.com',
        'display_name': null,
        'email_verified': 1,
        'privacy_consent': 1,
        'age_country': 'TR',
        'age_min': 18,
        'created_at': '2026-08-06T00:00:00+00:00',
      };
}

const _seededUser = AuthUser(id: 1, email: 'user@example.com');

/// Persist a session (token + user) before the controller is created, so the
/// restore path actually finds a token to validate.
Future<void> seedSession(AppDatabase db, {String token = 'stale-token'}) async {
  await AuthRepository(db).saveSession(token, _seededUser);
}

Future<ProviderContainer> buildContainer(AppDatabase db, AuthApi api) async {
  final container = ProviderContainer(
    overrides: [
      appDatabaseProvider.overrideWithValue(db),
      authApiProvider.overrideWithValue(api),
    ],
  );
  addTearDown(container.dispose);
  // Create the controller (triggers async _restore()) and let it settle.
  container.read(authControllerProvider);
  await pumpEventQueue();
  return container;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('restore with valid token keeps session', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());
    await seedSession(db);

    final api = RestoreFakeAuthApi();
    final container = await buildContainer(db, api);

    final state = container.read(authControllerProvider);
    expect(state.status, AuthStatus.loggedIn);
    expect(state.isLoggedIn, isTrue);
    expect(state.user?.email, 'user@example.com');
    expect(api.meCallCount, 1, reason: 'token validated against /api/auth/me');

    // Session retained, not cleared.
    final repo = container.read(authRepositoryProvider);
    expect(await repo.loadToken(), 'stale-token');
    expect((await repo.loadUser())?.email, 'user@example.com');

    // Not pushed into guest mode.
    expect(container.read(guestModeProvider), isFalse);
  });

  test('restore with stale token (401) clears session, anonymous fallback',
      () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());
    await seedSession(db);

    final api = RestoreFakeAuthApi(
      meError: AuthApiException('Token expired', statusCode: 401),
    );
    final container = await buildContainer(db, api);

    final state = container.read(authControllerProvider);
    // "Anonymous" == AuthStatus.loggedOut: the enum has no separate
    // anonymous value; guest mode carries the anonymous content flow.
    expect(state.status, AuthStatus.loggedOut);
    expect(state.isLoggedIn, isFalse);

    // Session cleared from persistence.
    final repo = container.read(authRepositoryProvider);
    expect(await repo.loadToken(), isNull);
    expect(await repo.loadUser(), isNull);

    // Silent anonymous fallback: guest mode flipped so the user lands on the
    // anonymous catalog, not trapped on the login screen.
    expect(container.read(guestModeProvider), isTrue);
  });

  test('restore with offline failure keeps cached session (no logout)', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(() => db.close());
    await seedSession(db);

    // Connectivity failure surfaces as AuthApiException WITHOUT a status code.
    final api = RestoreFakeAuthApi(
      meError: AuthApiException('Sunucuya bağlanılamadı.'),
    );
    final container = await buildContainer(db, api);

    final state = container.read(authControllerProvider);
    // A temporary network blip must never log the user out.
    expect(state.status, AuthStatus.loggedIn);
    expect(state.user?.email, 'user@example.com');

    final repo = container.read(authRepositoryProvider);
    expect(await repo.loadToken(), 'stale-token');
    expect(container.read(guestModeProvider), isFalse);
  });
}
