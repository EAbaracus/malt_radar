class DbWhiskyMapper {
  static Map<String, dynamic> toLegacyMap(
    Map<String, dynamic> dbWhisky, {
    Map<String, dynamic>? flavorProfile,
    List<Map<String, dynamic>>? tastingNotes,
  }) {
    final mapped = <String, dynamic>{};
    mapped['external_id'] = dbWhisky['whisky_id']?.toString();
    mapped['name'] = dbWhisky['name'] ?? 'Unknown';
    mapped['country'] = dbWhisky['country'];
    mapped['region'] = dbWhisky['region'];
    mapped['category'] = dbWhisky['category'];
    mapped['distillery'] = dbWhisky['distillery'];
    mapped['age'] = dbWhisky['stated_age'];
    mapped['abv'] = dbWhisky['abv'];
    mapped['cask_type'] = dbWhisky['cask_type'];
    mapped['default_price'] = dbWhisky['retail_price'];
    mapped['currency'] = dbWhisky['currency'];
    mapped['source'] = dbWhisky['source'];
    mapped['url'] = dbWhisky['url'];
    mapped['global_score'] = dbWhisky['global_rating'];

    if (tastingNotes != null) {
      mapped['tasting_notes'] = tastingNotes
          .map((e) => e['note_text']?.toString())
          .where((e) => e != null)
          .cast<String>()
          .toList();
    } else {
      mapped['tasting_notes'] = <String>[];
    }

    mapped['flavor_profile'] = flavorProfile;
    if (flavorProfile != null) {
      mapped['flavor_vector'] = flavorProfile['flavor_vector_json'];
      mapped['flavor_tags'] = flavorProfile['flavor_tags_json'];
    }

    return mapped;
  }
}
