import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/features/whisky/presentation/controllers/whisky_providers.dart';
import 'package:malt_radar/features/lists/domain/repositories/user_lists_repository.dart';
import 'package:malt_radar/features/lists/data/repositories/user_lists_repository_impl.dart';
import 'package:malt_radar/features/lists/domain/models/user_list.dart';
import 'package:malt_radar/features/lists/domain/models/user_list_item.dart';

// Repository Provider
final userListsRepositoryProvider = Provider<UserListsRepository>((ref) {
  final db = ref.watch(appDatabaseProvider);
  return UserListsRepositoryImpl(db);
});

// Watch All Lists
final watchUserListsProvider = StreamProvider<List<UserList>>((ref) {
  final repository = ref.watch(userListsRepositoryProvider);
  return repository.watchLists();
});

// Watch List Items
final watchUserListItemsProvider = StreamProvider.family<List<UserListItem>, int>((ref, listId) {
  final repository = ref.watch(userListsRepositoryProvider);
  return repository.watchListItems(listId);
});

// Future Get Lists for Whisky
final getListsForWhiskyProvider = FutureProvider.family<List<UserList>, int>((ref, whiskyId) {
  final repository = ref.watch(userListsRepositoryProvider);
  return repository.getListsForWhisky(whiskyId);
});

// Check if whisky in specific list
final isWhiskyInListProvider = FutureProvider.family<bool, ({int listId, int whiskyId})>((ref, args) {
  final repository = ref.watch(userListsRepositoryProvider);
  return repository.isWhiskyInList(args.listId, args.whiskyId);
});
