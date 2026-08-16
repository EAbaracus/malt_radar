/// Platform-aware facade for the Consent Mode v2 JS bridge.
///
/// On web (`dart.library.html`) this exports the real implementation that calls
/// `window.updateGoogleConsent` ([consent_bridge_web.dart]); everywhere else
/// (mobile, desktop, and the unit-test VM) it exports an inert no-op stub
/// ([consent_bridge_stub.dart]). This mirrors the conditional-export pattern
/// used by `google_sign_in_web_button.dart` so the `dart:js_interop` import
/// never loads on non-web builds.
library;

export 'consent_bridge_stub.dart'
    if (dart.library.html) 'consent_bridge_web.dart';
