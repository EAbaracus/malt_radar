class AppConfig {
  /// Feature flag to switch between legacy API and the new DB API backend.
  /// Default is false to preserve existing app behavior.
  static const bool useDbApi = false;
}
