import 'package:flutter/foundation.dart';

/// Central AdMob configuration.
///
/// The AdMob application / ad-unit ids are NOT secrets — they are embedded in
/// every compiled client by necessity (the SDK must know them at runtime), so
/// committing the production ids here is safe.
///
/// - `adUnitBannerId` : optional build-time override via
///   `--dart-define=ADMOB_BANNER_ID=…` (e.g. a different test/canary unit).
/// - `productionBannerUnitId` : the real banner unit used by default.
/// - Ads render on Android only; other platforms show nothing.
class AdsConfig {
  AdsConfig._();

  /// Optional override injected at build time. Empty in dev/tests.
  static const String adUnitBannerId = String.fromEnvironment(
    'ADMOB_BANNER_ID',
  );

  /// Real production banner unit (this app).
  static const String productionBannerUnitId =
      'ca-app-pub-4569028808710145/4150292677';

  /// Test banner unit (Google's) for safe dev toggling.
  static const String testBannerUnitId =
      'ca-app-pub-3940256099942544/6300978111';

  /// Effective unit: explicit override if set, else the production id.
  static String get effectiveBannerUnitId =>
      adUnitBannerId.isNotEmpty ? adUnitBannerId : productionBannerUnitId;

  /// The app has a real monetization id configured (this app always does).
  static bool get hasAdUnit => true;

  /// Ads render on Android only (web/desktop/iOS: no ads in this product).
  static bool get platformEnabled =>
      !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
}
