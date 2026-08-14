# Foreign Key Report
Total Violations: 0
New Violations (introduced by promotion): 0

**CRITICAL SCHEMA ERROR:** foreign key mismatch - "price_history" referencing "whiskies"
This prevents `PRAGMA foreign_key_check` from completing. This is a pre-existing schema defect where `price_history` references `whiskies` which lacks a UNIQUE index on `whisky_id`.

## Details
