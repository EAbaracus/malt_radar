import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/analytics/ga4_consent_interop_stub.dart';

void main() {
  test('stub syncGoogleConsent never throws off-web', () {
    // On the VM the stub is selected; the call must be a safe no-op for
    // both grant and deny, with and without the named secondary flag.
    expect(() => syncGoogleConsent(true), returnsNormally);
    expect(() => syncGoogleConsent(false), returnsNormally);
    expect(() => syncGoogleConsent(true, secondary: true), returnsNormally);
  });
}
