import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'package:malt_radar/core/config/feature_flags.dart';

/// GSI script yükleme garantisi (web). `google_sign_in` 7.x plugin'i Google
/// Identity Services (GSI) script'ini `initialize()` içinde KENDİSİ dinamik
/// olarak yüklüyor — bu katman DOM'a script inject ETMEZ (çift yükleme olur).
/// Rolü:
/// - feature flag kapalı veya web değilse `false` (script hiç yüklenmez),
/// - `initialize()` hatası → `completeError` DEĞİL `complete(false)` yazar
///   (uncaught exception riski olmaz; çağıran try/catch zorunluluğu yok),
/// - no-retry by design: bir kez `false` dönerse oturum boyunca `false` kalır
///   (geçici ağ hatası sonrası sessizce retry edilmez — kullanıcı email/şifre
///   akışında kalır, sayfa yenilemesi yeni şans verir).
class GoogleAuthScriptLoader {
  static final GoogleAuthScriptLoader instance = GoogleAuthScriptLoader._();
  GoogleAuthScriptLoader._();

  Completer<bool>? _completer;

  /// Returns `true` if GSI is ready for use, `false` if the feature flag is
  /// off, we are not on web, or script initialization failed.
  Future<bool> loadScript({String? clientId}) async {
    if (!kIsWeb || !FeatureFlags.enableGoogleSignIn) return false;
    if (_completer != null) return _completer!.future;
    _completer = Completer<bool>();
    try {
      await GoogleSignIn.instance.initialize(clientId: clientId);
      _completer!.complete(true);
    } catch (_) {
      // Never completeError: a failing GSI load must not surface as an
      // uncaught exception to consumers (no-retry by design).
      _completer!.complete(false);
    }
    return _completer!.future;
  }
}
