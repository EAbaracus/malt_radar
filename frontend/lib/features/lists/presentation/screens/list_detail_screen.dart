import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/lists/presentation/controllers/user_lists_providers.dart';
import 'package:malt_radar/features/whisky/presentation/screens/detail_screen.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/core/branding/brand_medallion_widget.dart';

class ListDetailScreen extends ConsumerWidget {
  final int listId;
  final String listName;

  const ListDetailScreen({
    super.key,
    required this.listId,
    required this.listName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = ref.watch(trProvider);
    final itemsAsync = ref.watch(watchUserListItemsProvider(listId));

    return Scaffold(
      appBar: AppBar(
        title: Text(listName),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.8),
            radius: 1.5,
            colors: [
              AppTheme.surfaceElevated,
              AppTheme.background,
              AppTheme.surface,
            ],
          ),
        ),
        child: SafeArea(
          child: itemsAsync.when(
            data: (items) {
              if (items.isEmpty) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.liquor_outlined,
                          size: 80,
                          color: AppTheme.textMuted.withValues(alpha: 0.5),
                        ),
                        const SizedBox(height: 24),
                        Text(
                          tr('empty_list'),
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                color: AppTheme.textPrimary,
                              ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Add some whiskies to see them here.',
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                        ),
                      ],
                    ),
                  ),
                );
              }

              return ListView.separated(
                padding: const EdgeInsets.all(24),
                itemCount: items.length,
                separatorBuilder: (context, index) => const SizedBox(height: 16),
                itemBuilder: (context, index) {
                  final item = items[index];
                  final whisky = item.whisky;

                  return Container(
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceElevated.withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppThemeColors.parchment.withValues(alpha: 0.05)),
                    ),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                      leading: CircleAvatar(
                        backgroundColor: AppTheme.primary.withValues(alpha: 0.1),
                        child: Text(
                          '${item.whiskyId}',
                          style: const TextStyle(color: AppTheme.primary, fontSize: 12),
                        ),
                      ),
                      title: Text(
                        whisky?.name ?? 'Whisky #${item.whiskyId}',
                        style: TextStyle(
                          color: whisky != null ? AppTheme.textPrimary : AppTheme.textMuted,
                          fontWeight: whisky != null ? FontWeight.bold : FontWeight.normal,
                          fontSize: 16,
                        ),
                      ),
                      subtitle: whisky != null
                          ? Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 4),
                                Text(
                                  [
                                    if (whisky.distillery != null) whisky.distillery,
                                    if (whisky.category != null) whisky.category!.replaceAll('SingleMalt-like', 'Single malt-like'),
                                  ].join(' • '),
                                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                                ),
                                if (whisky.globalScore != null && whisky.globalScore! > 0) ...[
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      const Icon(Icons.star, color: AppTheme.primary, size: 14),
                                      const SizedBox(width: 4),
                                      Text(
                                        '${whisky.globalScore!.toStringAsFixed(1)} ${tr('preview_global_score')}',
                                        style: const TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.bold),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            )
                          : Text(
                              'whisky_id: ${item.whiskyId}',
                              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                            ),
                      trailing: IconButton(
                        icon: const Icon(Icons.remove_circle_outline, color: AppTheme.error),
                        onPressed: () async {
                          final repo = ref.read(userListsRepositoryProvider);
                          await repo.removeWhiskyFromList(listId, item.whiskyId);

                          // Sync legacy favorites table if this is the favorites list
                          try {
                            final lists = await repo.getLists();
                            final currentList = lists.firstWhere((l) => l.id == listId);
                            if (currentList.defaultType == 'favorites') {
                              final whiskyRepo = ref.read(whiskyRepositoryProvider);
                              final w = await whiskyRepo.getWhiskyById(item.whiskyId);
                              if (w != null && w.isFavorite) {
                                await whiskyRepo.toggleFavorite(item.whiskyId);
                                ref.invalidate(whiskyDetailProvider(item.whiskyId));
                              }
                            }
                          } catch (_) {}

                          // Force update queries
                          ref.invalidate(getListsForWhiskyProvider(item.whiskyId));

                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(tr('lists_updated')),
                                backgroundColor: AppTheme.primary,
                                duration: const Duration(seconds: 1),
                                behavior: SnackBarBehavior.floating,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                              ),
                            );
                          }
                        },
                      ),
                      onTap: whisky != null
                          ? () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => DetailScreen(whiskyId: whisky.id),
                                ),
                              );
                            }
                          : null,
                    ),
                  );
                },
              );
            },
            loading: () => const Center(
              child: BrandSpinner(),
            ),
            error: (err, _) => Center(
              child: Text(
                '${tr('error')}: $err',
                style: const TextStyle(color: AppTheme.error),
              ),
            ),
          ),
        ),
      ),
    );
  }
}