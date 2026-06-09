import 'package:drift/drift.dart';
import 'package:malt_radar/core/database/database.dart';

class Whisky {
  final int id; // local database auto-increment ID
  final String? externalId; // ID from external API (e.g. wh-lagavulin-16)
  final String name;
  final String? country;
  final String? region;
  final String? category;
  final int? age;
  final double? abv;
  final String? caskType;
  final double? defaultPrice;
  final String? currency;
  final String? sourceName;
  final String? sourceUrl;
  final String? fetchedAt;
  final List<String> tastingNotes;
  final List<String> companionSuggestions;
  
  // User specific attributes
  final int personalScore; // absolute score (0-100)
  final String personalNotes;
  final bool isFavorite;

  Whisky({
    required this.id,
    this.externalId,
    required this.name,
    this.country,
    this.region,
    this.category,
    this.age,
    this.abv,
    this.caskType,
    this.defaultPrice,
    this.currency,
    this.sourceName,
    this.sourceUrl,
    this.fetchedAt,
    required this.tastingNotes,
    required this.companionSuggestions,
    required this.personalScore,
    required this.personalNotes,
    required this.isFavorite,
  });

  Whisky copyWith({
    int? id,
    String? externalId,
    String? name,
    String? country,
    String? region,
    String? category,
    int? age,
    double? abv,
    String? caskType,
    double? defaultPrice,
    String? currency,
    String? sourceName,
    String? sourceUrl,
    String? fetchedAt,
    List<String>? tastingNotes,
    List<String>? companionSuggestions,
    int? personalScore,
    String? personalNotes,
    bool? isFavorite,
  }) {
    return Whisky(
      id: id ?? this.id,
      externalId: externalId ?? this.externalId,
      name: name ?? this.name,
      country: country ?? this.country,
      region: region ?? this.region,
      category: category ?? this.category,
      age: age ?? this.age,
      abv: abv ?? this.abv,
      caskType: caskType ?? this.caskType,
      defaultPrice: defaultPrice ?? this.defaultPrice,
      currency: currency ?? this.currency,
      sourceName: sourceName ?? this.sourceName,
      sourceUrl: sourceUrl ?? this.sourceUrl,
      fetchedAt: fetchedAt ?? this.fetchedAt,
      tastingNotes: tastingNotes ?? this.tastingNotes,
      companionSuggestions: companionSuggestions ?? this.companionSuggestions,
      personalScore: personalScore ?? this.personalScore,
      personalNotes: personalNotes ?? this.personalNotes,
      isFavorite: isFavorite ?? this.isFavorite,
    );
  }

  // Convert from Database entities
  factory Whisky.fromEntities({
    required WhiskyEntity whisky,
    int? score,
    String? notes,
    bool? favorite,
  }) {
    return Whisky(
      id: whisky.id,
      externalId: whisky.externalId,
      name: whisky.name,
      country: whisky.country,
      region: whisky.region,
      category: whisky.category,
      age: whisky.age,
      abv: whisky.abv,
      caskType: whisky.caskType,
      defaultPrice: whisky.defaultPrice,
      currency: whisky.currency,
      sourceName: whisky.sourceName,
      sourceUrl: whisky.sourceUrl,
      fetchedAt: whisky.fetchedAt,
      tastingNotes: whisky.tastingNotes.isEmpty 
          ? [] 
          : whisky.tastingNotes.split(',').map((e) => e.trim()).toList(),
      companionSuggestions: whisky.companionSuggestions.isEmpty
          ? []
          : whisky.companionSuggestions.split(',').map((e) => e.trim()).toList(),
      personalScore: score ?? 0,
      personalNotes: notes ?? '',
      isFavorite: favorite ?? false,
    );
  }

  // Convert from backend REST API Map (JSON)
  factory Whisky.fromMap(Map<String, dynamic> map) {
    return Whisky(
      id: 0, // Unsaved
      externalId: map['external_id'] as String?,
      name: map['name'] as String,
      country: map['country'] as String?,
      region: map['region'] as String?,
      category: map['category'] as String?,
      age: map['age'] as int?,
      abv: (map['abv'] as num?)?.toDouble(),
      caskType: map['cask_type'] as String?,
      defaultPrice: (map['default_price'] as num?)?.toDouble(),
      currency: map['currency'] as String?,
      sourceName: map['source_name'] as String?,
      sourceUrl: map['source_url'] as String?,
      fetchedAt: map['fetched_at'] as String? ?? DateTime.now().toIso8601String(),
      tastingNotes: (map['tasting_notes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      companionSuggestions: (map['companion_suggestions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      personalScore: 0,
      personalNotes: '',
      isFavorite: false,
    );
  }

  // Convert to companion for database inserts
  WhiskiesCompanion toCompanion() {
    return WhiskiesCompanion.insert(
      id: id == 0 ? const Value.absent() : Value(id),
      externalId: Value(externalId),
      name: name,
      country: Value(country),
      region: Value(region),
      category: Value(category),
      age: Value(age),
      abv: Value(abv),
      caskType: Value(caskType),
      defaultPrice: Value(defaultPrice),
      currency: Value(currency),
      sourceName: Value(sourceName),
      sourceUrl: Value(sourceUrl),
      fetchedAt: Value(fetchedAt),
      tastingNotes: Value(tastingNotes.join(',')),
      companionSuggestions: Value(companionSuggestions.join(',')),
    );
  }
}
