import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../whisky/domain/models/whisky.dart';

final similarFlavorWhiskiesProvider = FutureProvider.family<List<Whisky>, int>((ref, targetWhiskyId) async {
  // Minimal compile-safe placeholder since the local Drift DB was removed
  // and we do not want to build a new backend-driven recommendation engine yet.
  return [];
});
