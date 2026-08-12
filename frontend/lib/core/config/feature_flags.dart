import 'package:flutter_riverpod/flutter_riverpod.dart';

abstract class FeatureFlags {
  /// Controls whether Google Sign-In UI and script injection are active.
  /// Defaults to `false` in production unless explicitly enabled via
  /// `--dart-define=ENABLE_GOOGLE_SIGN_IN=true`.
  static const bool enableGoogleSignIn =
      bool.fromEnvironment('ENABLE_GOOGLE_SIGN_IN', defaultValue: false);
}

/// Riverpod view over [FeatureFlags.enableGoogleSignIn].
///
/// Exists so widget tests can override the compile-time flag per-test
/// (`googleSignInEnabledProvider.overrideWithValue(true)`) without
/// recompiling; production behavior is always the const flag.
final googleSignInEnabledProvider = Provider<bool>((ref) {
  return FeatureFlags.enableGoogleSignIn;
});
