import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:malt_radar/features/ads/ads_config.dart';

/// Lazily initializes AdMob only when age gate consent has been given and
/// the platform supports ads. Must never be called before user consent —
/// doing so on Android can trigger a play-services crash. On non-ad platforms
/// it is a safe no-op (MobileAds initializes to a default context).
final _adsInitGuard = _AdsInitGuard();

void initAdMobIfAllowed() {
  if (!AdsConfig.platformEnabled) return;
  _adsInitGuard.init();
}

class _AdsInitGuard {
  bool _initialized = false;
  Future<void>? _initFuture;

  void init() {
    if (_initialized || _initFuture != null) return;
    _initFuture = _doInit().then((_) => _initialized = true);
  }

  Future<void> _doInit() async {
    try {
      await MobileAds.instance.initialize();
    } catch (_) {
      // Ads SDK failure must never crash app startup. Silent fail.
    }
  }
}
