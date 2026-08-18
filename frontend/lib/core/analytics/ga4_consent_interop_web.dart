// Web-only GA4 consent interop.
//
// Selected by the conditional import when building for the web
// (`dart.library.js` is available there). Bridges app consent decisions to
// the global `updateGoogleConsent(granted, secondary)` function defined by
// the GA4 Consent Mode v2 snippet.
//
// dart:js (not dart:js_interop) is used deliberately to mirror the prior
// implementation and keep behavior identical on the web target.
// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:js' as js;

void syncGoogleConsent(bool granted, {bool secondary = false}) {
  if (js.context['updateGoogleConsent'] == null) return;
  try {
    js.context.callMethod('updateGoogleConsent', [granted, secondary]);
  } catch (_) {
    // GA4 consent update failed — non-critical, continue.
  }
}
