import 'package:drift/drift.dart';
import 'package:malt_radar/core/database/database.dart';

class UserList {
  final int id;
  final String name;
  final String? description;
  final String? defaultType;
  final int sortOrder;
  final DateTime createdAt;
  final DateTime updatedAt;
  final bool isSystemDefault;
  final int itemCount; // Computed, not persisted directly in table

  UserList({
    required this.id,
    required this.name,
    this.description,
    this.defaultType,
    required this.sortOrder,
    required this.createdAt,
    required this.updatedAt,
    required this.isSystemDefault,
    this.itemCount = 0,
  });

  UserList copyWith({
    int? id,
    String? name,
    String? description,
    String? defaultType,
    int? sortOrder,
    DateTime? createdAt,
    DateTime? updatedAt,
    bool? isSystemDefault,
    int? itemCount,
  }) {
    return UserList(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      defaultType: defaultType ?? this.defaultType,
      sortOrder: sortOrder ?? this.sortOrder,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      isSystemDefault: isSystemDefault ?? this.isSystemDefault,
      itemCount: itemCount ?? this.itemCount,
    );
  }

  factory UserList.fromEntity(UserListEntity entity, {int itemCount = 0}) {
    return UserList(
      id: entity.id,
      name: entity.name,
      description: entity.description,
      defaultType: entity.defaultType,
      sortOrder: entity.sortOrder,
      createdAt: DateTime.parse(entity.createdAt),
      updatedAt: DateTime.parse(entity.updatedAt),
      isSystemDefault: entity.isSystemDefault,
      itemCount: itemCount,
    );
  }

  UserListsCompanion toCompanion() {
    return UserListsCompanion.insert(
      id: id == 0 ? const Value.absent() : Value(id),
      name: name,
      description: Value(description),
      defaultType: Value(defaultType),
      sortOrder: Value(sortOrder),
      createdAt: createdAt.toIso8601String(),
      updatedAt: updatedAt.toIso8601String(),
      isSystemDefault: Value(isSystemDefault),
    );
  }
}
