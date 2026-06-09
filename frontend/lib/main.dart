import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'features/whisky/presentation/controllers/whisky_providers.dart';
import 'features/whisky/presentation/screens/home_screen.dart';
import 'features/whisky/presentation/screens/setup_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: MaltRadarApp(),
    ),
  );
}

class MaltRadarApp extends ConsumerWidget {
  const MaltRadarApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settingsAsync = ref.watch(referenceSettingsStreamProvider);

    return MaterialApp(
      title: 'Malt Radar',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: settingsAsync.when(
        data: (settings) {
          final id = settings['reference_whisky_id'];
          if (id != null) {
            return const HomeScreen();
          } else {
            return const SetupScreen();
          }
        },
        loading: () => const Scaffold(
          body: Center(
            child: CircularProgressIndicator(color: AppTheme.primary),
          ),
        ),
        error: (error, stack) => Scaffold(
          body: Center(
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text('Veritabanı başlatılamadı:\n$error\n\nStack:\n$stack', 
                  style: const TextStyle(color: AppTheme.error, fontSize: 12),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
