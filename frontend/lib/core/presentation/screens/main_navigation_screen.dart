import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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
                    child: BottomNavigationBar(
                      backgroundColor: Colors.transparent,
                      elevation: 0,
                      selectedItemColor: AppTheme.primary,
                      unselectedItemColor: AppTheme.textMuted,
                      currentIndex: _selectedIndex,
                      onTap: (index) {
                        setState(() {
                          _selectedIndex = index;
                        });
                      },
                      items: [
                        BottomNavigationBarItem(
                          icon: const Icon(Icons.explore_outlined),
                          activeIcon: const Icon(Icons.explore),
                          label: tr('explore'),
                        ),
                        BottomNavigationBarItem(
                          icon: const Icon(Icons.bookmark_outline),
                          activeIcon: const Icon(Icons.bookmark),
                          label: tr('lists'),
                        ),
                        BottomNavigationBarItem(
                          icon: const Icon(Icons.settings_outlined),
                          activeIcon: const Icon(Icons.settings),
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
