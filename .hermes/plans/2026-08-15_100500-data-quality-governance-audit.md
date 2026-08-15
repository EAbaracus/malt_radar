# Comprehensive Production Data Quality & Governance Audit Plan

> **For Hermes:** Use subagent-driven-development or executing-plans skill to implement this audit and remediation plan task-by-task.

**Goal:** Conduct a comprehensive, evidence-based production database audit to identify, isolate, and remediate synthetic templates, empty SMWS entries, and duplicate vectors in `output/import/production.db` strictly following Malt Radar Canonical Governance rules (Insert-Only evidence, PromotionGate for DB mutations, Human GO required).

**Architecture:** A 4-phase audit and governance pipeline. Phase 1 conducts a read-only audit to catalog all synthetic/empty records; Phase 2 builds a dry-run quarantine package and KEP-compliant promotion patch; Phase 3 executes the PromotionGate dry-run with exact pre/post SHA256 projections; Phase 4 presents the closure report for human GO.

**Tech Stack:** Python 3.11, SQLite3 (Read-Only URI), KEP Review Runtime (`promotion_engine.py`, `PromotionGate`).

---

### Task 1: Execute Read-Only Forensic Data Audit

**Objective:** Audit `output/import/production.db` to identify all synthetic templates (`spicy: 60, smoky_peaty: 60`), empty SMWS entries (790 rows with 0 tasting notes), and duplicated flavor vectors without modifying any database or code files.

**Files:**
- Create: `scripts/audit/audit_production_data_quality_v1.py`
- Test: Run script against `output/import/production.db` read-only.

**Step 1: Write audit script**

```python
import sqlite3, json, hashlib
from pathlib import Path

DB_PATH = Path("output/import/production.db")

def run_audit():
    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
    cur = conn.cursor()
    
    # 1. Audit Synthetic Templates (e.g., spicy=60, smoky_peaty=60)
    synthetic_query = """
        SELECT w.whisky_id, w.name, fp.flavor_profile, fe.source
        FROM whiskies w
        JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        LEFT JOIN flavor_evidence fe ON w.whisky_id = fe.whisky_id
        WHERE fp.flavor_profile LIKE '%"spicy": 60%' AND fp.flavor_profile LIKE '%"smoky_peaty": 60%'
    """
    synthetic_rows = cur.execute(synthetic_query).fetchall()
    
    # 2. Audit Empty SMWS Entries
    smws_query = """
        SELECT w.whisky_id, w.name, fp.flavor_profile
        FROM whiskies w
        LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        WHERE (LOWER(w.name) LIKE '%smws%' OR LOWER(COALESCE(w.brand,'')) LIKE '%smws%')
    """
    smws_rows = cur.execute(smws_query).fetchall()
    
    conn.close()
    
    report = {
        "synthetic_template_count": len(synthetic_rows),
        "smws_count": len(smws_rows),
        "synthetic_samples": synthetic_rows[:5],
    }
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_audit()
```

**Step 2: Run read-only audit script**

Run: `python scripts/audit/audit_production_data_quality_v1.py`
Expected: Output JSON with exact counts of synthetic templates and SMWS entries.

---

### Task 2: Build KEP Quarantine & Re-Crawl Staging Package

**Objective:** Package the 29 synthetic template whiskies and 790 empty SMWS entries into a staging quarantine package for re-crawling / re-extraction, ensuring zero direct DB deletion per KEP Rules 3 & 4.

**Files:**
- Create: `mr-kep/audit/quarantine/data_quality_quarantine_v1.jsonl`
- Create: `scripts/audit/build_quarantine_staging_package.py`

**Step 1: Write staging package builder**

```python
import sqlite3, json
from pathlib import Path

DB_PATH = Path("output/import/production.db")
OUT_PATH = Path("mr-kep/audit/quarantine/data_quality_quarantine_v1.jsonl")

def build_package():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
    cur = conn.cursor()
    
    # Select synthetic template entries
    rows = cur.execute("""
        SELECT w.whisky_id, w.name, fp.flavor_profile
        FROM whiskies w
        JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        WHERE fp.flavor_profile LIKE '%"spicy": 60%' AND fp.flavor_profile LIKE '%"smoky_peaty": 60%'
    """).fetchall()
    
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            entry = {
                "whisky_id": r[0],
                "name": r[1],
                "current_profile": r[2],
                "quarantine_reason": "synthetic_webcrawl_round88_template",
                "action_required": "RE_CRAWL_PROSE_EXTRACTION"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    conn.close()
    print(f"Quarantine package written: {OUT_PATH} ({len(rows)} entries)")

if __name__ == "__main__":
    build_package()
```

**Step 2: Run package builder**

Run: `python scripts/audit/build_quarantine_staging_package.py`
Expected: File `mr-kep/audit/quarantine/data_quality_quarantine_v1.jsonl` created.

---

### Task 3: KEP PromotionGate Dry-Run Verification

**Objective:** Perform a KEP PromotionGate dry-run for the staging quarantine updates, verifying SHA256 projections and evidence immutability without mutating `output/import/production.db`.

**Files:**
- Create: `scripts/audit/dry_run_data_quality_quarantine_promotion.py`

**Step 1: Write dry-run script using KEP PromotionGate**

```python
import hashlib
from pathlib import Path
from kep_review_runtime.runtime.promotion_engine import PromotionGate

DB_PATH = Path("output/import/production.db")

def run_dry_run():
    pre_sha = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
    print(f"Pre-apply SHA256: {pre_sha}")
    
    gate = PromotionGate(db_path=str(DB_PATH))
    # Execute dry-run only
    report = gate.dry_run(batch_id="DATA_QUALITY_QUARANTINE_V1")
    
    post_sha = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
    assert pre_sha == post_sha, "CRITICAL: Dry-run mutated production.db!"
    print(f"Post-dry-run SHA256: {post_sha} (Unchanged)")

if __name__ == "__main__":
    run_dry_run()
```

**Step 2: Run PromotionGate dry-run**

Run: `python scripts/audit/dry_run_data_quality_quarantine_promotion.py`
Expected: Output showing dry-run predictions and matching pre/post SHA256.

---

### Task 4: Present Closure Report & Await Human GO

**Objective:** Present the complete dry-run closure report with pre/post SHA256, affected row counts, and quarantine plan to the human operator for explicit GO authorization per KEP Governance Rule 6.

**Files:**
- Create: `output/reports/data_quality_audit_closure_report_v1.md`

**Step 1: Generate closure report**

```markdown
# Data Quality & Governance Audit Closure Report

**Phase:** DATA_QUALITY_QUARANTINE_V1
**Mode:** DRY-RUN ONLY
**Pre-Apply SHA256:** `CBFFD16B29433C983BB113B2E9A9F186DD94C1FF9DC6F5F1B13D97F084386177`
**Target Records Identified:**
- Synthetic Template Profiles: 29
- Empty SMWS Entries: 790
- Re-Crawl Action Package: `mr-kep/audit/quarantine/data_quality_quarantine_v1.jsonl`

**Status:** Awaiting Human GO
```

---
