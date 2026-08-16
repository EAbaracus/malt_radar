import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'consent_bridge.dart';
import 'consent_state.dart';

/// Injectable seam for the Consent Mode v2 JS bridge. Overridden in tests with
/// a recording fake so the payload handed to `window.updateGoogleConsent` can be
/// asserted without a browser.
final consentBridgeProvider = Provider<ConsentBridge>((ref) {
  return const ConsentBridge();
});

/// Single source of truth for the CMP decision.
///
/// Persists the decision to the local Drift `UserSettings` store (key `'consent'`,
/// the same pattern as the age gate and language) so the banner does not
/// reappear on every launch, and forwards the decision to the Consent Mode v2
/// bootstrap via [ConsentBridge.updateGoogleConsent].
///
/// G6 boundary: this records consent *state only*. It never dispatches live
/// telemetry and never touches a GA4 measurement id.
class ConsentController extends StateNotifier<ConsentState> {
  final AppDatabase _db;
  final ConsentBridge _bridge;
  static const _key = 'consent';

  ConsentController(this._db, this._bridge) : super(ConsentState.undecided) {
    _load();
  }

  Future<void> _load() async {
    final row = await (_db.select(_db.userSettings)
          ..where((t) => t.key.equals(_key)))
        .getSingleOrNull();
    if (row == null) return;
    state = ConsentState.decode(row.value);
  }

  /// Banner "Accept all": analytics + marketing granted.
  Future<void> acceptAll() => _decide(
        analytics: ConsentChoice.granted,
        marketing: ConsentChoice.granted,
      );

  /// Banner "Reject all": analytics + marketing denied.
  Future<void> denyAll() => _decide(
        analytics: ConsentChoice.denied,
        marketing: ConsentChoice.denied,
      );

  /// Preferences dialog granular save.
  Future<void> savePreferences({
    required ConsentChoice analytics,
    required ConsentChoice marketing,
  }) =>
      _decide(analytics: analytics, marketing: marketing);

  Future<void> _decide({
    required ConsentChoice analytics,
    required ConsentChoice marketing,
  }) async {
    final next = ConsentState(analytics: analytics, marketing: marketing);
    // Update UI state first, then notify the JS bootstrap (synchronous), then
    // persist. Persistence is best-effort; the in-memory decision is canonical
    // for the rest of this session.
    state = next;
    _bridge.updateGoogleConsent(
      analyticsGranted: next.isAnalyticsGranted,
      marketingGranted: next.isMarketingGranted,
    );
    await _db.into(_db.userSettings).insertOnConflictUpdate(
          UserSettingsCompanion.insert(key: _key, value: next.encode()),
        );
  }
}

final consentControllerProvider =
    StateNotifierProvider<ConsentController, ConsentState>((ref) {
  final db = ref.watch(appDatabaseProvider);
  final bridge = ref.watch(consentBridgeProvider);
  return ConsentController(db, bridge);
});
