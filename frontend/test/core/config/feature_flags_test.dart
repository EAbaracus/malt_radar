import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/config/feature_flags.dart';

void main() {
  test('FeatureFlags.enableGoogleSignIn defaults to false', () {
    expect(FeatureFlags.enableGoogleSignIn, isFalse);
  });
}
