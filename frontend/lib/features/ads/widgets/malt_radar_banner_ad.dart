import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:malt_radar/features/ads/ads_config.dart';

/// Banner AdMob ad widget, consent-gated and fail-safe.
///
/// - When [enabled] is false (default: driven by [AdsConfig.platformEnabled]),
///   renders nothing — no crash on non-Android platforms.
/// - Uses the production unit id from [AdsConfig] by default; override via
///   `--dart-define=ADMOB_BANNER_ID=…` (test/canary unit).
/// - Catches banner load errors and renders nothing rather than crashing,
///   per UX spec: ads must never block catalog reading.
class MaltRadarBannerAd extends StatefulWidget {
  const MaltRadarBannerAd({
    super.key,
    this.enabled,
    this.size = AdSize.banner,
  });

  final bool? enabled;
  final AdSize size;

  @override
  State<MaltRadarBannerAd> createState() => _MaltRadarBannerAdState();
}

class _MaltRadarBannerAdState extends State<MaltRadarBannerAd> {
  BannerAd? _bannerAd;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _initBanner();
  }

  void _initBanner() {
    final adsEnabled = widget.enabled ?? AdsConfig.platformEnabled;
    if (!adsEnabled) return;
    _bannerAd = BannerAd(
      size: widget.size,
      adUnitId: AdsConfig.effectiveBannerUnitId,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) => setState(() => _loaded = true),
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          setState(() => _loaded = false);
        },
      ),
    );
    _bannerAd!.load();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final adsEnabled = widget.enabled ?? AdsConfig.platformEnabled;
    if (!adsEnabled || !_loaded || _bannerAd == null) {
      return const SizedBox.shrink();
    }
    return SizedBox(
      width: widget.size.width.toDouble(),
      height: widget.size.height.toDouble(),
      child: AdWidget(ad: _bannerAd!),
    );
  }
}
