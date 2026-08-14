# Architectural Decisions

## Decision 1: Price Exclusion
- **Date:** 2026-07-08
- **Decision:** Price is excluded from recommendation engine and user-facing profiles.
- **Reason:** Recommendation quality and flavor profiles must remain independent from market fluctuations.
- **Status:** Accepted

## Decision 2: Restricted Flavor Axes
- **Date:** 2026-07-08
- **Decision:** Flavor system is restricted to 7 core axes (smoky, peaty, fruity, sweet, spicy, maritime, sherry).
- **Reason:** Ensures model explainability, stability, and historical consistency.
- **Status:** Accepted

## Decision 3: Weighted Average Profiling
- **Date:** 2026-07-05
- **Decision:** Multi-book/multi-evidence flavor vectors are merged using a Weighted Average model.
- **Reason:** Protects existing profiles from being overwritten, allowing cumulative multi-source refinement.
- **Status:** Accepted
