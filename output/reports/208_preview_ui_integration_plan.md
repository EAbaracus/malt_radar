# Preview UI Integration Plan

## 1. Objectives
Plan the UI integration of the `scotchgit` flavor profiles as a Preview/QA feature without disrupting the production user experience or altering production database state.

## 2. Feature Flagging
We will introduce a debug flag to toggle the preview features:
- `AppConfig.enableFlavorPreviewMode` (default: `false`)
- In production builds (`kReleaseMode`), this flag will be hardcoded/forced to `false`.

## 3. Normal Mode Behavior (`enableFlavorPreviewMode == false`)
- **Radar Chart**: Displays only `production` or `whiskeymapper` profiles based on priority.
- **Similar Flavor Provider**: Calculates distances using only `production` and `whiskeymapper` profiles.
- **UI**: No badges, no visual changes. `scotchgit` data is completely ignored.

## 4. QA / Debug Mode Behavior (`enableFlavorPreviewMode == true`)
### A. Radar Chart (`FlavorRadarChart`)
- If a `scotchgit` profile exists but a higher-priority profile (`production` or `whiskeymapper`) also exists (Conflict):
  - The chart displays the higher-priority profile.
  - A subtle badge is added near the chart: **"Preview Source Available (Lower Priority)"**.
  - *Future Enhancement*: Tap badge to toggle/compare the shadow `scotchgit` profile on the chart.
- If ONLY a `scotchgit` profile exists (No Conflict):
  - The chart displays the `scotchgit` profile.
  - A prominent badge is added: **"QA Preview: ScotchGit"**.

### B. Similar Flavor Provider (`similar_flavor_provider.dart`)
- The provider must be updated to resolve the "effective flavor profile" dynamically based on the feature flag.
- In QA mode, whiskies with ONLY a `scotchgit` profile will suddenly participate in Euclidean distance calculations and appear in "Similar Whiskies" lists.
- *Risk*: This might yield strange recommendations if the AI hallucinated. This is acceptable for QA mode to test the quality of the extraction.

## 5. Architectural Changes Required (Next Stages)
1. **Database Schema**: Ensure the app reads from `flavor_profiles` (1-to-many) or create a dedicated `preview_flavor_profile` column in `whiskies` to avoid complex client-side joins for every similarity calculation.
2. **Provider Updates**: Update Riverpod providers to inject `enableFlavorPreviewMode` into the repository layer.
3. **Normalizer**: `FlavorProfileNormalizer` already supports the standard 7-axis format that `scotchgit` will use. No changes needed there.

## 6. Security & Risks
- **Risk**: Leaking untested AI flavor profiles to users.
- **Mitigation**: The feature flag must be strictly tied to debug/internal builds. The CI/CD pipeline should ensure release builds strip preview code or force the flag to false.
