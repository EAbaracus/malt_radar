import 'package:flutter/material.dart';
import 'brand_medallion.dart';
import '../theme/app_theme_colors.dart';

/// Markalı medallion widget'ı.
/// - default statik (ticker yok, pumpAndSettle güvenli).
/// - animate:true → tek sefer sweep (0→410°→360°), sonra sabit.
///   LOOP YASAK (marka kuralı: ibre döndürülemez).
/// - spin:true → sürekli dönen ibre (dönen logo / loading göstergesi);
///   heptagon sabit kalır, marka okunur. Loading yüzeylerinde CPI yerine.
/// - reduced-motion'da animasyon kapanır.
class Medallion extends StatefulWidget {
  const Medallion({
    super.key,
    this.size = 48,
    this.level = MedallionLevel.icon,
    this.palette,
    this.animate = false,
    this.spin = false,
  });

  final double size;
  final MedallionLevel level;
  final MedallionPalette? palette;
  final bool animate;
  /// Infinite rotation (loading indicator): the needle keeps turning while the
  /// static heptagon stays put. Prefer `spin` over `animate` for loading
  /// surfaces that must keep rotating.
  final bool spin;

  @override
  State<Medallion> createState() => _MedallionState();
}

class _MedallionState extends State<Medallion>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  Animation<double>? _rotation;
  bool _done = false;
  bool _started = false;

  @override
  void initState() {
    super.initState();
    // Ticker yalnızca animate/spin isteniyorsa kurulur; default'da unbounded (ticker yok).
    _controller = (widget.animate || widget.spin)
        ? AnimationController(
            vsync: this,
            duration: const Duration(milliseconds: 2400),
          )
        : AnimationController.unbounded(vsync: this);

    if (widget.animate) {
      _rotation = TweenSequence<double>([
        TweenSequenceItem(
          tween: Tween(begin: 0.0, end: _deg2rad(410.0))
              .chain(CurveTween(curve: Curves.easeOutCubic)),
          weight: 72,
        ),
        TweenSequenceItem(
          tween: Tween(begin: _deg2rad(410.0), end: _deg2rad(360.0)),
          weight: 28,
        ),
      ]).animate(_controller);
      _controller.addStatusListener((status) {
        if (status == AnimationStatus.completed) {
          setState(() => _done = true);
        }
      });
    } else if (widget.spin) {
      // Continuous rotation for the loading needle: full 2π over 2.4s, linear.
      _rotation = Tween(begin: 0.0, end: _deg2rad(360.0))
          .chain(CurveTween(curve: Curves.linear))
          .animate(_controller);
      _controller.addStatusListener((status) {
        if (status == AnimationStatus.completed) {
          _controller.repeat();
        }
      });
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // MediaQuery erişimi initState'te güvenilmez → burada yap.
    if ((widget.animate || widget.spin) && !_started) {
      final reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
      _started = true;
      if (reduce) return; // reduced-motion: animasyon başlatma (sweep veya spin kapalı)
      _controller.forward();
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
        final rot = _done ? _deg2rad(360.0) : (_rotation?.value ?? 0.0);
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

/// Markalı loading göstergesi — dönen medallion ibresi.
/// `CircularProgressIndicator` yerine loading yüzeylerinde kullanılır;
/// heptagon sabit kalır, ibre sürekli döner (marka okunur).
class BrandSpinner extends StatelessWidget {
  const BrandSpinner({super.key, this.size = 20, this.level = MedallionLevel.micro});

  final double size;
  final MedallionLevel level;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Medallion(
        size: size,
        level: level,
        spin: true,
      ),
    );
  }
}
