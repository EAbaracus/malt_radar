import 'package:flutter/material.dart';

/// Non-web stub for [GoogleSignInWebButton].
///
/// The real implementation (web only) lives in `google_sign_in_web_button_web.dart`
/// and is selected via the conditional export in `google_sign_in_web_button.dart`.
/// Because [AuthScreen] only instantiates the web button behind a `kIsWeb` guard,
/// this stub is never built off-web. Throwing in `build` is a fail-fast backstop
/// in case it is ever instantiated on the wrong platform.
class GoogleSignInWebButton extends StatelessWidget {
  const GoogleSignInWebButton({super.key});

  @override
  Widget build(BuildContext context) =>
      throw UnsupportedError('GoogleSignInWebButton is only available on web');
}
