import 'package:drift/drift.dart';
import 'package:drift/web.dart';

/// Opens a Drift database connection for web platform.
/// Uses in-memory sql.js backed storage via drift's built-in WebDatabase.
QueryExecutor openConnection() {
  return WebDatabase.withStorage(
    DriftWebStorage.indexedDb('malt_radar_v2'),
  );
}
