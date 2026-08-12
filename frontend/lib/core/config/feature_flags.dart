abstract class FeatureFlags {
  /// Controls whether Google Sign-In UI and script injection are active.
  /// Defaults to `false` in production unless explicitly enabled via
  /// `--dart-define=ENABLE_GOOGLE_SIGN_IN=true`.
  static const bool enableGoogleSignIn =
      bool.fromEnvironment('ENABLE_GOOGLE_SIGN_IN', defaultValue: false);
}
