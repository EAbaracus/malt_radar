import 'dart:convert';
import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../whisky/domain/models/whisky.dart';
import '../../../whisky/presentation/controllers/whisky_providers.dart';

final similarFlavorWhiskiesProvider = FutureProvider.family<List<Whisky>, int>((ref, targetWhiskyId) async {
  final db = ref.read(databaseProvider);
  final allEntities = await db.select(db.whiskies).get();
  
  WhiskyEntity? targetEntity;
  for (var w in allEntities) {
    if (w.id == targetWhiskyId) {
      targetEntity = w;
      break;
    }
  }

  if (targetEntity == null || targetEntity.flavorProfile == null) return [];

  Map<String, dynamic> targetProfile;
  try {
    targetProfile = json.decode(targetEntity.flavorProfile!) as Map<String, dynamic>;
  } catch (_) {
    return [];
  }

  final categories = [
    'fruity', 'sweet', 'spicy', 'smoky_peaty', 'oak_cask', 'malty_cereal', 'floral_herbal'
  ];

  double cosineSimilarity(Map<String, dynamic> p1, Map<String, dynamic> p2) {
    double dotProduct = 0.0;
    double normA = 0.0;
    double normB = 0.0;
    for (var cat in categories) {
      final v1 = (p1[cat] as num?)?.toDouble() ?? 0.0;
      final v2 = (p2[cat] as num?)?.toDouble() ?? 0.0;
      dotProduct += v1 * v2;
      normA += v1 * v1;
      normB += v2 * v2;
    }
    if (normA == 0.0 || normB == 0.0) return 0.0;
    return dotProduct / (sqrt(normA) * sqrt(normB));
  }

  List<Map<String, dynamic>> scoredWhiskies = [];

  for (var w in allEntities) {
    if (w.id == targetWhiskyId) continue;
    if (w.flavorProfile == null) continue;

    try {
      final p = json.decode(w.flavorProfile!) as Map<String, dynamic>;
      double sim = cosineSimilarity(targetProfile, p);
      
      // The user requested 80% flavor sim, 10% type, 10% region. 
      // We will apply a simplified weighted similarity
      double finalScore = sim * 0.8;
      if (w.category != null && targetEntity.category != null && w.category == targetEntity.category) {
        finalScore += 0.1;
      }
      if (w.region != null && targetEntity.region != null && w.region == targetEntity.region) {
        finalScore += 0.1;
      }
      
      scoredWhiskies.add({
        'whisky': w,
        'score': finalScore,
      });
    } catch (_) {}
  }

  scoredWhiskies.sort((a, b) => (b['score'] as double).compareTo(a['score'] as double));

  // Return top 3
  return scoredWhiskies.take(3).map((e) {
    final entity = e['whisky'] as WhiskyEntity;
    return Whisky.fromEntities(whisky: entity);
  }).toList();
});
