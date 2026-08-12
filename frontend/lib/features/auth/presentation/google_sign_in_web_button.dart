/// Platform-aware facade for the web Google sign-in button.
///
/// On web (`dart.library.html`) this exports the real GSI `renderButton`-backed
/// widget ([google_sign_in_web_button_web.dart]); on every other platform it
/// exports an inert stub ([google_sign_in_web_button_stub.dart]) that throws if
/// built. [AuthScreen] only ever instantiates [GoogleSignInWebButton] behind a
/// `kIsWeb` guard, so the stub is never built off-web — and the
/// `package:google_sign_in_web` / `package:web` imports never load on mobile or
/// in the unit-test VM (which runs non-web).
export 'google_sign_in_web_button_stub.dart'
    if (dart.library.html) 'google_sign_in_web_button_web.dart';
