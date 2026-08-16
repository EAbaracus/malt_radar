import 'dart:js_interop';

/// Web implementation of [ConsentBridge].
///
/// Invokes `window.updateGoogleConsent(analyticsGranted, marketingGranted)`,
/// the Consent Mode v2 helper injected by `web/index.html` (and the built
/// `deploy/web-build/index.html`). The helper maps the two booleans onto
/// `analytics_storage` and `ad_storage` / `ad_user_data` / `ad_personalization`
/// and pushes a `gtag('consent', 'update', …)` call.
class ConsentBridge {
  const ConsentBridge();

  bool updateGoogleConsent({
    required bool analyticsGranted,
    required bool marketingGranted,
  }) {
    try {
      _updateGoogleConsent(analyticsGranted, marketingGranted);
      return true;
    } catch (_) {
      // Helper absent (e.g. an index.html without the bootstrap). Fail-closed.
      return false;
    }
  }
}

/// Bound to the global `window.updateGoogleConsent` defined in `web/index.html`.
@JS('updateGoogleConsent')
external void _updateGoogleConsent(bool analyticsGranted, bool marketingGranted);
