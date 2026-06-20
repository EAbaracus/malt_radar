import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/config/app_config.dart';
import 'package:malt_radar/features/flavor/domain/flavor_source_priority.dart';

void main() {
  group('AppConfig', () {
    test('enableFlavorPreviewMode default is false', () {
      expect(AppConfig.enableFlavorPreviewMode, isFalse, 
        reason: 'Preview mode must be false by default for production safety');
    });
  });

  group('FlavorSourcePriority', () {
    test('getEffectiveSource returns null for empty list', () {
      expect(FlavorSourcePriority.getEffectiveSource([]), isNull);
    });

    test('getEffectiveSource returns production when alone', () {
      expect(
        FlavorSourcePriority.getEffectiveSource([FlavorSource.production]),
        FlavorSource.production,
      );
    });

    test('getEffectiveSource prioritizes production over whiskeymapper', () {
      expect(
        FlavorSourcePriority.getEffectiveSource([
          FlavorSource.whiskeymapper,
          FlavorSource.production,
        ]),
        FlavorSource.production,
      );
    });

    test('getEffectiveSource ignores scotchgit when preview mode is disabled (default)', () {
      expect(
        FlavorSourcePriority.getEffectiveSource([
          FlavorSource.scotchgit,
        ]),
        isNull,
      );
      
      expect(
        FlavorSourcePriority.getEffectiveSource([
          FlavorSource.scotchgit,
          FlavorSource.whiskeymapper,
        ]),
        FlavorSource.whiskeymapper,
      );
    });

    test('getEffectiveSource returns scotchgit when alone and preview mode enabled (no conflict)', () {
      expect(
        FlavorSourcePriority.getEffectiveSource(
          [FlavorSource.scotchgit],
          previewModeEnabled: true,
        ),
        FlavorSource.scotchgit,
      );
    });

    test('getEffectiveSource prioritizes production/wm over scotchgit even in preview mode (conflict)', () {
      // Conflict with production
      expect(
        FlavorSourcePriority.getEffectiveSource(
          [FlavorSource.scotchgit, FlavorSource.production],
          previewModeEnabled: true,
        ),
        FlavorSource.production,
      );

      // Conflict with whiskeymapper
      expect(
        FlavorSourcePriority.getEffectiveSource(
          [FlavorSource.scotchgit, FlavorSource.whiskeymapper],
          previewModeEnabled: true,
        ),
        FlavorSource.whiskeymapper,
      );
    });

    test('fromString parses correctly', () {
      expect(FlavorSourcePriority.fromString('production'), FlavorSource.production);
      expect(FlavorSourcePriority.fromString('existing'), FlavorSource.production);
      expect(FlavorSourcePriority.fromString('whiskeymapper'), FlavorSource.whiskeymapper);
      expect(FlavorSourcePriority.fromString('scotchgit'), FlavorSource.scotchgit);
      expect(FlavorSourcePriority.fromString('random_ai'), FlavorSource.unverified);
      expect(FlavorSourcePriority.fromString(null), FlavorSource.production); // Legacy default
      expect(FlavorSourcePriority.fromString(''), FlavorSource.production); // Legacy default
    });
  });
}
