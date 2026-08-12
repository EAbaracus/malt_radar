# Design Spec: Google Sign-In Feature Flag & Web Script Isolation

**Date:** 2026-08-12  
**Status:** Approved  
**Scope:** Frontend Google Sign-In Feature Flag & Dynamic Web Script Isolation

---

## 1. Goal & Context

Google Sign-In integration on Flutter Web currently causes render/GSI loading freezes ("Getting ready" screen hang) in production. The objective is to **disable Google Sign-In in production by default** via a compile-time feature flag, cleanly removing the UI and web script overhead, while providing a clean isolation path for local development and testing.

---

## 2. Architecture & Components

### 2.1 Feature Flag Configuration (`lib/core/config/feature_flags.dart`)
Compile-time flag backed by `bool.fromEnvironment`, defaulting to `false` in production builds unless explicitly overridden at build time.

```dart
class FeatureFlags {
  /// Controls whether Google Sign-In UI, script injection, and authentication flows are active.
  /// Defaults to `false` in production. Enable locally via:
  /// `--dart-define=ENABLE_GOOGLE_SIGN_IN=true`
  static const bool enableGoogleSignIn =
      bool.fromEnvironment('ENABLE_GOOGLE_SIGN_IN', defaultValue: false);
}
```

---

### 2.2 Dynamic Web Script Injection & Lifecycle (`GoogleAuthScriptLoader`)
Instead of an unconditional `<script src="https://accounts.google.com/gsi/client">` tag in `index.html`, script injection is handled programmatically with strict idempotency and async error handling.

#### Design Principles:
1. **Idempotency & Deduplication:** Managed via a singleton `GoogleAuthScriptLoader` with a `Completer<void>` and DOM query check (`script[src*="gsi/client"]`). Repeated calls return the exact same in-flight or completed `Future`.
2. **Async Load / Error Handling:** Listens to `onload` and `onerror` JS script events. If blocked by adblockers, network loss, or Google outage:
   - `onload` -> Completes successfully.
   - `onerror` -> Completes with error / catches gracefully.
   - Fallback -> If script fails to load, `GoogleSignInWebButton` silently hides itself or falls back safely, ensuring the user's primary Email/Password login flow remains 100% operational.

---

### 2.3 UI Integration (`AuthScreen`)
In `AuthScreen`, the Google Sign-In button and the visual `"or"` (`veya`) divider row are conditionally rendered **only** when `FeatureFlags.enableGoogleSignIn` is `true`.

```dart
if (FeatureFlags.enableGoogleSignIn) ...[
  if (kIsWeb)
    const GoogleSignInWebButton()
  else
    GoogleSignInButton(
      label: isTr ? 'Google ile devam et' : 'Continue with Google',
      isLoading: _googleBusy,
      onPressed: _signInWithGoogle,
    ),
  const SizedBox(height: 16),
  Row(children: [...]), // Divider row ("veya" / "or")
  const SizedBox(height: 16),
],
```

When `FeatureFlags.enableGoogleSignIn` is `false`:
- Zero GSI network requests.
- Zero "Getting ready" / GSI script loading overhead.
- Clean, direct Email/Password authentication form.

---

## 3. Build & Operational Commands

### Production Build (Default - Google Sign-In Disabled)
```bash
flutter build web --release \
  --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com
```

### Local Development / Debugging (Google Sign-In Enabled)
```bash
flutter run -d chrome \
  --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com \
  --dart-define=ENABLE_GOOGLE_SIGN_IN=true \
  --dart-define=GOOGLE_CLIENT_ID_WEB=655891240518-c3ku52gk6qfd7ar08e1o3ntolqh2vql0.apps.googleusercontent.com
```

---

## 4. Verification & Testing Strategy

1. **Unit & Widget Tests:** Update existing widget tests (`auth_screen_test.dart`, `google_sign_in_button_test.dart`) to verify that when `ENABLE_GOOGLE_SIGN_IN` is `false` (default), no Google button or divider is present in the widget tree.
2. **Web Script Verification:** Verify that `index.html` does not contain any hardcoded `gsi/client` script tag.
3. **Local Ad-hoc Verification:** Verify `--dart-define=ENABLE_GOOGLE_SIGN_IN=true` correctly renders the button and attempts script loading in local dev mode.
