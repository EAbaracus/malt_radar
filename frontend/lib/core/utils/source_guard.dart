class SourceGuard {
  static const Set<String> forbiddenSourceFields = {
    'source_id',
    'source_name',
    'source_url',
    'source_system',
    'source_reference',
    'internal_source_url',
    'internal_source_id',
    'internal_audit_url',
  };

  static Map<String, dynamic> sanitizePublicItem(
    Map<String, dynamic> item, {
    bool isManual = false,
  }) {
    if (isManual) {
      return Map<String, dynamic>.from(item);
    }

    final sanitized = Map<String, dynamic>.from(item);

    for (final field in forbiddenSourceFields) {
      sanitized.remove(field);
    }

    return sanitized;
  }

  static List<Map<String, dynamic>> sanitizePublicList(
    List<Map<String, dynamic>> items, {
    bool isManual = false,
  }) {
    return items
        .map((item) => sanitizePublicItem(item, isManual: isManual))
        .toList();
  }

  static bool hasPublicSourceFields(Map<String, dynamic> item) {
    return forbiddenSourceFields.any(item.containsKey);
  }
}