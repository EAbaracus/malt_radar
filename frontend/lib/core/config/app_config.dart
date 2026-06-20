class AppConfig {
  /// Feature flag to switch between legacy API and the new DB API backend.
  /// Default is false to preserve existing app behavior.
  static const bool useDbApi = false;

  /// Feature flag for ScotchGit QA preview mode.
  /// If true, preview profiles (e.g. scotchgit) are considered in the UI.
  /// Should be false in production/release mode.
  static const bool enableFlavorPreviewMode = false;
}
