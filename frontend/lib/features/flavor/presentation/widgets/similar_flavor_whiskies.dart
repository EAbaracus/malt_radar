import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_theme.dart';
import '../providers/similar_flavor_provider.dart';
import '../../whisky/domain/models/whisky.dart';

class SimilarFlavorWhiskies extends ConsumerWidget {
  final int whiskyId;
  final Function(Whisky) onWhiskyTap;

  const SimilarFlavorWhiskies({
    super.key, 
    required this.whiskyId,
    required this.onWhiskyTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final similarAsync = ref.watch(similarFlavorWhiskiesProvider(whiskyId));

    return similarAsync.when(
      data: (whiskies) {
        if (whiskies.isEmpty) return const SizedBox();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              child: Text(
                'Benzer Lezzetler',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
            ),
            SizedBox(
              height: 140,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: whiskies.length,
                itemBuilder: (context, index) {
                  final w = whiskies[index];
                  return GestureDetector(
                    onTap: () => onWhiskyTap(w),
                    child: Container(
                      width: 120,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceLight,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white10),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.liquor, size: 40, color: AppTheme.accent),
                          const SizedBox(height: 8),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                            child: Text(
                              w.name,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                              textAlign: TextAlign.center,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (w.globalScore != null) ...[
                            const SizedBox(height: 4),
                            Text(
                              w.globalScore!.toStringAsFixed(1),
                              style: const TextStyle(
                                color: AppTheme.secondary,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ]
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        );
      },
      loading: () => const Center(child: CircularProgressIndicator(strokeWidth: 2)),
      error: (_, __) => const SizedBox(),
    );
  }
}
