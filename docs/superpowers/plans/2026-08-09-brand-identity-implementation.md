# Malt Radar Marka Kimliği Uygulaması — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** App (`frontend/` Flutter) + web (`build/web` aynı codebase) marka kimliğine tam süpürme: etiketsiz 7-gen medallion (CustomPainter), marka paleti (Copper/Verdigris/Oxblood, brass yalnız amblem), 4 font asset bundle, markalı loading animasyonu, launcher ikonu.

**Architecture:** Tek Flutter codebase hem mobile hem web. Medallion `CustomPainter` (true-source, `level:` parametrik), renkler `AppTheme` token'larından, brass UI'dan yalıtık. Fallback yok, iki render yolu yok.

**Tech Stack:** Flutter (Riverpod, Drift, fl_chart, go_router), CustomPainter, `flutter_launcher_icons` (dev), 4 ün .ttf font asset. Google Fonts runtime indirme KALDIRILIR.

## Global Constraints

- **Repo:** `C:/Users/eltun/Documents/malt radar CLEAN` (GÜNCEL/kanonik). `malt radar` (CLEAN'sız) ESKİ snapshot — buraya YAZMA.
- **Kod icra durumu: BEKLE.** Spec/plan tamam. Kod tasks'leri ancak kullanıcı "GO" verdiğinde (mevcut sosyal/X queue işi bittikten ve branch kararı sonrası) uygulanır. Bu plan icra için hazırlandı, icra edilmedi.
- `AppConfig.useDbApi` default (`MALT_RADAR_USE_DB_API` defaultValue:true) **DOKUNULMAZ** (protected).
- Catalog CSV'leri client bundle'a **ASLA geri gelmez.** Font `.ttf` asset'e girer; `assets/data/*.csv` GİREMEZ. `pubspec.yaml` satır 82-84'teki CSV'ler yorumda kalır.
- `production.db`'ye HİÇBİR yazma; backend/schema DEĞİŞMEZ — tamamen frontend rebrand.
- Brass (brass `#C9A227`) token'ı `AppTheme`'e KONMAZ; yalnız `app_theme_colors.dart` içinde `MedallionPalette.rimNeedle`.
- Dark-only bu sprint; light theme ayrı planlanır (kullanıcı erteledi).
- `google_fonts` KALDIRILIR → `TextStyle(fontFamily:...)`. Offline-safe, deterministik, Play-safe.
- Testi: `flutter test --no-pub` (skill: iOS ephemeral `.packages` fix gerekebilir).

---

### Task 1: Marka palet sabitleri + MedallionPalette

**Files:**
- Create: `frontend/lib/core/theme/app_theme_colors.dart`
- Test: `frontend/test/app_theme_colors_test.dart`

**Interfaces:**
- Consumes: (yok — taze dosya)
- Produces: `class AppThemeColors` (static const hex renkler), `class MedallionPalette` (web/rim/needle/dot/textColor), `kMasterDarkPalette`, `kMasterLightPalette`, `kMedallionFontFamily` (Courier Prime sabiti).

- [ ] **Step 1: Write the failing test**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  test('marka paleti hex değerleri kilitli', () {
    expect(AppThemeColors.caskChar, const Color(0xFF1A120B));
    expect(AppThemeColors.parchment, const Color(0xFFEDE1C8));
    expect(AppThemeColors.copper, const Color(0xFFA6672C));
    expect(AppThemeColors.verdigris, const Color(0xFF5C7A6E));
    expect(AppThemeColors.brass, const Color(0xFFC9A227));
    expect(AppThemeColors.oxblood, const Color(0xFF6B1E23));
  });

  test('MedallionPalette master dark: web/dot copper, rim/needle brass, metin parchment', () {
    final p = kMasterDarkPalette;
    expect(p.web, const Color(0xFFA6672C));
    expect(p.rim, const Color(0xFFC9A227));
    expect(p.needle, const Color(0xFFC9A227));
    expect(p.dot, const Color(0xFFA6672C));
    expect(p.textColor, const Color(0xFFEDE1C8));
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/app_theme_colors_test.dart --no-pub`
Expected: FAIL — "not defined" (`AppThemeColors`/`kMasterDarkPalette` yok).

- [ ] **Step 3: Write minimal implementation** (`app_theme_colors.dart`)

```dart
import 'package:flutter/material.dart';

/// Marka paleti — tek token kaynağı. Görsel spec:
/// docs/superpowers/specs/2026-08-09-brand-identity-implementation-design.md
/// Kullanım oranı: ~%65 char/parşömen · %20 bakır · %10 verdigris · %5 pirinç/oxblood.
class AppThemeColors {
  const AppThemeColors._();

  static const Color caskChar = Color(0xFF1A120B);        // zemin / metin
  static const Color parchment = Color(0xFFEDE1C8);       // açık zemin
  static const Color parchmentLt = Color(0xFFF5ECD8);
  static const Color inkSoft = Color(0xFF2B1F14);
  static const Color copper = Color(0xFFA6672C);          // birincil vurgu
  static const Color copperDim = Color(0xFF8A5424);
  static const Color verdigris = Color(0xFF5C7A6E);       // ikincil vurgu / rozet
  static const Color brass = Color(0xFFC9A227);           // SADECE amblem mühür halkası + ibre
  static const Color oxblood = Color(0xFF6B1E23);         // nadir — uyarı/özel rozet
}

/// Medallion renk paketi. `brass` yalnızca burada (rim/needle) yaşar.
/// UI widgetlarının brass'a erişimi YOKTUR (AppTheme'e konmaz).
class MedallionPalette {
  const MedallionPalette({
    required this.web,
    required this.rim,
    required this.needle,
    required this.dot,
    required this.textColor,
  });

  final Color web;       // 7-gen çizgileri
  final Color rim;       // dış mühür halkası (brass)
  final Color needle;    // ibre (brass)
  final Color dot;       // köşe noktaları
  final Color textColor; // yedek — etiket yok, ileride kullanılırsa

  static const MedallionPalette masterDark = MedallionPalette(
    web: AppThemeColors.copper,
    rim: AppThemeColors.brass,
    needle: AppThemeColors.brass,
    dot: AppThemeColors.copper,
    textColor: AppThemeColors.parchment,
  );

  static const MedallionPalette masterLight = MedallionPalette(
    web: AppThemeColors.copperDim,
    rim: AppThemeColors.copperDim,
    needle: AppThemeColors.oxblood,
    dot: AppThemeColors.oxblood,
    textColor: AppThemeColors.caskChar,
  );
}

const kMasterDarkPalette = MedallionPalette.masterDark;
const kMasterLightPalette = MedallionPalette.masterLight;
const kMedallionFontFamily = 'CourierPrime';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/app_theme_colors_test.dart --no-pub`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/core/theme/app_theme_colors.dart frontend/test/app_theme_colors_test.dart
git commit -m "feat(brand): marka paleti sabitleri + MedallionPalette (brass yalniz amblem)"
```

---

### Task 2: MedallionPainter — etiketsiz 7-gen, 3 kademe

**Files:**
- Create: `frontend/lib/core/branding/brand_medallion.dart`
- Test: `frontend/test/brand_medallion_test.dart`

**Interfaces:**
- Consumes: `MedallionPalette`, `AppThemeColors` (Task 1)
- Produces: `enum MedallionLevel { master, icon, micro }`, `class MedallionPainter extends CustomPainter` (ctor `MedallionPainter({required MedallionPalette palette, MedallionLevel level = MedallionLevel.master})`), `double kMedallionNeedleRestAngle = 0.0`, `double kMedallionSweepAngle = ...` (anim Task 6'da). `shouldRepaint(covariant MedallionPainter old) => old.palette != palette || old.level != level`.

- [ ] **Step 1: Write the failing test**

```dart
import 'dart:ui' as ui;
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/branding/brand_medallion.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  // Geometri: 200x200 viewBox; merkez (100,100).
  const pts = [
    Offset(100, 30), Offset(154.73, 56.35), Offset(168.26, 115.57),
    Offset(130.37, 163.07), Offset(69.63, 163.07),
    Offset(31.74, 115.57), Offset(45.27, 56.35),
  ];

  test('7-gen vertex koordinatları geometriye uyuyor', () {
    // Dış 7-gen: eş merkezli, düzenli. maxX-minX > 100 (geniş) ve yükseklik ~133.
    final xs = pts.map((p) => p.dx).toList();
    final ys = pts.map((p) => p.dy).toList();
    expect(xs.reduce((a, b) => a > b ? a : b) - xs.reduce((a, b) => a < b ? a : b), greaterThan(100));
    expect(ys.reduce((a, b) => a > b ? a : b) - ys.reduce((a, b) => a < b ? a : b), inInclusiveRange(125, 140));
  });

  test('painter 3 kademede de üretir; micro'da ring/dot yok', () {
    // shouldRepaint davranışı
    final p = MedallionPainter(palette: kMasterDarkPalette, level: MedallionLevel.master);
    final p2 = MedallionPainter(palette: kMasterDarkPalette, level: MedallionLevel.micro);
    expect(p.shouldRepaint(p2), isTrue);          // level farklı → repaint
    expect(p.shouldRepaint(p), isFalse);          // aynı → repaint yok

    // micro: level enum'ı döner, çizim farkı paint.showInnerRings / showOuterRim flag'lerinde.
    expect(p2.level, MedallionLevel.micro);
    expect(p.level, MedallionLevel.master);
  });

  test('palet brass yalnizca rim+needle (UI brass erisimi yok)', () {
    // AppThemeColors.brass mevcut; MedallionPalette.masterDark.rim == brass
    expect(kMasterDarkPalette.rim, AppThemeColors.brass);
    expect(kMasterDarkPalette.needle, AppThemeColors.brass);
    // web/dot asla brass değil
    expect(kMasterDarkPalette.web, isNot(AppThemeColors.brass));
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/brand_medallion_test.dart --no-pub`
Expected: FAIL — `MedallionPainter`/`MedallionLevel` tanımsız.

- [ ] **Step 3: Write minimal implementation** (`brand_medallion.dart`)

Geometri dosyadan geliyor, CustomPainter: merkez (100,100), 7 dış köşe + mid ring + inner ring (yalnız master), ibre + merkez pivot. Etiket/text ÇİZİLMEZ (karar #1). Level'a göre detay flagleri.

```dart
import 'package:flutter/material.dart';
import '../theme/app_theme_colors.dart';

enum MedallionLevel { master, icon, micro }

/// Marka amblemi — "7 eksenli ölçüm"ün sabit sembolü. ETİKETSİZDİR;
/// canonical eksen isimleri yalnızca app içindeki gerçek radar chart'ta gösterilir.
class MedallionPainter extends CustomPainter {
  MedallionPainter({
    required this.palette,
    this.level = MedallionLevel.master,
    this.needleRotation = 0.0, // radyan; animasyonlu sweep Task 6'da set edilir
  });

  final MedallionPalette palette;
  final MedallionLevel level;
  final double needleRotation;

  // Dış 7-gen köşeleri (200x200 viewBox), marka dokümanından.
  static const List<Offset> outer7 = [
    Offset(100, 30), Offset(154.73, 56.35), Offset(168.26, 115.57),
    Offset(130.37, 163.07), Offset(69.63, 163.07),
    Offset(31.74, 115.57), Offset(45.27, 56.35),
  ];
  static const List<Offset> mid7 = [
    Offset(100, 45), Offset(143.0, 65.71), Offset(153.64, 112.24),
    Offset(123.86, 149.56), Offset(76.14, 149.56),
    Offset(46.36, 112.24), Offset(57.0, 65.71),
  ];
  static const List<Offset> inner7 = [
    Offset(100, 60), Offset(131.27, 75.06), Offset(139.01, 108.90),
    Offset(117.36, 136.04), Offset(82.64, 136.04),
    Offset(60.99, 108.90), Offset(68.73, 75.06),
  ];

  bool get _showInnerRings => level == MedallionLevel.master;
  bool get _showOuterRim => level != MedallionLevel.micro;
  bool get _showDots => level != MedallionLevel.micro;
  double get _webStroke =>
      level == MedallionLevel.micro ? 2.0 : 1.3;
  double get _needleStroke =>
      level == MedallionLevel.micro ? 2.2 : 1.6;

  @override
  void paint(Canvas canvas, Size size) {
    // viewBox 200x200 -> size scale
    final s = size.shortestSide / 200.0;
    canvas.scale(s);
    final center = const Offset(100, 100);

    final webPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _webStroke
      ..color = palette.web;

    if (_showOuterRim) {
      final rimPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6
        ..color = palette.rim;
      canvas.drawCircle(center, 95, rimPaint);
      if (_showInnerRings) {
        final innerRim = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.6
          ..color = palette.rim.withValues(alpha: 0.55);
        canvas.drawCircle(center, 88, innerRim);
      }
    }

    final path = Path()..moveTo(outer7[0].dx, outer7[0].dy);
    for (var i = 1; i < outer7.length; i++) {
      path.lineTo(outer7[i].dx, outer7[i].dy);
    }
    path.close();
    canvas.drawPath(path, webPaint);

    if (_showInnerRings) {
      canvas.drawPath(_poly(mid7), Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.6
        ..color = palette.web.withValues(alpha: 0.5));
      canvas.drawPath(_poly(inner7), Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.6
        ..color = palette.web.withValues(alpha: 0.35));
    }

    if (_showDots) {
      final dotPaint = Paint()..color = palette.dot;
      for (final p in outer7) {
        canvas.drawCircle(p, 2.4, dotPaint);
      }
    }

    // İbre (pivot (100,100))
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(needleRotation);
    final needlePaint = Paint()
      ..strokeWidth = _needleStroke
      ..strokeCap = StrokeCap.round
      ..color = palette.needle;
    canvas.drawLine(const Offset(0, 0), const Offset(0, -66), needlePaint);
    canvas.drawCircle(Offset.zero, 3.4, Paint()..color = palette.needle);
    canvas.restore();
  }

  Path _poly(List<Offset> pts) {
    final p = Path()..moveTo(pts[0].dx, pts[0].dy);
    for (var i = 1; i < pts.length; i++) {
      p.lineTo(pts[i].dx, pts[i].dy);
    }
    return p..close();
  }

  @override
  bool shouldRepaint(covariant MedallionPainter oldDelegate) =>
      oldDelegate.palette != palette ||
      oldDelegate.level != level ||
      oldDelegate.needleRotation != needleRotation;
}
```

> Not: `withValues(alpha:)` Flutter 3.27+ API'si; repo `sdk: ^3.12.1` (Dart) — Flutter sürümü uyumu implement sırasında `flutter --version` ile teyit edilir. Eski Flutter'da `withOpacity` kullan.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/brand_medallion_test.dart --no-pub`
Expected: PASS (implement sırasında `flutter --version` teyidi + geometrik assert'ler).

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/core/branding/brand_medallion.dart frontend/test/brand_medallion_test.dart
git commit -m "feat(brand): etiketsiz MedallionPainter (master/icon/micro) + geometri testi"
```

---

### Task 3: Medallion widget + tek sefer sweep animasyonu

**Files:**
- Create: `frontend/lib/core/branding/brand_medallion_widget.dart`
- Test: `frontend/test/brand_medallion_widget_test.dart`

**Interfaces:**
- Consumes: `MedallionPainter`, `MedallionLevel`, paletler (Task 2)
- Produces: `class Medallion extends StatefulWidget` (`const Medallion({super.key, this.size=48, this.level=MedallionLevel.icon, this.palette, this.animate=false})`); `animate:true` → tek sefer sweep 0→410°→360° (easing cubic-bezier .2,.7,.15,1) sonra sabit; `animate:false` (default) → statik, `pumpAndSettle` güvenli (ticker yok). `MediaQuery.disableAnimations` true ise sweep kapalı.

- [ ] **Step 1: Write the failing test**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  testWidgets('animate:false default — statik, pumpAndSettle güvenli', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Medallion(size: 60, level: MedallionLevel.master, palette: kMasterDarkPalette),
    ));
    // pumpAndSettle sonsuz döngüye takılmamalı (ticker yok)
    await tester.pumpAndSettle();
    expect(find.byType(Medallion), findsOneWidget);
  });

  testWidgets('animate:true — tek sefer sweep COMPLETED, döngü yok', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: SizedBox(
        width: 200, height: 200,
        child: Medallion(size: 200, level: MedallionLevel.master,
            palette: kMasterDarkPalette, animate: true),
      ),
    ));
    await tester.pumpAndSettle(const Duration(milliseconds: 3000));
    // Anim sona erdi → sonsuz ticker yok. pumpAndSettle dönerse PASS.
  });

  testWidgets('reduced-motion — animasyon kapalı', (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        FakeAccessibilityFeatures(disableAnimations: true);
    await tester.pumpWidget(const MaterialApp(
      home: Medallion(size: 100, animate: true, palette: kMasterDarkPalette),
    ));
    await tester.pumpAndSettle();
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/brand_medallion_widget_test.dart --no-pub`
Expected: FAIL — `Medallion` tanımsız.

- [ ] **Step 3: Write minimal implementation** (`brand_medallion_widget.dart`)

```dart
import 'package:flutter/material.dart';
import 'brand_medallion.dart';
import '../theme/app_theme_colors.dart';

/// Markalı medallion widget'ı.
/// - default statik (ticker yok, pumpAndSettle güvenli).
/// - animate:true → tek sefer sweep (0→410°→360°), sonra sabit.
///   LOOP YASAK (marka kuralı: ibre döndürülemez).
/// - reduced-motion'da animasyon kapanır.
class Medallion extends StatefulWidget {
  const Medallion({
    super.key,
    this.size = 48,
    this.level = MedallionLevel.icon,
    this.palette,
    this.animate = false,
  });

  final double size;
  final MedallionLevel level;
  final MedallionPalette? palette;
  final bool animate;

  @override
  State<Medallion> createState() => _MedallionState();
}

class _MedallionState extends State<Medallion>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _rotation;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    final reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (widget.animate && !reduce) {
      _controller = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 2400),
      );
      _rotation = TweenSequence<double>([
        TweenSequenceItem(
          tween: Tween(begin: 0.0, end: _deg2rad(410)).chain(
              CurveTween(curve: Curves.easeOutCubic)),
          weight: 72,
        ),
        TweenSequenceItem(
          tween: Tween(begin: _deg2rad(410), end: _deg2rad(360)),
          weight: 28,
        ),
      ]).animate(_controller);
      _controller.addStatusListener((status) {
        if (status == AnimationStatus.completed) {
          setState(() => _done = true);
        }
      });
      _controller.forward();
    } else {
      _controller = AnimationController.unbounded(vsync: this); // ticker yok
    }
  }

  static double _deg2rad(double d) => d * 3.141592653589793 / 180.0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final rot = _done
            ? _deg2rad(360.0)
            : (_rotation?.value ?? 0.0);
        return CustomPaint(
          size: Size.square(widget.size),
          painter: MedallionPainter(
            palette: widget.palette ??
                (Theme.of(context).brightness == Brightness.dark
                    ? kMasterDarkPalette
                    : kMasterLightPalette),
            level: widget.level,
            needleRotation: rot,
          ),
        );
      },
    );
  }
}
```

> Marka kuralı: 360°'de "settle" tamamlanır; ileride dinamik bir açı istenmezse (ör. splash sonrası) `needleRestAngle` parametresiyle sabitlenir. Şu an kural: tek sefer sweep → 360° sabit.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/brand_medallion_widget_test.dart --no-pub`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/core/branding/brand_medallion_widget.dart frontend/test/brand_medallion_widget_test.dart
git commit -m "feat(brand): Medallion widget + tek sefer sweep animasyonu (loop yasak)"
```

---

### Task 4: AppTheme token swap + font haritası (google_fonts kaldır)

**Files:**
- Modify: `frontend/lib/core/theme/app_theme.dart` (tam değişim)
- Modify: `frontend/pubspec.yaml` (font asset girişleri + google_fonts kaldır)
- Add fonts (implement günü indirilir): `frontend/assets/fonts/Fraunces-*.ttf`, `SourceSerif4-*.ttf`, `CourierPrime-Regular.ttf`, `Inter-*.ttf`
- Test: `frontend/test/app_theme_test.dart`

**Interfaces:**
- Consumes: `AppThemeColors` (Task 1)
- Produces: `AppTheme.darkTheme` marka tokenları + `TextTheme` (display=Fraunces, gövde=SourceSerif4, UI=Inter); `AppTheme.background/surface/primary/...` marka değerleri. Brass `AppTheme`'e KONMAZ.

- [ ] **Step 1: Write the failing test**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';

void main() {
  test('AppTheme tokenları marka paletine map'li — eski gold yok', () {
    expect(AppTheme.background, AppThemeColors.caskChar);
    expect(AppTheme.primary, AppThemeColors.copper);      // gold DEĞİL
    expect(AppTheme.secondary, AppThemeColors.verdigris);
    expect(AppTheme.error, AppThemeColors.oxblood);
  });

  test('brass AppTheme üzerinde TANIMLI DEĞİL (UI yalıtımı)', () {
    // AppTheme static üyelerinde brass yoktur — derleme anı yapısı:
    // brass yalnız AppThemeColors.brass / MedallionPalette'de.
    expect(AppThemeColors.brass, const Color(0xFFC9A227));
  });

  test('darkTheme font dokuları marka ailesini kullanır', () {
    final t = AppTheme.darkTheme;
    expect(t.textTheme.displayLarge?.fontFamily, 'Fraunces');
    expect(t.textTheme.bodyMedium?.fontFamily, 'SourceSerif4');
    expect(t.textTheme.labelSmall?.fontFamily, 'Inter');
    // eslint-disable: google_fonts kaldırıldı → import yoksa bu test derlenmeli.
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/app_theme_test.dart --no-pub`
Expected: FAIL — eski değerler (gold primary, font aileleri yok).

- [ ] **Step 3: Implement** — `app_theme.dart` token değerleri + font haritası (temel değişim). Font satırları eyleses: `GoogleFonts.X(...)` → `TextStyle(fontFamily: '...', ...)`. `google_fonts` import kaldırılır. `pubspec.yaml`:

```yaml
dependencies:
  # google_fonts: ^6.2.1   # KALDIRILDI (runtime indirme; offline/Play-safe değil)
  ...
flutter:
  uses-material-design: true
  fonts:
    - family: Fraunces
      fonts:
        - asset: assets/fonts/Fraunces-400.ttf
        - asset: assets/fonts/Fraunces-600.ttf
          weight: 600
        - asset: assets/fonts/Fraunces-700.ttf
          weight: 700
    - family: SourceSerif4
      fonts:
        - asset: assets/fonts/SourceSerif4-400.ttf
        - asset: assets/fonts/SourceSerif4-600.ttf
          weight: 600
    - family: CourierPrime
      fonts:
        - asset: assets/fonts/CourierPrime-Regular.ttf
    - family: Inter
      fonts:
        - asset: assets/fonts/Inter-400.ttf
        - asset: assets/fonts/Inter-500.ttf
          weight: 500
        - asset: assets/fonts/Inter-600.ttf
          weight: 600
        - asset: assets/fonts/Inter-700.ttf
          weight: 700
```

> **ÇİZGİSEL:** `google_fonts` kaldırınca `pubspec.lock` güncellenir ve `flutter pub get` gerekir. Font `.ttf` dosyaları implement günü indirilip `assets/fonts/` altına konur (Google Fonts static dosyaları). CSRV asset eklenmez — `assets/data/*.csv` yorumda kalır (satır 82-84).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter pub get && flutter test test/app_theme_test.dart --no-pub`
Expected: PASS

- [ ] **Step 5: Gate doğrula** (anti-scrape + brass)

```bash
cd frontend
grep -rn "D4AF37" lib || echo "GOLD YOK (OK)"
grep -rn "C9A227" lib        # yalnız core/theme/app_theme_colors.dart geçmeli
grep -rn "assets/data.*csv" lib test   # boş olmalı
```

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/core/theme/app_theme.dart frontend/pubspec.yaml frontend/test/app_theme_test.dart
git add frontend/assets/fonts        # .ttf'ler
git commit -m "feat(brand): AppTheme marka paleti + font haritası; google_fonts kaldırıldı"
```

---

### Task 5: Ekran sweep — radar chart + tüm AppTheme referansları

**Files:**
- Modify: `frontend/lib/features/flavor/presentation/widgets/flavor_radar_chart.dart`
- Modify: `frontend/lib/main.dart` (süpürme, yalnız referans)
- Modify: rest `frontend/lib/**` — hardcode `Color(...)` / `AppTheme.*` markaya (taranır)
- Test: mevcut suite (renk assert eden test yok — skill doğruladı)

**Interfaces:**
- Consumes: marka `AppTheme.primary/secondary/...`
- Produces: tutarlı marka rengi her ekranda.

- [ ] **Step 1: Radar chart renk** — `flavor_radar_chart.dart:34,35`

```dart
// satır 34-35: fillColor: AppTheme.secondary.withValues(alpha: 0.3), borderColor: AppTheme.primary
// Zaten token tabanlı → markaya otomatik uyar (primary=copper). Değişmez — doğrulanır.
```

- [ ] **Step 2: Kalan sert kodları tara ve map'le** (implement günü)

```bash
cd frontend && grep -rn "0xFF" lib | grep -v "app_theme_colors\|app_theme.dart" 
# Her sert hex, marka tokenına eşlenir:
#   #D4AF37 gold            -> AppTheme.primary (copper)
#   #B8860B amber           -> AppTheme.secondary (verdigris)
#   #0F0F0F / #1A1A1A obsidian -> AppTheme.background/surface
#   #E57373                 -> AppTheme.error (oxblood)
#   Kernel #FDFDFD / #A5A6AC -> textPrimary/textSecondary
# Medallion dışı brass/hardcode bulunursa AppThemeColors'tan değil, marka tokenına çevrilir.
```
> **Kural:** `app_theme.dart` + `app_theme_colors.dart` + `brand_medallion*.dart` dışında hiçbir sert renk kalmaz. Her birini implement günü belge-tabanlı map'le; tek tek review edilir.

- [ ] **Step 3: Test**

Run: `cd frontend && flutter test --no-pub`
Expected: suite yeşil; renk assert'i olmadığından token swap otomatik geçer.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib frontend/test
git commit -m "feat(brand): ekran renklerini marka tokenlarına süpürdü (radar bw, sert hex temiz)"
```

---

### Task 6: In-app loading — CircularProgressIndicator → Medallion(animate:true)

**Files:**
- Modify: `frontend/lib/main.dart:59-70` (initAsync loading dalı) ve `:40-44` (settings loading dalı)

**Interfaces:**
- Consumes: `Medallion` (Task 3)
- Produces: Markalı loading; spinner (loop) kaldırılır.

- [ ] **Step 1: Failing test** — `widget_test.dart` (mevcut; loading'de `CircularProgressIndicator` bekleyen assert varsa güncelle):

```dart
// loading dalında CircularProgressIndicator yerine Medallion beklenir.
expect(find.byType(Medallion), findsWidgets);
expect(find.byType(CircularProgressIndicator), findsNothing);
```

- [ ] **Step 2: Implement** — iki loading dalında `CircularProgressIndicator(color: AppTheme.primary)` → `Medallion(size: 96, level: MedallionLevel.master, animate: true)` (koyu zeminde). Metin (`'Veritabanı hazırlanıyor...'`) korunur, altına `SizedBox` boşluğu.

> Native `launch_background.xml` statik kalır (char zemin + medallion drawable — Task 7). Flutter loading frame = sweep animasyonunun TEK yeri (loop spinner yasak).

- [ ] **Step 3: Test**

Run: `cd frontend && flutter test --no-pub`
Expected: suite yeşil; `Medallion` loading'de render olur, loop yok.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/main.dart frontend/test/widget_test.dart
git commit -m "feat(brand): loading spinner -> markalı medallion sweep (loop yasak)"
```

---

### Task 7: Native launch_background + launcher ikonu

**Files:**
- Modify: `frontend/android/app/src/main/res/drawable*/launch_background.xml` (2 dosya)
- Modify: `frontend/pubspec.yaml` (`flutter_launcher_icons` dev dep + config)
- Create: `frontend/assets/launcher/icon.png` (1024px, icon kademesi medallion)
- Generated: `frontend/android/app/src/main/res/mipmap-*` ikonları

**Interfaces:**
- Consumes: amblem geometrisi (Task 2'den), palet tokenları
- Produces: markalı native splash + markalı launcher ikonu.

- [ ] **Step 1: pubspec dev_deps + config**

```yaml
dev_dependencies:
  flutter_launcher_icons: ^0.14.1

flutter_launcher_icons:
  android: true
  ios: false            # iOS hedef değil (Android-only bu üründe)
  image_path: "assets/launcher/icon.png"
  adaptive_icon_background: "#1A120B"   # caskChar
  adaptive_icon_foreground: "assets/launcher/icon_foreground.png"
  min_sdk_android: 21
```

- [ ] **Step 2: icon.png üret** (implement günü) — icon kademesi (7-gen + mühür halkası + ibre, köşe pontos), brass rim/needle + copper web/dot, char zemin. 1024x1024. `assets/launcher/icon.png` + `icon_foreground.png` (802x802 safe zone içinde medallion).

> Launcher ikonu statik PNG — CustomPainter launcher'a giremez. Geometri Task 2'deki `outer7`'den; isim/renk token taşımaz. Render'ı bir kez SVG→PNG ile çıkarılır (harici tool veya Flutter snapshot script).

- [ ] **Step 3: launch_background.xml** — iki dosyayı da:

```xml
<item android:drawable="@color/launch_cask_char" />
<item>
  <bitmap
    android:gravity="center"
    android:src="@drawable/launch_medallion" />
</item>
```
Buna ek: `values/colors.xml` `launch_cask_char` = `#1A120B`; `drawable/launch_medallion.xml` (vektör) — 7-gen + halka, copper web + brass rim. Vektör Android drawable olarak Task 2 geometrisinden elle çizilir (ya da statik png `mipmap-*` yeniden kullanılır).

- [ ] **Step 4: Generate + test**

```bash
cd frontend && flutter pub get && dart run flutter_launcher_icons
flutter build apk --debug   # ikon/splash paketleme doğrula (timestamp)
```
> Tam APK build uzun olabilir; hedef ikon+varsayılan paketleme. `flutter test --no-pub` ile grafik-free.

- [ ] **Step 5: Commit**

```bash
git add frontend/pubspec.yaml frontend/assets/launcher frontend/android/app/src/main/res
git commit -m "feat(brand): markali launcher ikonu + native launch_background"
```

---

### Task 8: Brass/gold/csv gate'leri (repo-check)

**Files:**
- Modify: `scripts/gates/check_repo_state.ps1`

**Interfaces:**
- Consumes: marka renk sabitleri
- Produces: `just repo-check` brass/gold/csv regresyon bekçisi.

- [ ] **Step 1: Gate script'e ekle** (anti-regresyon):

```powershell
Write-Host "`n=== Brand token gates ==="
$gold = git grep -l "0xFFD4AF37\|0xFFd4af37" -- frontend/lib 2>$null
if ($gold) { Write-Host "GOLD KALINTISI (YASAK):" -ForegroundColor Red; $gold }
else { Write-Host "gold: temiz" -ForegroundColor Green }

$brassFiles = git grep -l "0xFFC9A227\|0xFFc9a227" -- frontend/lib 2>$null
if ($brassFiles) {
    $bad = $brassFiles | Where-Object { $_ -notlike "*app_theme_colors.dart" }
    if ($bad) { Write-Host "BRASS UI'DA (YASAK — yalniz app_theme_colors)" -ForegroundColor Red; $bad }
    else { Write-Host "brass: yalniz app_theme_colors.dart (OK)" -ForegroundColor Green }
} else { Write-Host "brass: hic referans yok (OK)" -ForegroundColor Yellow }

$csv = git grep -l "- assets/data" -- frontend/pubspec.yaml 2>$null
if ($csv) { Write-Host "CSV ASSET LEAK (YASAK)" -ForegroundColor Red; $csv }
else { Write-Host "csv: temiz" -ForegroundColor Green }
```

- [ ] **Step 2: Test gate**

```bash
just repo-check
```
Expected: gold temiz, brass OK (yalnız app_theme_colors), csv temiz. Risk row çıktısı korunur.

- [ ] **Step 3: Commit**

```bash
git add scripts/gates/check_repo_state.ps1
git commit -m "chore(gates): brand token anti-regresyon (gold/brass/csv) repo-check'e"
```

---

### Task 9: Full suite + nodata probe

**Files:** (yalnız doğrulama)

- [ ] **Step 1: Full suite**

```bash
# iOS ephemeral fix gerekiyorsa (skill):
chmod -R u+w frontend/ios/Flutter/ephemeral/Packages/ 2>/dev/null
rm -rf frontend/ios/Flutter/ephemeral/Packages/.packages 2>/dev/null
cd frontend && flutter test --no-pub
```
Expected: tüm suite yeşil.

- [ ] **Step 2: Web nodata probe** (anti-scrape kanıtı)

```bash
cd frontend && flutter build web --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.example.com
find build/web -name "*.csv"        # BOŞ
grep -rliE "whisky_database_merged_max|flavor_profiles\.csv|scotchgit_flavor" build/web   # BOŞ
```
Expected: CSV yok; AssetManifest'te `.csv` yok. Font `.ttf` build/web içinde görünebilir — beklenen (asset, veri değil).

- [ ] **Step 3: flutter analyze**

```bash
cd frontend && flutter analyze --no-pub
```
Expected: 0 error (pre-existing unused_import uyarıları dokunulmaz).

---

## Self-Review (plan yazımı sonrası)

- **Spec coverage:** Tüm 5 karar + her tasarım bölümü bir task'a karşılık geliyor: palet(T1), medallion(T2), widget/anim(T3), tema+font(T4), ekran sweep(T5), loading(T6), launcher/splash(T7), gate(T8), full verify(T9). Splash iki katmanı (native Task 7, in-app Task 6) ayrıştırıldı. Brass kuralı T1'de token yalıtımı + T4/T8 gate ile.
- **Placeholder scan:** Font `.ttf` dosyalarının indirilmesi, icon.png üretimi, sert hex taranması "implement günü" işi olarak işaretlendi (gerçek dosya binary/indirme gerektirdiğinden plan metnine gömülemez — doğru). Tüm Dart kodları tam.
- **Type consistency:** `MedallionPalette`, `MedallionLevel`, `MedallionPainter`, `Medallion`, `kMasterDarkPalette`, `kMasterLightPalette`, `AppThemeColors` tutarlı tek isimlendirme; Task 1-3 arasında yukarı bağımlı, Task 4-9 aşağı tüketir.
- **Font aile isimleri:** `Fraunces`, `SourceSerif4`, `CourierPrime`, `Inter` — pubspec family ile `TextStyle(fontFamily:)` aynı (kritik: boşluksuz family adı). Test Task 4'te `'SourceSerif4'` (kaynak dokümanındaki "Source Serif 4" display adı değil — font asset family anahtarı).

## Execution Handoff

Plan kaydedildi: `docs/superpowers/plans/2026-08-09-brand-identity-implementation.md`

**İcra durumu: BEKLE.** Kullanıcı, mevcut sosyal/X queue işi + branch kararını (main'den yeni brand branch'i önerisi) bitirene kadar kod tasks'leri AÇIK DEĞİL. İcra başladığında iki seçenek:

**1. Subagent-Driven (önerilen)** — görev başına taze subagent, aralarında review
**2. Inline Execution** — bu session'da `executing-plans`, checkpoint'lerle

Hangisi istersen, "GO" verdiğinde.
