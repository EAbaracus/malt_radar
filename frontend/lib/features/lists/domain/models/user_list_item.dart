import 'package:drift/drift.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/domain/models/whisky.dart';

class UserListItem {
  final int id;
  final int listId;
  final int whiskyId;
  final String? note;
  final int sortOrder;
  final DateTime createdAt;
  final Whisky? whisky; // Joined for display

  UserListItem({
    required this.id,
    required this.listId,
    required this.whiskyId,
    this.note,
    required this.sortOrder,
    required this.createdAt,
    this.whisky,
  });

  UserListItem copyWith({
    int? id,
    int? listId,
    int? whiskyId,
    String? note,
    int? sortOrder,
    DateTime? createdAt,
    Whisky? whisky,
  }) {
    return UserListItem(
      id: id ?? this.id,
      listId: listId ?? this.listId,
      whiskyId: whiskyId ?? this.whiskyId,
      note: note ?? this.note,
      sortOrder: sortOrder ?? this.sortOrder,
      createdAt: createdAt ?? this.createdAt,
      whisky: whisky ?? this.whisky,
    );
  }

  factory UserListItem.fromEntity(UserListItemEntity entity, {Whisky? whisky}) {
    return UserListItem(
      id: entity.id,
      listId: entity.listId,
      whiskyId: entity.whiskyId,
      note: entity.note,
      sortOrder: entity.sortOrder,
      createdAt: DateTime.parse(entity.createdAt),
      whisky: whisky,
    );
  }

  UserListItemsCompanion toCompanion() {
    return UserListItemsCompanion.insert(
      id: id == 0 ? const Value.absent() : Value(id),
      listId: listId,
      whiskyId: whiskyId,
      note: Value(note),
      sortOrder: Value(sortOrder),
      createdAt: createdAt.toIso8601String(),
    );
  }
}
