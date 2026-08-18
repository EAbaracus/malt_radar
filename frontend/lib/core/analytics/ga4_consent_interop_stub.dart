/// Non-web GA4 consent interop stub.
///
/// On Android/iOS/desktop the web-only `dart:js` library does not exist, so
/// this stub is selected by the conditional import
/// (`if (dart.library.js)`). GA4 consent on native is handled by the native
/// analytics path; this call is an intentional no-op and must never throw.
void syncGoogleConsent(bool granted, {bool secondary = false}) {
  // Intentionally empty on non-web platforms.
}
