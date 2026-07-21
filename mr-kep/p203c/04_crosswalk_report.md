# P203C — 04 Crosswalk Report (P203B)

Crosswalk resolved: **1/15** | Unknown (→ review queue): **14/15**
P203B crosswalk used exactly as-is (read-only on knowledge.db). No fabricated canonicals; unknowns preserved in review.

## Resolved example
- `Undisclosed Speyside` → `D1902` (Speyside region entity) via substring scan.
## Finding
- Low resolution is a downstream effect of broken `whisky_raw_name` (section titles rarely contain a distillery token).
- When a real distillery token IS present (e.g. 'Glenmorangie', 'Ardbeg', 'Amrut' from the earlier diagnostic run), the crosswalk resolves correctly (conf 1.0).
- Once `discover_listing` is fixed and real review titles flow, crosswalk resolution will rise substantially.
