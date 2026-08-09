import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/core/theme/app_theme.dart';
import 'package:malt_radar/core/theme/app_theme_colors.dart';
import 'package:malt_radar/core/localization/localization_provider.dart';
import 'package:malt_radar/features/lists/presentation/controllers/user_lists_providers.dart';
import 'package:malt_radar/features/lists/domain/models/user_list.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';

class AddToListSheet extends ConsumerStatefulWidget {
  final int whiskyId;

  const AddToListSheet({super.key, required this.whiskyId});

  static Future<void> show(BuildContext context, int whiskyId) {
    return showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: AddToListSheet(whiskyId: whiskyId),
      ),
    );
  }

  @override
  ConsumerState<AddToListSheet> createState() => _AddToListSheetState();
}

class _AddToListSheetState extends ConsumerState<AddToListSheet> {
  final _newListNameController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isCreating = false;

  @override
  void initState() {
    super.initState();
    // Ensure default lists exist in the DB
    Future.microtask(() async {
      await ref.read(userListsRepositoryProvider).ensureDefaultLists();
    });
  }

  @override
  void dispose() {
    _newListNameController.dispose();
    super.dispose();
  }

  String _getLocalizedListName(UserList list, String Function(String) tr) {
    if (list.isSystemDefault && list.defaultType != null) {
      return tr(list.defaultType!.toLowerCase());
    }
    return list.name;
  }

  Future<void> _createNewList(String Function(String) tr) async {
    if (!_formKey.currentState!.validate()) return;
    
    final name = _newListNameController.text.trim();
    setState(() {
      _isCreating = true;
    });

    try {
      final repo = ref.read(userListsRepositoryProvider);
      await repo.createList(name);
      _newListNameController.clear();
      
      if (mounted) {
        FocusScope.of(context).unfocus();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(tr('lists_updated')),
            backgroundColor: AppTheme.primary,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${tr('error')}: $e'),
            backgroundColor: AppTheme.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCreating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final tr = ref.watch(trProvider);
    final listsAsync = ref.watch(watchUserListsProvider);
    final selectedListsAsync = ref.watch(getListsForWhiskyProvider(widget.whiskyId));

    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Handle Bar
            Center(
              child: Container(
                width: 48,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: AppTheme.textMuted.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  tr('add_to_lists'),
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: AppTheme.primary,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: AppTheme.textSecondary),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Create New List Form
            Form(
              key: _formKey,
              child: Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _newListNameController,
                      style: const TextStyle(color: AppTheme.textPrimary),
                      decoration: InputDecoration(
                        hintText: tr('create_new_list'),
                        hintStyle: const TextStyle(color: AppTheme.textMuted),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return tr('enter_list_name');
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  _isCreating
                      ? const SizedBox(
                          width: 48,
                          height: 48,
                          child: Padding(
                            padding: EdgeInsets.all(12),
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: AppTheme.primary,
                            ),
                          ),
                        )
                      : ElevatedButton(
                          onPressed: () => _createNewList(tr),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            minimumSize: const Size(48, 48),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                          ),
                          child: const Icon(Icons.add, color: AppTheme.background),
                        ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Lists List
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.of(context).size.height * 0.4,
              ),
              child: listsAsync.when(
                data: (lists) {
                  if (lists.isEmpty) {
                    return Center(
                      child: Text(
                        tr('no_lists_found'),
                        style: const TextStyle(color: AppTheme.textSecondary),
                      ),
                    );
                  }

                  return selectedListsAsync.when(
                    data: (selectedLists) {
                      final selectedIds = selectedLists.map((l) => l.id).toSet();

                      return ListView.separated(
                        shrinkWrap: true,
                        itemCount: lists.length,
                        separatorBuilder: (context, index) => const SizedBox(height: 8),
                        itemBuilder: (context, index) {
                          final list = lists[index];
                          final isSelected = selectedIds.contains(list.id);

                          return Container(
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceElevated.withValues(alpha: 0.3),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: isSelected 
                                    ? AppTheme.primary.withValues(alpha: 0.3)
                                    : AppThemeColors.parchment.withValues(alpha: 0.05),
                              ),
                            ),
                            child: CheckboxListTile(
                              title: Text(
                                _getLocalizedListName(list, tr),
                                style: TextStyle(
                                  color: isSelected ? AppTheme.primary : AppTheme.textPrimary,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                ),
                              ),
                              subtitle: list.description != null && list.description!.isNotEmpty
                                  ? Text(list.description!, style: const TextStyle(color: AppTheme.textMuted))
                                  : null,
                              value: isSelected,
                              activeColor: AppTheme.primary,
                              checkColor: AppTheme.background,
                              controlAffinity: ListTileControlAffinity.trailing,
                              onChanged: (bool? checked) async {
                                if (checked == null) return;

                                final listRepo = ref.read(userListsRepositoryProvider);
                                if (checked) {
                                  await listRepo.addWhiskyToList(list.id, widget.whiskyId);
                                  
                                  // Sync with legacy favorites table if Favorites list is checked
                                  if (list.defaultType == 'favorites') {
                                    final whiskyRepo = ref.read(whiskyRepositoryProvider);
                                    final whisky = await whiskyRepo.getWhiskyById(widget.whiskyId);
                                    if (whisky != null && !whisky.isFavorite) {
                                      await whiskyRepo.toggleFavorite(widget.whiskyId);
                                      ref.invalidate(whiskyDetailProvider(widget.whiskyId));
                                    }
                                  }
                                } else {
                                  await listRepo.removeWhiskyFromList(list.id, widget.whiskyId);
                                  
                                  // Sync with legacy favorites table if Favorites list is unchecked
                                  if (list.defaultType == 'favorites') {
                                    final whiskyRepo = ref.read(whiskyRepositoryProvider);
                                    final whisky = await whiskyRepo.getWhiskyById(widget.whiskyId);
                                    if (whisky != null && whisky.isFavorite) {
                                      await whiskyRepo.toggleFavorite(widget.whiskyId);
                                      ref.invalidate(whiskyDetailProvider(widget.whiskyId));
                                    }
                                  }
                                }

                                // Refresh the lists for this whisky
                                ref.invalidate(getListsForWhiskyProvider(widget.whiskyId));

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
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}
