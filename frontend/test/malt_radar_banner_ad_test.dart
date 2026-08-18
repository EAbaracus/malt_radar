import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:malt_radar/features/ads/ads_config.dart';
import 'package:malt_radar/features/ads/widgets/malt_radar_banner_ad.dart';

void main() {
  group('AdsConfig', () {
    test('effectiveBannerUnitId falls back to production id when override empty', () {
      expect(AdsConfig.effectiveBannerUnitId, AdsConfig.productionBannerUnitId);
    });

    test('platformEnabled is true only on Android non-web', () {
      expect(AdsConfig.platformEnabled, !kIsWeb && defaultTargetPlatform == TargetPlatform.android);
    });
  });

  group('MaltRadarBannerAd', () {
    // Ads are Android-only by design. On the test VM (not Android),
    // platformEnabled is false, so the widget renders nothing without
    // constructing a real BannerAd — this is the fail-safe path we cover.
    testWidgets('renders nothing when ads disabled', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: MaltRadarBannerAd(enabled: false)),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(SizedBox), findsOneWidget);
    });
  });
}
