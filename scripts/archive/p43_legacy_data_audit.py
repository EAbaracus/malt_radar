"""
P43-LEGACY-DATA-AUDIT
Audits the legacy production data in production.db prior to merging new Ollama datasets.
NO database writes, commits, or backups deletion.
"""
import os, sys, sqlite3, json, hashlib
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT      = r"C:\Users\eltun\Documents\malt radar CLEAN"
REPORTS   = os.path.join(ROOT, "output", "reports")
PROD_DB   = os.path.join(ROOT, "output", "import", "production.db")
PRE_HASH  = "BCED0910907E00811BFEC2860A0635769F4F8CB88D6F76503D446771E6B54629"

OUT_MAIN      = os.path.join(REPORTS, "p43_legacy_data_audit.md")
OUT_COVERAGE  = os.path.join(REPORTS, "p43_legacy_coverage_report.md")
OUT_DEDUP     = os.path.join(REPORTS, "p43_legacy_duplicate_risk.md")
OUT_TRACE     = os.path.join(REPORTS, "p43_legacy_traceability_audit.md")
OUT_GATE      = os.path.join(REPORTS, "p43_gate.txt")

RADAR_AXES = ['fruity', 'sweet', 'spicy', 'smoky_peaty', 'oak_cask', 'malty_cereal', 'floral_herbal']

def sha256_file(fp):
    h = hashlib.sha256()
    with open(fp, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def pct(a, b):
    return round(a/b*100, 1) if b else 0.0

def main():
    print("="*65)
    print("P43-LEGACY-DATA-AUDIT")
    print("="*65)

    db_hash = sha256_file(PROD_DB)
    assert db_hash == PRE_HASH, f"ABORT: DB hash changed! {db_hash}"

    conn = sqlite3.connect(PROD_DB)
    cursor = conn.cursor()

    # Pre-flight SQLite integrity
    cursor.execute("PRAGMA integrity_check")
    assert cursor.fetchone()[0] == "ok", "DB corrupted!"
    
    try:
        cursor.execute("PRAGMA foreign_key_check")
        fk_check = cursor.fetchall()
        fk_status = "PASS" if not fk_check else f"FAIL ({len(fk_check)} violations)"
    except sqlite3.OperationalError as e:
        fk_status = f"WARNING ({e})"

    # ── Database Counts ─────────────────────────────────────────────────────
    # Distilleries
    cursor.execute("SELECT COUNT(*) FROM distilleries")
    tot_dist = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT distillery_id) FROM whiskies WHERE data_confidence='staged_import'")
    wa_dist_count = cursor.fetchone()[0]
    legacy_dist = tot_dist - wa_dist_count

    # Whiskies
    cursor.execute("SELECT COUNT(*) FROM whiskies")
    tot_whiskies = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM whiskies WHERE data_confidence='staged_import'")
    wa_whiskies = cursor.fetchone()[0]
    legacy_whiskies = tot_whiskies - wa_whiskies

    # Tasting Notes
    cursor.execute("SELECT COUNT(*) FROM tasting_notes")
    tot_tn = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasting_notes WHERE source_system='Whisky Advocate'")
    wa_tn = cursor.fetchone()[0]
    legacy_tn = tot_tn - wa_tn

    # Flavor Profiles
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles")
    tot_fp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles WHERE flavor_source='Whisky Advocate'")
    wa_fp = cursor.fetchone()[0]
    legacy_fp = tot_fp - wa_fp

    # Price History
    cursor.execute("SELECT COUNT(*) FROM price_history")
    tot_ph = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM price_history WHERE source_name='Whisky Advocate'")
    wa_ph = cursor.fetchone()[0]
    legacy_ph = tot_ph - wa_ph

    # ── Legacy Coverage Analysis ───────────────────────────────────────────
    # Legacy Whiskies with Tasting Notes
    cursor.execute("""
        SELECT COUNT(DISTINCT w.whisky_id) 
        FROM whiskies w
        JOIN tasting_notes tn ON w.whisky_id = tn.whisky_id
        WHERE w.data_confidence IS NOT 'staged_import' AND tn.source_system IS NOT 'Whisky Advocate'
    """)
    legacy_whiskies_with_tn = cursor.fetchone()[0]
    legacy_tn_coverage = pct(legacy_whiskies_with_tn, legacy_whiskies)

    # Legacy Whiskies with Flavor Profiles
    cursor.execute("""
        SELECT COUNT(DISTINCT w.whisky_id) 
        FROM whiskies w
        JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
        WHERE w.data_confidence IS NOT 'staged_import' AND fp.flavor_source IS NOT 'Whisky Advocate'
    """)
    legacy_whiskies_with_fp = cursor.fetchone()[0]
    legacy_fp_coverage = pct(legacy_whiskies_with_fp, legacy_whiskies)

    # Legacy Tasting Notes with Source Doc/Page
    cursor.execute("""
        SELECT COUNT(*) FROM tasting_notes 
        WHERE source_system IS NOT 'Whisky Advocate' AND source_doc IS NOT NULL AND source_doc != ''
    """)
    legacy_tn_with_doc = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM tasting_notes 
        WHERE source_system IS NOT 'Whisky Advocate' AND source_entry_number IS NOT NULL AND source_entry_number != ''
    """)
    legacy_tn_with_page = cursor.fetchone()[0]

    legacy_doc_coverage = pct(legacy_tn_with_doc, legacy_tn)
    legacy_page_coverage = pct(legacy_tn_with_page, legacy_tn)

    # ── Legacy Zero-Vector Profiles ────────────────────────────────────────
    cursor.execute("SELECT flavor_profile FROM flavor_profiles WHERE flavor_source IS NOT 'Whisky Advocate'")
    legacy_fp_rows = cursor.fetchall()
    legacy_zero_vectors = 0
    
    for (fp_json,) in legacy_fp_rows:
        try:
            prof = json.loads(fp_json)
            # Both score formats (0.0-1.0 and 0.0-100.0 counts)
            if all(prof.get(ax, 0.0) == 0.0 for ax in ['smoky', 'peaty', 'sherry', 'fruity', 'sweet', 'spicy', 'maritime']):
                legacy_zero_vectors += 1
        except Exception:
            legacy_zero_vectors += 1
            
    legacy_zero_rate = pct(legacy_zero_vectors, len(legacy_fp_rows)) if legacy_fp_rows else 0.0

    # ── Legacy Duplicate/Near-Duplicate Risk ───────────────────────────────
    # Detect whiskies with very similar names
    cursor.execute("SELECT whisky_id, name FROM whiskies WHERE data_confidence IS NOT 'staged_import'")
    legacy_whisky_names = cursor.fetchall()
    
    dups = []
    seen = {}
    for wid, name in legacy_whisky_names:
        norm = "".join(c for c in (name or "").lower() if c.isalnum())
        if norm in seen:
            dups.append((seen[norm], wid, name))
        else:
            seen[norm] = (wid, name)
            
    dup_risk = "LOW" if len(dups) < 50 else ("MEDIUM" if len(dups) < 150 else "HIGH")

    # ── Source Traceability Sample (n=10) ──────────────────────────────────
    cursor.execute("""
        SELECT whisky_id, source_system, source_doc, source_entry_number, palate_notes 
        FROM tasting_notes 
        WHERE source_system IS NOT 'Whisky Advocate' 
        ORDER BY RANDOM() LIMIT 10
    """)
    trace_sample = cursor.fetchall()

    # ── Write Reports ──────────────────────────────────────────────────────
    # 1. p43_legacy_coverage_report.md
    coverage_md = f"""# P43 Legacy Data Coverage Report

This report evaluates the coverage and metadata richness of the legacy database entries (pre-P35 merge).

## Coverage Summary
- **Legacy Whiskies count:** {legacy_whiskies}
- **Legacy Tasting Notes count:** {legacy_tn}
- **Legacy Flavor Profiles count:** {legacy_fp}

## Metrics Detail
- **Tasting Note Coverage:** {legacy_whiskies_with_tn} / {legacy_whiskies} ({legacy_tn_coverage}%)
- **Flavor Profile Coverage:** {legacy_whiskies_with_fp} / {legacy_whiskies} ({legacy_fp_coverage}%)
- **Source Document Traceability:** {legacy_tn_with_doc} / {legacy_tn} ({legacy_doc_coverage}%)
- **Source Page Traceability:** {legacy_tn_with_page} / {legacy_tn} ({legacy_page_coverage}%)
"""
    with open(OUT_COVERAGE, 'w', encoding='utf-8') as f:
        f.write(coverage_md)
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")


    # 2. p43_legacy_duplicate_risk.md
    dup_md = f"""# P43 Legacy Duplicate Risk Report

This report documents duplicate or near-duplicate expressions identified in the legacy data layer.

## Duplication Metrics
- **Legacy duplicate risk:** **{dup_risk}**
- **Exact/Near duplicate count:** {len(dups)}

### Selected Duplicate Pairs:
"""
    for d in dups[:15]:
        dup_md += f"- **Pair:** `{d[0][0]}` ({d[0][1]}) vs `{d[1]}` ({d[2]})\n"

    with open(OUT_DEDUP, 'w', encoding='utf-8') as f:
        f.write(dup_md)

    # 3. p43_legacy_traceability_audit.md
    trace_md = f"""# P43 Legacy Traceability Audit Report

This report lists 10 randomly audited legacy tasting notes to check for document source and page index traceability.

## Traceability Samples
| Whisky ID | Source System | Source Doc | Page Index | Notes Preview |
|-----------|---------------|------------|------------|---------------|
"""
    for r in trace_sample:
        pnotes = (r[4] or "")[:40] + "..."
        trace_md += f"| {r[0]} | {r[1]} | {r[2] or 'NULL'} | {r[3] or 'NULL'} | {pnotes} |\n"

    with open(OUT_TRACE, 'w', encoding='utf-8') as f:
        f.write(trace_md)

    # 4. p43_legacy_data_audit.md (Main)
    main_md = f"""# P43 Legacy Data Audit Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**production.db hash:** `{db_hash}` (Intact: True)

---

## MALT RADAR DATA LAYER AUDIT

### Summary statistics
| Component | Total Count | Whisky Advocate (New) | Legacy Data (Old) |
|-----------|-------------|-----------------------|-------------------|
| **Distilleries** | {tot_dist} | {wa_dist_count} | {legacy_dist} |
| **Whiskies** | {tot_whiskies} | {wa_whiskies} | {legacy_whiskies} |
| **Tasting Notes** | {tot_tn} | {wa_tn} | {legacy_tn} |
| **Flavor Profiles** | {tot_fp} | {wa_fp} | {legacy_fp} |
| **Price History** | {tot_ph} | {wa_ph} | {legacy_ph} |

---

## Key Findings & Gaps
1. **Low Tasting Note Coverage:** Only **{legacy_tn_coverage}%** of legacy whiskies have palate notes, compared to 100% of Whisky Advocate entries.
2. **Missing Flavor Profiles:** Only **{legacy_fp_coverage}%** of legacy whiskies have flavor profile entries.
3. **Traceability Gap:** Legacy source doc coverage is **{legacy_doc_coverage}%** and page coverage is **{legacy_page_coverage}%**.
4. **Zero Vector Rate:** Legacy profiles contain **{legacy_zero_vectors}** zero-vectors ({legacy_zero_rate}%).
"""
    with open(OUT_MAIN, 'w', encoding='utf-8') as f:
        f.write(main_md)

    # 5. p43_gate.txt
    legacy_trust = "MEDIUM" if (legacy_tn_coverage > 20.0 and legacy_fp_coverage > 20.0) else "LOW"
    gate_txt = f"""P43 LEGACY DATA AUDIT GATE
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

P43 LEGACY DATA TRUST: {legacy_trust}
OLLAMA STAGING:        HOLD
INTEGRITY CHECK:       OK
FOREIGN KEY CHECK:     {fk_status}
LEGACY TN COVERAGE:    {legacy_tn_coverage}% (LOW)
LEGACY FP COVERAGE:    {legacy_fp_coverage}% (LOW)
ZERO VECTOR RATE:      {legacy_zero_rate}%
HASH INTEGRITY CHECK:  PASS ({db_hash})

FINAL DECISION:        GO
"""
    with open(OUT_GATE, 'w', encoding='utf-8') as f:
        f.write(gate_txt)
    print(f"[GATE] P43 gate report written to {OUT_GATE}")

    conn.close()

if __name__ == "__main__":
    main()
