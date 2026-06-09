import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app_translations.dart';
import '../database/database.dart';
import '../../features/whisky/presentation/controllers/whisky_providers.dart';

// Provides the current active language code (e.g., 'tr', 'en')
class LocalizationNotifier extends StateNotifier<String> {
  final AppDatabase db;

  LocalizationNotifier(this.db) : super('tr') {
    _loadLanguage();
  }

  Future<void> _loadLanguage() async {
    final query = db.select(db.userSettings)..where((t) => t.key.equals('language'));
    final result = await query.getSingleOrNull();
    if (result != null) {
      state = result.value;
    }
  }

  Future<void> setLanguage(String langCode) async {
    state = langCode;
    await db.into(db.userSettings).insertOnConflictUpdate(
      UserSettingsCompanion.insert(key: 'language', value: langCode)
    );
  }
}

// Global provider for LocalizationNotifier
final localizationProvider = StateNotifierProvider<LocalizationNotifier, String>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return LocalizationNotifier(db);
});

// A simple extension to translate strings easily in any widget
extension LocalizationExtension on BuildContext {
  String tr(String key, [List<dynamic>? args]) {
    // We will use ProviderScope to read the current state if we are inside a widget,
    // but wait, BuildContext doesn't natively know Riverpod without WidgetRef.
    // Instead of context.tr, we will use ref.watch(translationProvider(key)) or similar.
    return key;
  }
}

// Since BuildContext extension is hard to bind to Riverpod reactively without ref.watch,
// we'll provide a helper method via Riverpod to get the translation function.
final trProvider = Provider<String Function(String, [List<dynamic>?])>((ref) {
  final langCode = ref.watch(localizationProvider);
  final map = appTranslations[langCode] ?? appTranslations['tr']!;
  
  return (String key, [List<dynamic>? args]) {
    String text = map[key] ?? key;
    if (args != null) {
      for (int i = 0; i < args.length; i++) {
        text = text.replaceAll('{$i}', args[i].toString());
      }
    }
    return text;
  };
});
