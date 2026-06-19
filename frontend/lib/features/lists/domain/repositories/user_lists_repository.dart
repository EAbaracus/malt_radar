import '../models/user_list.dart';
import '../models/user_list_item.dart';

abstract class UserListsRepository {
  /// Create a new custom list
  Future<int> createList(String name, {String? description});
  
  /// Update an existing list metadata
  Future<void> updateList(int id, {String? name, String? description, int? sortOrder});
  
  /// Delete a list and all its item mappings
  Future<void> deleteList(int id);
  
  /// Reactive stream of all lists (with computed item counts)
  Stream<List<UserList>> watchLists();
  
  /// Reactive stream of items in a specific list, joined with Whisky models
  Stream<List<UserListItem>> watchListItems(int listId);
  
  /// Add a whisky to a list
  Future<void> addWhiskyToList(int listId, int whiskyId, {String? note});
  
  /// Remove a whisky from a list
  Future<void> removeWhiskyFromList(int listId, int whiskyId);
  
  /// Check if a whisky is in a specific list
  Future<bool> isWhiskyInList(int listId, int whiskyId);
  
  /// Get all lists that contain this specific whisky
  Future<List<UserList>> getListsForWhisky(int whiskyId);
  
  /// Ensure default system lists (Favorites, Wishlist, Tried, Collection) exist
  Future<void> ensureDefaultLists();

  /// Get all lists (non-reactive)
  Future<List<UserList>> getLists();

  /// Get items in a specific list (non-reactive)
  Future<List<UserListItem>> getListItems(int listId);

  /// Toggle a whisky in a list (adds if not present, removes if present)
  Future<void> toggleWhiskyInList(int listId, int whiskyId);
}
