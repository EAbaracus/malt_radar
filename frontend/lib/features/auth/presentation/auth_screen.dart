import 'package:flutter/foundation.dart'; // kIsWeb
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/analytics/analytics_service.dart';
import 'package:malt_radar/core/config/feature_flags.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import 'package:malt_radar/features/compliance/presentation/age_gate_providers.dart';
import 'auth_controller.dart';
import 'referral_utils.dart';
import 'google_sign_in_button.dart';
import 'google_sign_in_web_button.dart';
import 'google_sign_in_messages.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';

/// Login / Register form. Uses the already-passed age gate decision to fill the
/// required country + legal-minimum-age at registration (KVKK consent is
/// explicitly requested here).
class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({this.initialMode = AuthMode.login, super.key});

  final AuthMode initialMode;

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

enum AuthMode { login, register }

class _AuthScreenState extends ConsumerState<AuthScreen> {
  late AuthMode _mode;
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  final _displayName = TextEditingController();
  bool _privacyConsent = false;
  bool _ageAffirm = false;
  bool _busy = false;
  bool _googleBusy = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    _displayName.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final isTr = ref.read(localizationProvider) == 'tr';
    final email = _email.text.trim();
    final password = _password.text;

    if (email.isEmpty || password.isEmpty) {
      _toast(isTr ? 'Tüm alanları doldurun' : 'Please fill in all fields');
      return;
    }
    // Basic email shape check before any network call.
    final emailRe = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
    if (!emailRe.hasMatch(email)) {
      _toast(isTr ? 'Geçerli bir e-posta girin' : 'Please enter a valid email');
      return;
    }
    setState(() => _busy = true);

    // Track sign_up_start for register mode
    if (_mode == AuthMode.register) {
      ref.read(analyticsServiceProvider).trackSignUpStart(
        entryPoint: 'auth_screen',
        authProvider: 'email',
        sessionId: ref.read(sessionIdProvider),
      );
    }

    String? err;
    try {
      if (_mode == AuthMode.login) {
        err = await ref
            .read(authControllerProvider.notifier)
            .login(email, password);
      } else {
        if (password.length < 8) {
          setState(() => _busy = false);
          _toast(
            isTr
                ? 'Şifre en az 8 karakter olmalı'
                : 'Password must be at least 8 characters',
          );
          return;
        }
        if (password != _confirm.text) {
          setState(() => _busy = false);
          _toast(isTr ? 'Şifreler eşleşmiyor' : 'Passwords do not match');
          return;
        }
        if (!_privacyConsent || !_ageAffirm) {
          setState(() => _busy = false);
          _toast(
            isTr
                ? 'Devam için onay kutularını işaretleyin'
                : 'Please accept the consent boxes to continue',
          );
          return;
        }
        final age = ref.read(ageGateProvider);
        final country = age.country ?? 'XX';
        final minAge = age.minAge ?? 18;
        err = await ref
            .read(authControllerProvider.notifier)
            .register(
              email: email,
              password: password,
              displayName: _displayName.text.trim().isEmpty
                  ? null
                  : _displayName.text.trim(),
              ageCountry: country,
              ageMin: minAge,
              privacyConsent: _privacyConsent,
            );
      }
    } catch (e) {
      // Catch any unexpected exception
      err = isTr ? 'Beklenmeyen hata: $e' : 'Unexpected error: $e';
    }

    if (!mounted) return;
    setState(() => _busy = false);
    if (err == null) {
      // Track sign_up_complete on successful registration
      if (_mode == AuthMode.register) {
        ref.read(analyticsServiceProvider).trackSignUpComplete(
          userId: email,
          authProvider: 'email',
          sessionId: ref.read(sessionIdProvider),
          referralSource: extractReferralSource(),
        );
      }
      // Login/register succeeded. Force main.dart rebuild.
      ref.invalidate(authControllerProvider);
    } else {
      _toast(err);
    }
  }

  Future<void> _signInWithGoogle() async {
    if (_googleBusy) return;
    final isTr = ref.read(localizationProvider) == 'tr';
    setState(() => _googleBusy = true);

    String? err;
    try {
      err = await ref.read(authControllerProvider.notifier).signInWithGoogle();
    } catch (e) {
      // Catch any unexpected exception (timeout, parse error, etc.)
      err = isTr ? 'Beklenmeyen hata: $e' : 'Unexpected error: $e';
    }

    if (!mounted) return;
    setState(() => _googleBusy = false);
    if (err == null) {
      // Track sign_up_complete for Google Sign-In
      ref.read(analyticsServiceProvider).trackSignUpComplete(
        userId: ref.read(authControllerProvider).user?.email ?? 'google_user',
        authProvider: 'google',
        sessionId: ref.read(sessionIdProvider),
        referralSource: extractReferralSource(),
      );
    } else {
      _toast(googleSignInErrorMessage(err, isTr: isTr));
    }
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppTheme.error),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isTr = ref.watch(localizationProvider) == 'tr';
    // Don't watch auth here - let main.dart handle navigation.
    // When login succeeds, main.dart rebuilds and unmounts this widget.

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Brand header — first-viewport product signal (matches the
              // splash wordmark; static medallion, no spin).
              const Center(
                child: Medallion(size: 72, level: MedallionLevel.master),
              ),
              const SizedBox(height: 12),
              Center(
                child: Text(
                  'MALT RADAR',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: AppTheme.primary,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 2.0,
                  ),
                ),
              ),
              const SizedBox(height: 32),
              Text(
                _mode == AuthMode.login
                    ? (isTr ? 'Giriş Yap' : 'Sign in')
                    : (isTr ? 'Kayıt Ol' : 'Create account'),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _mode == AuthMode.login
                    ? (isTr
                          ? 'Hesabına devam et, kişisel viski verilerini cihazlar arasında sakla.'
                          : 'Sign in to keep your personal whisky data across devices.')
                    : (isTr
                          ? 'Kayıt ile favoriler, listeler ve puanlar sunucuya senkronize olur.'
                          : 'Create an account to sync favorites, lists and scores.'),
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(height: 1.4),
              ),
              const SizedBox(height: 24),
              // The form is a framed tool (sheet-like surface) per the
              // DESIGN.md overlay/sheet family — not a repeated list card.
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: AppThemeColors.parchment.withValues(alpha: 0.08),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // TODO(i18n): move the Google button label and the Google
                    // error strings (_googleErrorMessage) into the app's
                    // translation table (trProvider) once it exists.
                    // Web uses Google's native GSI `renderButton`; mobile keeps our
                    // styled button driving `authenticate()`. Both are gated behind
                    // the compile-time feature flag (default OFF in production —
                    // GSI script is not loaded and no Google button/divider renders
                    // until `--dart-define=ENABLE_GOOGLE_SIGN_IN=true`).
                    if (ref.watch(googleSignInEnabledProvider)) ...[
                      if (kIsWeb)
                        const GoogleSignInWebButton()
                      else
                        GoogleSignInButton(
                          label: isTr
                              ? 'Google ile devam et'
                              : 'Continue with Google',
                          isLoading: _googleBusy,
                          onPressed: _signInWithGoogle,
                        ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          const Expanded(
                            child: Divider(
                              color: AppTheme.textSecondary,
                              thickness: 1,
                              height: 1,
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            child: Text(
                              isTr ? 'veya' : 'or',
                              style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          const Expanded(
                            child: Divider(
                              color: AppTheme.textSecondary,
                              thickness: 1,
                              height: 1,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                    ],
                    if (_mode == AuthMode.register) ...[
                      TextField(
                        controller: _displayName,
                        style: const TextStyle(color: AppThemeColors.parchment),
                        decoration: InputDecoration(
                          labelText: isTr
                              ? 'Görünen ad (opsiyonel)'
                              : 'Display name (optional)',
                          prefixIcon: const Icon(
                            Icons.person_outline,
                            color: AppTheme.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    TextField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      autocorrect: false,
                      style: const TextStyle(color: AppThemeColors.parchment),
                      decoration: InputDecoration(
                        labelText: 'E-posta',
                        prefixIcon: const Icon(
                          Icons.mail_outline,
                          color: AppTheme.primary,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _password,
                      obscureText: true,
                      style: const TextStyle(color: AppThemeColors.parchment),
                      decoration: InputDecoration(
                        labelText: isTr ? 'Şifre' : 'Password',
                        prefixIcon: const Icon(
                          Icons.lock_outline,
                          color: AppTheme.primary,
                        ),
                      ),
                    ),
                    if (_mode == AuthMode.register) ...[
                      const SizedBox(height: 16),
                      TextField(
                        controller: _confirm,
                        obscureText: true,
                        style: const TextStyle(color: AppThemeColors.parchment),
                        decoration: InputDecoration(
                          labelText: isTr
                              ? 'Şifre (tekrar)'
                              : 'Confirm password',
                          prefixIcon: const Icon(
                            Icons.lock_outline,
                            color: AppTheme.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      _ConsentRow(
                        value: _privacyConsent,
                        text: isTr
                            ? 'Kişisel veri işleme aydınlatma metnini okudum ve kabul ediyorum (KVKK).'
                            : 'I have read and accept the privacy notice / KVKK data-processing consent.',
                        onChanged: (v) => setState(() => _privacyConsent = v),
                      ),
                      const SizedBox(height: 8),
                      _ConsentRow(
                        value: _ageAffirm,
                        text: isTr
                            ? 'Ülkemin yasal içki yaşını doldurduğumu onaylıyorum.'
                            : 'I confirm I am of legal drinking age in my country.',
                        onChanged: (v) => setState(() => _ageAffirm = v),
                      ),
                    ],
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: _busy ? null : _submit,
                      child: _busy
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: BrandSpinner(),
                            )
                          : Text(
                              _mode == AuthMode.login
                                  ? (isTr ? 'GİRİŞ YAP' : 'SIGN IN')
                                  : (isTr ? 'KAYIT OL' : 'SIGN UP'),
                            ),
                    ),
                    const SizedBox(height: 12),
                    TextButton(
                      onPressed: () {
                        setState(() {
                          _mode = _mode == AuthMode.login
                              ? AuthMode.register
                              : AuthMode.login;
                        });
                      },
                      child: Text(
                        _mode == AuthMode.login
                            ? (isTr
                                  ? 'Hesabın yok mu? Kaydol'
                                  : "Don't have an account? Sign up")
                            : (isTr
                                  ? 'Zaten hesabın var? Giriş yap'
                                  : 'Already have an account? Sign in'),
                        style: const TextStyle(color: AppTheme.textSecondary),
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: () {
                        ref.read(guestModeProvider.notifier).state = true;
                      },
                      child: Text(
                        isTr ? 'Misafir Olarak İncele' : 'Explore as Guest',
                        style: const TextStyle(
                          color: AppTheme.textSecondary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ConsentRow extends StatelessWidget {
  final bool value;
  final String text;
  final ValueChanged<bool> onChanged;
  const _ConsentRow({
    required this.value,
    required this.text,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Checkbox(
          value: value,
          activeColor: AppTheme.primary,
          onChanged: (v) => onChanged(v ?? false),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              text,
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
