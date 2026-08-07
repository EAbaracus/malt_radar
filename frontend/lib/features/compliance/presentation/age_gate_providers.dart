import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import '../domain/legal_age.dart';

/// Lifecycle of the compliance age gate.
enum AgeGateStatus { unknown, notConsented, consented, blocked }

/// Result of evaluating the persisted age-gate (if any).
@immutable
class AgeGateDecision {
  final AgeGateStatus status;
  final String? country;
  final int? minAge;

  const AgeGateDecision(this.status, {this.country, this.minAge});

  /// True when the user has successfully passed the gate and may use the app.
  bool get isAllowed => status == AgeGateStatus.consented && minAge != null;
}

/// Persists the age-gate answer in the local Drift `UserSettings` key-value
/// store (no new dependency, survives restart). Value encoding:
///   - `blocked`          → user declared underage (app locked)
///   - `<CC>|<minAge>`    → consented, e.g. `TR|18`
class AgeGateNotifier extends StateNotifier<AgeGateDecision> {
  final AppDatabase db;
  static const _key = 'age_gate';
  static const _blockedValue = 'blocked';

  AgeGateNotifier(this.db)
    : super(const AgeGateDecision(AgeGateStatus.unknown)) {
    _load();
  }

  Future<void> _load() async {
    final row = await (db.select(
      db.userSettings,
    )..where((t) => t.key.equals(_key))).getSingleOrNull();
    if (row == null) {
      state = const AgeGateDecision(AgeGateStatus.notConsented);
      return;
    }
    if (row.value == _blockedValue) {
      state = const AgeGateDecision(AgeGateStatus.blocked);
      return;
    }
    final parts = row.value.split('|');
    final country = parts.isNotEmpty ? parts[0] : null;
    final minAge = parts.length > 1 ? int.tryParse(parts[1]) : null;
    state = AgeGateDecision(
      minAge != null ? AgeGateStatus.consented : AgeGateStatus.notConsented,
      country: country,
      minAge: minAge,
    );
  }

  /// Records an affirmative age confirmation for [countryCode].
  Future<void> consent(String countryCode) async {
    final minAge = legalAgeFor(countryCode);
    await db
        .into(db.userSettings)
        .insertOnConflictUpdate(
          UserSettingsCompanion.insert(
            key: _key,
            value: '$countryCode|$minAge',
          ),
        );
    state = AgeGateDecision(
      AgeGateStatus.consented,
      country: countryCode,
      minAge: minAge,
    );
  }

  /// Records an underage declaration (app becomes locked).
  Future<void> block() async {
    await db
        .into(db.userSettings)
        .insertOnConflictUpdate(
          UserSettingsCompanion.insert(key: _key, value: _blockedValue),
        );
    state = const AgeGateDecision(AgeGateStatus.blocked);
  }

  /// Clears the stored decision so the user is asked to re-verify on the next
  /// launch.
  Future<void> reset() async {
    await (db.delete(db.userSettings)..where((t) => t.key.equals(_key))).go();
    state = const AgeGateDecision(AgeGateStatus.notConsented);
  }
}

final ageGateProvider = StateNotifierProvider<AgeGateNotifier, AgeGateDecision>(
  (ref) {
    final db = ref.watch(appDatabaseProvider);
    return AgeGateNotifier(db);
  },
);
