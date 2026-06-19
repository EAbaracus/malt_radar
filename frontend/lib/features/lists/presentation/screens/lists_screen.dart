import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/lists/presentation/controllers/user_lists_providers.dart';
import 'package:malt_radar/features/lists/domain/models/user_list.dart';
import 'package:malt_radar/features/lists/presentation/screens/list_detail_screen.dart';

class ListsScreen extends ConsumerStatefulWidget {
  const ListsScreen({super.key});

  @override
  ConsumerState<ListsScreen> createState() => _ListsScreenState();
}

class _ListsScreenState extends ConsumerState<ListsScreen> {
  @override
  void initState() {
    super.initState();
    // Ensure default system lists exist
    Future.microtask(() async {
      await ref.read(userListsRepositoryProvider).ensureDefaultLists();
    });
  }

  String _getLocalizedListName(UserList list, String Function(String) tr) {
    if (list.isSystemDefault && list.defaultType != null) {
      return tr(list.defaultType!.toLowerCase());
    }
    return list.name;
  }

  String _getItemCountString(int count, String Function(String) tr) {
    final isEn = tr('whisky_library') == 'Whisky library';
    if (isEn) {
      return count == 1 ? '1 whisky' : '$count whiskies';
    } else {
      return '$count viski';
    }
  }

  void _showCreateListDialog(BuildContext context, String Function(String) tr) {
    final formKey = GlobalKey<FormState>();
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: AppTheme.surfaceElevated,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(tr('create_list'), style: const TextStyle(color: AppTheme.primary)),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: nameController,
                  style: const TextStyle(color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    labelText: tr('list_name'),
                    hintText: tr('list_name'),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return tr('list_name');
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: descriptionController,
                  style: const TextStyle(color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    labelText: tr('list_description'),
                    hintText: tr('list_description'),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () async {
                if (!formKey.currentState!.validate()) return;
                final name = nameController.text.trim();
                final desc = descriptionController.text.trim();

                final repo = ref.read(userListsRepositoryProvider);
                await repo.createList(name, description: desc.isEmpty ? null : desc);

                if (context.mounted) {
                  Navigator.pop(context);
                }
              },
              child: Text(tr('save')),
            ),
          ],
        );
      },
    );
  }

  void _showEditListDialog(BuildContext context, UserList list, String Function(String) tr) {
    final formKey = GlobalKey<FormState>();
    final nameController = TextEditingController(text: list.name);
    final descriptionController = TextEditingController(text: list.description ?? '');

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: AppTheme.surfaceElevated,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(tr('edit_list'), style: const TextStyle(color: AppTheme.primary)),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: nameController,
                  style: const TextStyle(color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    labelText: tr('list_name'),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return tr('list_name');
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: descriptionController,
                  style: const TextStyle(color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    labelText: tr('list_description'),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () async {
                if (!formKey.currentState!.validate()) return;
                final name = nameController.text.trim();
                final desc = descriptionController.text.trim();

                final repo = ref.read(userListsRepositoryProvider);
                await repo.updateList(list.id, name: name, description: desc.isEmpty ? null : desc);

                if (context.mounted) {
                  Navigator.pop(context);
                }
              },
              child: Text(tr('save')),
            ),
          ],
        );
      },
    );
  }

  void _showDeleteConfirmationDialog(BuildContext context, UserList list, String Function(String) tr) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: AppTheme.surfaceElevated,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(tr('delete_list'), style: const TextStyle(color: AppTheme.error)),
          content: Text(
            tr('whisky_library') == 'Whisky library'
                ? 'Are you sure you want to delete "${list.name}"? Whiskies inside the list will not be deleted.'
                : '"${list.name}" listesini silmek istediğinize emin misiniz? Viskileriniz silinmeyecektir.',
            style: const TextStyle(color: AppTheme.textPrimary),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () async {
                final repo = ref.read(userListsRepositoryProvider);
                await repo.deleteList(list.id);
                if (context.mounted) {
                  Navigator.pop(context);
                }
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
              child: Text(tr('delete_list'), style: const TextStyle(color: AppTheme.textPrimary)),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    final listsAsync = ref.watch(watchUserListsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(tr('my_lists')),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateListDialog(context, tr),
        backgroundColor: AppTheme.primary,
        child: const Icon(Icons.add, color: AppTheme.background),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.8),
            radius: 1.5,
            colors: [
              Color(0xFF1E1E2C),
              AppTheme.background,
              Color(0xFF040406),
            ],
          ),
        ),
        child: SafeArea(
          child: listsAsync.when(
            data: (lists) {
              if (lists.isEmpty) {
                return Center(
                  child: Text(
                    tr('no_lists_found'),
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 16),
                  ),
                );
              }

              return ListView.separated(
                padding: const EdgeInsets.all(24),
                itemCount: lists.length,
                separatorBuilder: (context, index) => const SizedBox(height: 16),
                itemBuilder: (context, index) {
                  final list = lists[index];
                  final displayName = _getLocalizedListName(list, tr);
                  final itemText = _getItemCountString(list.itemCount, tr);

                  return Container(
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceElevated.withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                    ),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                      leading: CircleAvatar(
                        backgroundColor: AppTheme.primary.withValues(alpha: 0.1),
                        child: Icon(
                          list.isSystemDefault ? Icons.folder_special : Icons.folder,
                          color: AppTheme.primary,
                        ),
                      ),
                      title: Text(
                        displayName,
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (list.description != null && list.description!.isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              list.description!,
                              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                          const SizedBox(height: 6),
                          Text(
                            itemText,
                            style: const TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      trailing: list.isSystemDefault
                          ? null
                          : PopupMenuButton<String>(
                              icon: const Icon(Icons.more_vert, color: AppTheme.textSecondary),
                              onSelected: (value) {
                                if (value == 'edit') {
                                  _showEditListDialog(context, list, tr);
                                } else if (value == 'delete') {
                                  _showDeleteConfirmationDialog(context, list, tr);
                                }
                              },
                              itemBuilder: (context) => [
                                PopupMenuItem(
                                  value: 'edit',
                                  child: Row(
                                    children: [
                                      const Icon(Icons.edit, size: 20, color: AppTheme.textPrimary),
                                      const SizedBox(width: 8),
                                      Text(tr('edit_list')),
                                    ],
                                  ),
                                ),
                                PopupMenuItem(
                                  value: 'delete',
                                  child: Row(
                                    children: [
                                      const Icon(Icons.delete, size: 20, color: AppTheme.error),
                                      const SizedBox(width: 8),
                                      Text(tr('delete_list'), style: const TextStyle(color: AppTheme.error)),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ListDetailScreen(
                              listId: list.id,
                              listName: displayName,
                            ),
                          ),
                        );
                      },
                    ),
                  );
                },
              );
            },
            loading: () => const Center(
              child: CircularProgressIndicator(color: AppTheme.primary),
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
