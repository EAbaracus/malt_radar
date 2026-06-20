class ScotchGitPreviewProfile {
  final String whiskyId;
  final String productName;
  final String conflictStatus;
  final String priority;
  
  // Normalized 7-axis JSON map string
  final String flavorProfileJson;

  ScotchGitPreviewProfile({
    required this.whiskyId,
    required this.productName,
    required this.conflictStatus,
    required this.priority,
    required this.flavorProfileJson,
  });

  bool get isPreviewCandidate => priority == 'preview_whitelist' || conflictStatus == 'no_conflict';
  bool get hasConflict => conflictStatus != 'no_conflict';
}
