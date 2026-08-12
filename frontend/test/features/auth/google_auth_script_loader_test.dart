import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/features/auth/data/google_auth_script_loader.dart';

void main() {
  test('GoogleAuthScriptLoader returns false when feature flag is disabled', () async {
    final ok = await GoogleAuthScriptLoader.instance.loadScript();
    expect(ok, isFalse);
  });
}
