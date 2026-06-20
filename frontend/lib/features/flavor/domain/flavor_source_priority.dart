enum FlavorSource {
  production,
  whiskeymapper,
  scotchgit,
  unverified,
}

class FlavorSourcePriority {
  static const Map<FlavorSource, int> _priorityMap = {
    FlavorSource.production: 1,
    FlavorSource.whiskeymapper: 2,
    FlavorSource.scotchgit: 3,
    FlavorSource.unverified: 99,
  };

  /// Returns the highest priority source from a list of available sources.
  /// Returns null if no valid source is found.
  ///
  /// If [previewModeEnabled] is false, preview sources like scotchgit are ignored.
  static FlavorSource? getEffectiveSource(
    List<FlavorSource> availableSources, {
    bool previewModeEnabled = false,
  }) {
    if (availableSources.isEmpty) return null;

    final filtered = availableSources.where((s) {
      if (s == FlavorSource.unverified) return false;
      if (!previewModeEnabled && s == FlavorSource.scotchgit) return false;
      return true;
    }).toList();

    if (filtered.isEmpty) return null;

    filtered.sort((a, b) => _priorityMap[a]!.compareTo(_priorityMap[b]!));
    return filtered.first;
  }

  /// Parses a string source into the enum.
  static FlavorSource fromString(String? source) {
    if (source == null || source.isEmpty) {
      return FlavorSource.production; // Default assume production for legacy records
    }
    switch (source.toLowerCase()) {
      case 'production':
      case 'existing':
        return FlavorSource.production;
      case 'whiskeymapper':
        return FlavorSource.whiskeymapper;
      case 'scotchgit':
        return FlavorSource.scotchgit;
      default:
        return FlavorSource.unverified;
    }
  }
}
