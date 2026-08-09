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
    mapped['type'] = dbWhisky['type'];
    mapped['style_similarity'] = dbWhisky['style_similarity'];

    if (tastingNotes != null) {
      mapped['tasting_notes'] = tastingNotes
          .map((e) => e['note_text']?.toString())
          .where((e) => e != null)
          .cast<String>()
          .toList();
    } else {
      mapped['tasting_notes'] = <String>[];
    }

    // flavor_profile: prefer the explicit (detail) payload; otherwise fall
    // back to the raw catalogue row's string (list items carry their own
    // flavor_profile JSON, which the radar UI needs to render).
    final rawProfile = flavorProfile ?? dbWhisky['flavor_profile'];
    mapped['flavor_profile'] = rawProfile;
    if (rawProfile is Map<String, dynamic>) {
      mapped['flavor_vector'] = rawProfile['flavor_vector_json'];
      mapped['flavor_tags'] = rawProfile['flavor_tags_json'];
    }

    return mapped;
  }
}
