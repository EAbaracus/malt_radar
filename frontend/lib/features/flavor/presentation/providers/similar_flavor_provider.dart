import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/flavor_profile_normalizer.dart';
import '../../../whisky/domain/models/whisky.dart';
import '../../../whisky/presentation/controllers/whisky_providers.dart';

final similarFlavorWhiskiesProvider = FutureProvider.family<List<Whisky>, int>((ref, targetWhiskyId) async {
  final db = ref.watch(appDatabaseProvider);
  
  // 1. Fetch target whisky
  final target = await (db.select(db.whiskies)..where((t) => t.id.equals(targetWhiskyId))).getSingleOrNull();
  if (target == null || target.flavorProfile == null || target.flavorProfile!.isEmpty) {
    debugPrint('SimilarFlavor: Target whisky $targetWhiskyId has no flavor profile.');
    return [];
  }

  // 2. Fetch all other whiskies that have a flavorProfile
  final allOthers = await (db.select(db.whiskies)..where((t) => t.id.isNotValue(targetWhiskyId))).get();
  
  if (allOthers.isEmpty) return [];

  // Parse target profile
  Map<String, double> targetProfile = {};
  try {
    targetProfile = normalizeFlavorProfileJson(target.flavorProfile!);
  } catch (e) {
    debugPrint('SimilarFlavor: Failed to parse target profile: $e');
    return [];
  }

  // 3. Calculate Euclidean distance for others
  List<Map<String, dynamic>> scoredList = [];
  
  for (final other in allOthers) {
    if (other.flavorProfile == null || other.flavorProfile!.isEmpty) continue;
    
    try {
      final parsed = normalizeFlavorProfileJson(other.flavorProfile!);
      double sumSquares = 0.0;
      bool hasData = false;
      
      parsed.forEach((k, v) {
        if (targetProfile.containsKey(k)) {
          final diff = targetProfile[k]! - v;
          sumSquares += diff * diff;
          hasData = true;
        }
      });
      
      if (hasData) {
        scoredList.add({
          'whisky': Whisky.fromEntities(whisky: other),
          'distance': sumSquares,
        });
      }
    } catch (e) {
      // Ignore parse errors for individual whiskies
    }
  }

  // 4. Sort by shortest distance
  scoredList.sort((a, b) => (a['distance'] as double).compareTo(b['distance'] as double));

  // 5. Return top 5
  return scoredList.take(5).map((e) => e['whisky'] as Whisky).toList();
});
