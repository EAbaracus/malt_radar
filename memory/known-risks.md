# Known Risks

1. **PDF Extraction Inaccuracies:** Flavor extraction scoring regex patterns may fail or yield noisy values on non-standard layout books.
2. **Normalization Edge Cases:** Variant whisky names, single-cask expressions, and complex ABV/Age notations may bypass resolvers.
3. **Cross-Page Mapping Failures:** Fuzzy matching matching score thresholds might cause false matches or fail to link genuine duplicates.
4. **Missing Source Attribution:** Untraceable historical notes may enter production unless strict lineage validations are enforced.
