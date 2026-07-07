import 'package:flutter/foundation.dart';

class AppConfig {
  /// Feature flag to switch between legacy API and the new DB API backend.
  /// Default is false to preserve existing app behavior.
  static const bool useDbApi = false;

  /// Feature flag for ScotchGit QA preview mode.
  /// If true, preview profiles (e.g. scotchgit) are considered in the UI.
  /// Should be false in production/release mode.
  static const bool enableFlavorPreviewMode = false;

  /// Feature flag to filter out invalid, all-zero, or legacy low-signal flavor profiles.
  /// Default is true to maintain UI integrity (Radar Chart, Similarity).
  static const bool useFlavorQualityFilter = true;

  /// Feature flag to control visibility of whisky pricing data in UI and calculations.
  /// Default is false to hide pricing information in release/live environments.
  static const bool showPriceData = false;


  /// Retrieves the base URL depending on the environment and build mode.
  static String get baseUrl {
    const envUrl = String.fromEnvironment('MALT_RADAR_API_BASE_URL');
    
    if (kReleaseMode) {
      if (envUrl.isEmpty) {
        throw StateError('MALT_RADAR_API_BASE_URL environment variable is required in release mode.');
      }
      if (envUrl.startsWith('http://')) {
        throw StateError('Cleartext HTTP is not allowed in release mode. Please use HTTPS.');
      }
      return envUrl;
    }
    
    // Debug mode fallback
    if (envUrl.isNotEmpty) {
      return envUrl;
    }
    
    if (kIsWeb) return 'http://localhost:8080';
    try {
      if (defaultTargetPlatform == TargetPlatform.android) {
        return 'http://10.0.2.2:8080';
      }
    } catch (_) {}
    return 'http://localhost:8080';
  }
}
