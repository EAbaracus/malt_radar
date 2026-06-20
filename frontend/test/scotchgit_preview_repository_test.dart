import 'package:flutter_test/flutter_test.dart';
import 'package:malt_radar/core/config/app_config.dart';
import 'package:malt_radar/features/flavor/data/scotchgit_preview_profile.dart';
import 'package:malt_radar/features/flavor/data/scotchgit_preview_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ScotchGitPreviewRepository', () {
    late ScotchGitPreviewRepository repository;

    setUp(() {
      repository = ScotchGitPreviewRepository();
    });

    test('getPreviewProfiles returns empty list when feature flag is disabled', () async {
      // Feature flag is false by default
      expect(AppConfig.enableFlavorPreviewMode, isFalse);
      
      final profiles = await repository.getPreviewProfiles();
      expect(profiles, isEmpty);
    });

    test('getPreviewForWhisky returns null when feature flag is disabled', () async {
      expect(AppConfig.enableFlavorPreviewMode, isFalse);
      
      final profile = await repository.getPreviewForWhisky('W000080');
      expect(profile, isNull);
    });

    test('Model getters evaluate correctly', () {
      final conflictProfile = ScotchGitPreviewProfile(
        whiskyId: 'W1',
        productName: 'Test1',
        conflictStatus: 'existing_production_profile',
        priority: 'lower_than_existing_or_whiskeymapper',
        flavorProfileJson: '{}',
      );

      expect(conflictProfile.hasConflict, isTrue);
      expect(conflictProfile.isPreviewCandidate, isFalse);

      final noConflictProfile = ScotchGitPreviewProfile(
        whiskyId: 'W2',
        productName: 'Test2',
        conflictStatus: 'no_conflict',
        priority: 'preview_whitelist',
        flavorProfileJson: '{}',
      );

      expect(noConflictProfile.hasConflict, isFalse);
      expect(noConflictProfile.isPreviewCandidate, isTrue);
    });
  });
}
