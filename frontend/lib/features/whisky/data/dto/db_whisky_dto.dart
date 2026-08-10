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
    // Backend rows carry distillery_name (joined), not a `distillery` key.
    mapped['distillery'] = dbWhisky['distillery'] ?? dbWhisky['distillery_name'];
    // Backend schema uses `age` (not stated_age) and `meta_critic_score`
    // (not global_rating). Map both with fallbacks for resilience.
    mapped['age'] = dbWhisky['age'] ?? dbWhisky['stated_age'];
    mapped['abv'] = dbWhisky['abv'];
    mapped['cask_type'] = dbWhisky['cask_type'];
    mapped['default_price'] = dbWhisky['default_price'] ?? dbWhisky['retail_price'];
    mapped['currency'] = dbWhisky['currency'];
    mapped['source'] = dbWhisky['source'];
    mapped['url'] = dbWhisky['url'];
    mapped['global_score'] = dbWhisky['global_score'] ?? dbWhisky['meta_critic_score'] ?? dbWhisky['user_score'];
    mapped['type'] = dbWhisky['type'];
    mapped['style_similarity'] = dbWhisky['style_similarity'];

    // Use whisky_id as local id (hash to int)
    final whiskyId = dbWhisky['whisky_id']?.toString() ?? '';
    mapped['id'] = whiskyId.hashCode.abs() % 1000000;

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
