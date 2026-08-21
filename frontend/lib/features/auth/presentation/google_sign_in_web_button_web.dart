import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:google_sign_in_web/web_only.dart' as gsi_web;

import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'auth_controller.dart';
import 'google_sign_in_messages.dart';
import '../data/google_auth_script_loader.dart';

/// Web-only official Google sign-in button backed by the GSI `renderButton`
/// widget.
///
/// Unlike the mobile path (which drives a programmatic `authenticate()` flow
/// from our own styled button), on web we render Google's native button. The
/// GSI library delivers the resulting credential to
/// [GoogleSignIn.instance.authenticationEvents]; this widget listens for the
/// sign-in event, extracts the id token, and forwards it to
/// [AuthController.signInWithGoogleFromCredential] for the backend exchange.
///
/// Only ever instantiated behind a `kIsWeb` guard in [AuthScreen] — the
/// underlying platform view exists only on web.
class GoogleSignInWebButton extends ConsumerStatefulWidget {
  const GoogleSignInWebButton({super.key, this.configuration});

  /// Optional GSI button styling. `null` uses Google's default button.
  final gsi_web.GSIButtonConfiguration? configuration;

  @override
  ConsumerState<GoogleSignInWebButton> createState() =>
      _GoogleSignInWebButtonState();
}

class _GoogleSignInWebButtonState extends ConsumerState<GoogleSignInWebButton> {
  StreamSubscription<GoogleSignInAuthenticationEvent>? _sub;
  bool _busy = false;
  bool _gsiReady = false;

  @override
  void initState() {
    super.initState();
    _init();
    _sub = GoogleSignIn.instance.authenticationEvents.listen(
      _onSignIn,
      onError: _onError,
    );
  }

  /// Ensures the Google Identity Services client is initialized (which also
  /// loads the GSI script on web) before [gsi_web.renderButton] can render.
  ///
  /// Root cause of the "Getting ready" hang / popup that never produces a
  /// token: the web button previously called `renderButton` without ever
  /// calling `GoogleSignIn.instance.initialize(clientId:)` — GSI had no
  /// configured client, so the button stayed in its loading placeholder and
  /// any popup could not mint a credential. Initialization is delegated to
  /// [GoogleAuthScriptLoader] for flag gating + safe (no-retry) failure.
  Future<void> _init() async {
    final clientId = ref.read(googleAuthProvider).clientId;
    final ok = await GoogleAuthScriptLoader.instance.loadScript(
      clientId: clientId,
    );
    if (!mounted) return;
    setState(() => _gsiReady = ok);
  }

  void _onSignIn(GoogleSignInAuthenticationEvent event) {
    if (event case GoogleSignInAuthenticationEventSignIn(:final user)) {
      _exchange(user.authentication.idToken);
    }
  }

  void _onError(Object error, StackTrace stackTrace) {
    // A dismissed GSI flow surfaces as a GoogleSignInException on the stream.
    final code = switch (error) {
      GoogleSignInException(:final code) =>
        code == GoogleSignInExceptionCode.canceled ||
                code == GoogleSignInExceptionCode.interrupted ||
                code == GoogleSignInExceptionCode.uiUnavailable
            ? 'google_popup_closed'
            : 'google_sign_in_failed',
      _ => 'google_unknown',
    };
    _showError(code);
  }

  Future<void> _exchange(String? idToken) async {
    if (idToken == null || idToken.isEmpty) {
      _showError('google_popup_closed');
      return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    final err = await ref
        .read(authControllerProvider.notifier)
        .signInWithGoogleFromCredential(idToken);
    if (!mounted) return;
    setState(() => _busy = false);
    if (err != null) _showError(err);
  }

  void _showError(String code) {
    if (!mounted) return;
    final tr = ref.read(trProvider);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(googleSignInErrorMessage(code, tr: tr)),
        backgroundColor: AppTheme.error,
      ),
    );
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_busy) {
      // Mirror the mobile button's loading affordance.
      return const SizedBox(height: 48, child: Center(child: BrandSpinner()));
    }
    if (!_gsiReady) {
      // GSI client not initialized (script blocked, flag off, or failure).
      // Render nothing instead of Google's stuck "Getting ready" iframe.
      return const SizedBox(height: 48);
    }
    // The GSI-rendered button fills the available width; constrain its height
    // so it aligns with the mobile button.
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: gsi_web.renderButton(configuration: widget.configuration),
    );
  }
}
