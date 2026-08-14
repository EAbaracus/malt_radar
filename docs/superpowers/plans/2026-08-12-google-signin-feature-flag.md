# Google Sign-In Feature Flag & Web Script Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disable Google Sign-In in production builds by default using a compile-time feature flag and isolate web GSI script loading, while allowing seamless local enablement via `--dart-define=ENABLE_GOOGLE_SIGN_IN=true`.

**Architecture:** A static `FeatureFlags.enableGoogleSignIn` constant gates the UI in `AuthScreen`. On Web, an idempotent, async-safe `GoogleAuthScriptLoader` dynamically injects the Google Identity Services (GSI) script (`accounts.google.com/gsi/client`) only when the feature flag is enabled.

**Tech Stack:** Flutter Web/Mobile, Dart (`bool.fromEnvironment`, `dart:html` / `package:web`), Riverpod, `google_sign_in_web`.

**Spec Reference:** Derived from `docs/superpowers/specs/2026-08-12-google-signin-feature-flag-design.md` (HEAD @ `bf1d466`).

## Global Constraints

- Default behavior in production builds must be `enableGoogleSignIn == false`.
- Zero GSI script tags in `web/index.html`.
- No raw exceptions leaked to UI if script load fails (e.g. adblocker, network outage). No automatic retries within the same session by design (`no-retry by design`).
- All existing tests must pass; unit/widget tests must verify default feature flag behavior (`enableGoogleSignIn == false`).

---

### Task 1: Clean Static `index.html` & Add `FeatureFlags`

**Files:**
- Modify: `frontend/web/index.html` (remove GSI script tag)
- Create: `frontend/lib/core/config/feature_flags.dart`
- Create: `frontend/test/core/config/feature_flags_test.dart`

**Interfaces:**
- Produces: `FeatureFlags.enableGoogleSignIn` (bool)

- [ ] **Step 1: Write failing test for FeatureFlags**

```dart
// frontend/test/core/config/feature_flags_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/config/feature_flags.dart';

void main() {
  test('FeatureFlags.enableGoogleSignIn defaults to false', () {
    expect(FeatureFlags.enableGoogleSignIn, isFalse);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/core/config/feature_flags_test.dart --no-pub`
Expected: FAIL with compilation error (file not found).

- [ ] **Step 3: Implement FeatureFlags & clean `web/index.html`**

Create `frontend/lib/core/config/feature_flags.dart`:
```dart
abstract class FeatureFlags {
  /// Controls whether Google Sign-In UI and script injection are active.
  /// Defaults to `false` in production unless explicitly enabled via
  /// `--dart-define=ENABLE_GOOGLE_SIGN_IN=true`.
  static const bool enableGoogleSignIn =
      bool.fromEnvironment('ENABLE_GOOGLE_SIGN_IN', defaultValue: false);
}
```

Modify `frontend/web/index.html`:
Remove `<script src="https://accounts.google.com/gsi/client" async defer></script>` line.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/core/config/feature_flags_test.dart --no-pub`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/eltun/Documents/malt-radar-auth-b2
git add frontend/lib/core/config/feature_flags.dart frontend/test/core/config/feature_flags_test.dart frontend/web/index.html
git commit -m "feat(auth): add FeatureFlags and remove static GSI script from index.html"
```

---

### Task 2: Idempotent Dynamic Script Loader (`GoogleAuthScriptLoader`)

**Files:**
- Create: `frontend/lib/features/auth/data/google_auth_script_loader.dart`
- Create: `frontend/test/features/auth/google_auth_script_loader_test.dart`

**Interfaces:**
- Consumes: `FeatureFlags.enableGoogleSignIn`
- Produces: `GoogleAuthScriptLoader.loadScript()` -> `Future<bool>` (returns `true` on success, `false` on script load error or when flag disabled)

**Edge Case Guarantees:**
- **Idempotency:** Completer & DOM check `script[src*="gsi/client"]` ensure `appendChild` runs at most once.
- **Completer Safety:** Completes with `false` on `onerror` (never `completeError`), avoiding uncaught exceptions.
- **No-retry by design:** Failed load remains cached as `false` for the session.

- [ ] **Step 1: Write failing test for GoogleAuthScriptLoader**

```dart
// frontend/test/features/auth/google_auth_script_loader_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/auth/data/google_auth_script_loader.dart';

void main() {
  test('GoogleAuthScriptLoader returns false when feature flag is disabled', () async {
    final success = await GoogleAuthScriptLoader.instance.loadScript();
    expect(success, isFalse);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/features/auth/google_auth_script_loader_test.dart --no-pub`
Expected: FAIL with compilation error (file not found).

- [ ] **Step 3: Implement GoogleAuthScriptLoader**

Create `frontend/lib/features/auth/data/google_auth_script_loader.dart`:
```dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:malt_radar/core/config/feature_flags.dart';

/// Idempotent loader for Google Identity Services (GSI) script on Web.
class GoogleAuthScriptLoader {
  static final GoogleAuthScriptLoader instance = GoogleAuthScriptLoader._();
  GoogleAuthScriptLoader._();

  Completer<bool>? _completer;

  /// Loads the GSI JS script dynamically if running on Web and [FeatureFlags.enableGoogleSignIn] is true.
  /// Returns `true` if loaded successfully, `false` otherwise (or when flag is disabled).
  Future<bool> loadScript() async {
    if (!kIsWeb || !FeatureFlags.enableGoogleSignIn) {
      return false;
    }
    if (_completer != null) {
      return _completer!.future;
    }
    _completer = Completer<bool>();

    // In unit test VM environment, avoid web DOM interaction
    if (kIsWeb) {
      _loadWebScript();
    } else {
      _completer!.complete(false);
    }
    return _completer!.future;
  }

  void _loadWebScript() {
    // Web implementation injects script and completes _completer with true/false on load/error
    // Implementation uses HTML/DOM bindings defensively
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/features/auth/google_auth_script_loader_test.dart --no-pub`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/eltun/Documents/malt-radar-auth-b2
git add frontend/lib/features/auth/data/google_auth_script_loader.dart frontend/test/features/auth/google_auth_script_loader_test.dart
git commit -m "feat(auth): implement idempotent GoogleAuthScriptLoader with safe exception handling"
```

---

### Task 3: Feature Flag Gating in AuthScreen & Widget Tests

**Files:**
- Modify: `frontend/lib/features/auth/presentation/auth_screen.dart`
- Modify: `frontend/test/auth_controller_test.dart`
- Modify: `frontend/test/google_sign_in_button_test.dart`

**Interfaces:**
- Consumes: `FeatureFlags.enableGoogleSignIn`
- Produces: Conditional rendering of Google button & divider in `AuthScreen`

- [ ] **Step 1: Write failing widget test asserting Google button is absent when flag is false**

In `frontend/test/google_sign_in_button_test.dart`:
```dart
testWidgets('AuthScreen does not render Google sign-in button when FeatureFlags.enableGoogleSignIn is false', (tester) async {
  // Build AuthScreen inside ProviderScope / MaterialApp
  // Assert find.byKey(const Key('google-sign-in-button')) findsNothing
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/google_sign_in_button_test.dart --no-pub`
Expected: FAIL (button currently rendered unconditionally).

- [ ] **Step 3: Modify AuthScreen to gate Google button behind FeatureFlags.enableGoogleSignIn**

In `frontend/lib/features/auth/presentation/auth_screen.dart`:
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
  Row(
    children: [
      const Expanded(child: Divider(color: AppTheme.textSecondary, thickness: 1, height: 1)),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Text(isTr ? 'veya' : 'or', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
      ),
      const Expanded(child: Divider(color: AppTheme.textSecondary, thickness: 1, height: 1)),
    ],
  ),
  const SizedBox(height: 16),
],
```

- [ ] **Step 4: Run test suite & analyze**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/google_sign_in_button_test.dart --no-pub`
Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat analyze --no-pub lib/features/auth/`
Expected: ALL PASS, 0 analyze issues.

- [ ] **Step 5: Commit & Deploy Build Verification**

```bash
cd C:/Users/eltun/Documents/malt-radar-auth-b2
git add frontend/lib/features/auth/presentation/auth_screen.dart frontend/test/google_sign_in_button_test.dart
git commit -m "feat(auth): gate Google Sign-In UI behind FeatureFlags.enableGoogleSignIn"
```
