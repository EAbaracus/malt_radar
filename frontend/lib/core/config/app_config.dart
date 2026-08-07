import 'package:flutter/foundation.dart';

class AppConfig {
  static const bool useDbApiConst =
      bool.fromEnvironment('MALT_RADAR_USE_DB_API', defaultValue: false);

  /// Feature flag to switch between the local Drift/legacy-CSV repository and
  /// the certified-staging backend (DbApi mode).
  ///
  /// When true, the entire app data path is:
  ///   Flutter -> DbWhiskyRepositoryImpl -> FastAPI -> SQLite (staging)
  /// and the backend is the single source of truth. When false, the local
  /// Drift database (offline / legacy CSV / fallback) is used.
  ///
  /// The web target is ALWAYS backend-driven: forbidding the bundled catalog
  /// CSV from being pulled on web keeps the whisky data server-side (a core
  /// part of the anti-scrape posture — the CSV is not meant to ship to web
  /// clients at all). Local CSV mode remains for desktop/mobile fleet / offline.
  static bool get useDbApi => kIsWeb ? true : useDbApiConst;

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
