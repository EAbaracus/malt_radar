# Forensic Audit Report

## Row Counts
- **Whiskies:** 3557 -> 3876 (+319)
- **Distilleries:** 1913 -> 2131 (+218)
- **Brands:** 0 -> 250 (+250)

## ID Integrity
- **Whiskies:** Contiguous (Gaps: 0), Duplicates: 0
- **Distilleries:** Contiguous (Gaps: 0), Duplicates: 0
- **Brands:** Contiguous (Gaps: 0), Duplicates: 0

### Brand Audit
The promotion script initialized `brand_id` incrementally.
Prior to this sprint, `SELECT COUNT(*) FROM brands` was 0.
The promotion inserted 250 rows.
The current `brands` table contains 250 rows.
The minimum inserted ID was 1, and the maximum is 250.
There are 0 duplicate IDs.
The ID sequence is contiguous (Gaps: 0).
**Conclusion:** The report stating "Brands assigned 1 to 250" is CORRECT. The `brands` table was completely empty prior to this transaction. The IDs did not collide, they were cleanly generated using AUTOINCREMENT-style logic.


## Status
GO WITH PRE-EXISTING WARNINGS
