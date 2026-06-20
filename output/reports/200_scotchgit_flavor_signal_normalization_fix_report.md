# ScotchGit Flavor Signal Normalization Fix Report

## Scope

- Keyword and region signals are now tracked separately.
- Per-whisky max normalization is applied only to keyword scores.
- Region-only rows are capped at max axis <= 0.25 and signal_strength <= 0.75.
- Keyword plus region rows cap total region contribution to 20% of final score.

## Validation

- region_only rows: 431
- region_only max axis: 0.25
- region_only max signal_strength: 0.7499
- production.db changed: NO

## Named Checks

- Macallan 12 Double Cask | basis=region_only | sweet=0.12 | fruity=0.12 | warning=region_only_low_confidence
- Aberlour A'bunadh | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh Batch #63 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh batch #37 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh batch #40 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh batch #49 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh batch #55 | basis=keyword_plus_region | sherry=1.0 | fruity=0.097 | warning=keyword_signal_present
- Aberlour A'bunadh Batch #53 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh batch #39 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh batch #44 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
- Aberlour A'bunadh Batch #52 | basis=keyword_plus_region | sherry=1.0 | fruity=0.0952 | warning=keyword_signal_present
