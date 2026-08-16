/// Non-web implementation of [ConsentBridge].
///
/// On mobile/desktop and in the unit-test VM there is no `window` and no
/// Consent Mode v2 JS bootstrap, so the bridge is a safe no-op that reports the
/// helper as unavailable. [CmpBanner]/[CmpPreferencesDialog] are never shown on
/// non-web builds, but the controller must still be constructible everywhere.
class ConsentBridge {
  const ConsentBridge();

  /// No-op on non-web platforms; returns false (helper absent).
  bool updateGoogleConsent({
    required bool analyticsGranted,
    required bool marketingGranted,
  }) {
    return false;
  }
}
