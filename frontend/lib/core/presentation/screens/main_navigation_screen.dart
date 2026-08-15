import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/analytics/analytics_service.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/whisky/presentation/screens/home_screen.dart';
import 'package:malt_radar/features/lists/presentation/screens/lists_screen.dart';
import 'package:malt_radar/features/whisky/presentation/screens/settings_screen.dart';

class MainNavigationScreen extends ConsumerStatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  ConsumerState<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends ConsumerState<MainNavigationScreen> {
  int _selectedIndex = 0;

  final List<Widget> _screens = [
    const HomeScreen(),
    const ListsScreen(),
    const SettingsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _trackPageView(0);
    });
  }

  void _trackPageView(int tabIndex) {
    final analytics = ref.read(analyticsServiceProvider);
    final sessionId = ref.read(sessionIdProvider);
    final tabPaths = ['/', '/lists', '/settings'];
    analytics.trackPageView(
      urlPath: tabPaths[tabIndex],
      pageTitle: tabIndex == 0 ? 'Explore' : tabIndex == 1 ? 'Lists' : 'Settings',
      sessionId: sessionId,
    );
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    return Scaffold(
      body: Stack(
        children: [
          IndexedStack(
            index: _selectedIndex,
            children: _screens,
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: ClipRect(
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                child: Container(
                  decoration: BoxDecoration(
                    color: AppTheme.background.withValues(alpha: 0.8),
                    border: Border(
                      top: BorderSide(
                        color: AppThemeColors.parchment.withValues(alpha: 0.1),
                        width: 1,
                      ),
                    ),
                  ),
                  child: SafeArea(
                    child: NavigationBar(
                      selectedIndex: _selectedIndex,
                      onDestinationSelected: (index) {
                        setState(() {
                          _selectedIndex = index;
                        });
                        _trackPageView(index);
                      },
                      destinations: [
                        NavigationDestination(
                          icon: const Icon(Icons.explore_outlined),
                          selectedIcon: const Icon(Icons.explore),
                          label: tr('explore'),
                        ),
                        NavigationDestination(
                          icon: const Icon(Icons.bookmark_outline),
                          selectedIcon: const Icon(Icons.bookmark),
                          label: tr('lists'),
                        ),
                        NavigationDestination(
                          icon: const Icon(Icons.settings_outlined),
                          selectedIcon: const Icon(Icons.settings),
                          label: tr('settings'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
