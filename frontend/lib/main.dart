import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'core/branding/brand_medallion.dart';
import 'core/branding/brand_medallion_widget.dart';
import 'core/consent/cmp_banner.dart';
import 'features/whisky/presentation/controllers/whisky_providers.dart';
import 'core/presentation/screens/main_navigation_screen.dart';
import 'features/auth/presentation/auth_screen.dart';
import 'features/auth/presentation/auth_controller.dart';
import 'features/compliance/presentation/age_gate_providers.dart';
import 'features/compliance/presentation/age_gate_screen.dart';
import 'features/compliance/presentation/age_gate_blocked_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: MaltRadarApp()));
}

class MaltRadarApp extends ConsumerWidget {
  const MaltRadarApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final age = ref.watch(ageGateProvider);
    final auth = ref.watch(authControllerProvider);
    final isGuest = ref.watch(guestModeProvider);

    return MaterialApp(
      title: 'Malt Radar',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: _homeFor(age, auth, isGuest, ref),
    );
  }

  /// Routes the entry screen through the compliance age gate. None of the
  /// product content renders until the user confirms they are of legal
  /// drinking age in their country.
  Widget _homeFor(
    AgeGateDecision age,
    AuthState auth,
    bool isGuest,
    WidgetRef ref,
  ) {
    switch (age.status) {
      case AgeGateStatus.unknown:
        return const _GateLoadingScaffold();
      case AgeGateStatus.notConsented:
        return const AgeGateScreen();
      case AgeGateStatus.blocked:
        return const AgeGateBlockedScreen();
      case AgeGateStatus.consented:
        // Overlay the CMP consent banner on the post-age-gate content. It
        // collapses to nothing once the user records a decision.
        return Stack(
          children: [
            _mainHome(auth, isGuest, ref),
            const Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: CmpBanner(),
            ),
          ],
        );
    }
  }

  Widget _mainHome(AuthState auth, bool isGuest, WidgetRef ref) {
    final initAsync = ref.watch(appInitializationProvider);

    // Handle init states first
    if (initAsync.isLoading) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Medallion(size: 96, level: MedallionLevel.master, animate: true),
              SizedBox(height: 16),
              Text(
                'Veritabanı hazırlanıyor...',
                style: TextStyle(color: AppTheme.textSecondary),
              ),
            ],
          ),
        ),
      );
    }

    if (initAsync.hasError) {
      return Scaffold(
        body: Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Text(
                'Veritabanı başlatılamadı:\\n${initAsync.error}\\n\\nStack:\\n${initAsync.stackTrace}',
                style: const TextStyle(
                  color: AppTheme.errorOnDark,
                  fontSize: 12,
                ),
              ),
            ),
          ),
        ),
      );
    }

    // Init complete — now check auth (this rebuilds when auth changes)
    if (auth.status == AuthStatus.unknown) {
      // Session restore in flight — show a neutral splash, avoiding a
      // login-screen flash for users who already have a session.
      return const Scaffold(
        body: Center(
          child: Medallion(
            size: 96,
            level: MedallionLevel.master,
            animate: true,
          ),
        ),
      );
    }
    if (!auth.isLoggedIn && !isGuest) {
      return const AuthScreen();
    }
    return const MainNavigationScreen();
  }
}

class _GateLoadingScaffold extends StatelessWidget {
  const _GateLoadingScaffold();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Medallion(size: 96, level: MedallionLevel.master, spin: true),
            const SizedBox(height: 16),
            Text(
              'MALT RADAR',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                color: AppTheme.primary,
                fontWeight: FontWeight.w900,
                letterSpacing: 2.0,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
