#!/usr/bin/env python
"""
P52 - Prepare the 141 "current operating Scotch Whisky distilleries (Sept 2022)"
source list for the Malt Radar database.

READ-ONLY / STAGING phase (no production.db mutation).
Produces:
  output/import/distilleries_2022/staging_distilleries_2022.csv  (DB-ready rows)
  output/import/distilleries_2022/cross_reference.csv            (match results)
  output/import/distilleries_2022/evaluation_report.md           (report)

Source: list-of-current-operating-scotch-whisky-distilleries-sept-2022.pdf
"""
import sqlite3, re, os, csv, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_TXT = os.path.join(ROOT, "_tmp_pdf_distilleries_2022.txt")
DB = os.path.join(ROOT, "output", "import", "production.db")
OUTDIR = os.path.join(ROOT, "output", "import", "distilleries_2022")
os.makedirs(OUTDIR, exist_ok=True)

SOURCE_TITLE = "List of current operating Scotch Whisky distilleries (September 2022)"
SOURCE_FILE = "list-of-current-operating-scotch-whisky-distilleries-sept-2022.pdf"

# ---- Scotch region classification (derived, SWA 6-region model) ----
# region values mirror existing DB taxonomy: Speyside, Highland, Islay,
# Campbeltown, Lowland, Islands.
REGION = {
    1:"Islay",2:"Speyside",3:"Highland",4:"Speyside",5:"Islands",6:"Lowland",
    7:"Speyside",8:"Lowland",9:"Highland",10:"Highland",11:"Islay",12:"Highland",
    13:"Lowland",14:"Speyside",15:"Speyside",16:"Highland",17:"Speyside",18:"Speyside",
    19:"Speyside",20:"Highland",21:"Speyside",22:"Speyside",23:"Speyside",24:"Lowland",
    25:"Highland",26:"Lowland",27:"Lowland",28:"Islay",29:"Speyside",30:"Highland",
    31:"Islay",32:"Islay",33:"Highland",34:"Speyside",35:"Lowland",36:"Islay",
    37:"Speyside",38:"Lowland",39:"Highland",40:"Lowland",41:"Speyside",42:"Speyside",
    43:"Lowland",44:"Speyside",45:"Highland",46:"Speyside",47:"Highland",48:"Highland",
    49:"Highland",50:"Speyside",51:"Lowland",52:"Highland",53:"Lowland",54:"Highland",
    55:"Lowland",56:"Lowland",57:"Speyside",58:"Highland",59:"Speyside",60:"Speyside",
    61:"Speyside",62:"Highland",63:"Campbeltown",64:"Speyside",65:"Speyside",66:"Speyside",
    67:"Highland",68:"Speyside",69:"Speyside",70:"Speyside",71:"Speyside",72:"Highland",
    73:"Highland",74:"Campbeltown",75:"Lowland",76:"Speyside",77:"Speyside",78:"Highland",
    79:"Speyside",80:"Speyside",81:"Highland",82:"Highland",83:"Islands",84:"Islands",
    85:"Lowland",86:"Lowland",87:"Speyside",88:"Highland",89:"Islands",90:"Highland",
    91:"Islands",92:"Islay",93:"Lowland",94:"Speyside",95:"Speyside",96:"Speyside",
    97:"Islay",98:"Islands",99:"Islay",100:"Lowland",101:"Speyside",102:"Lowland",
    103:"Highland",104:"Highland",105:"Highland",106:"Speyside",107:"Speyside",
    108:"Highland",109:"Speyside",110:"Highland",111:"Speyside",112:"Speyside",
    113:"Lowland",114:"Highland",115:"Lowland",116:"Highland",117:"Islands",
    118:"Speyside",119:"Highland",120:"Highland",121:"Islands",122:"Speyside",
    123:"Speyside",124:"Campbeltown",125:"Lowland",126:"Lowland",127:"Highland",
    128:"Speyside",129:"Speyside",130:"Islands",131:"Speyside",132:"Speyside",
    133:"Highland",134:"Islands",135:"Highland",136:"Speyside",137:"Islands",
    138:"Speyside",139:"Highland",140:"Highland",141:"Highland",
}
# Distilleries whose region is uncertain and needs human verification
REGION_REVIEW = {6, 105, 123}  # Aisla Bay, Lone Wolf, The Speyside Distillery

# Grain distilleries (vs malt) - informational note only
GRAIN = {35, 55, 104, 113, 125, 126}  # Cameronbridge, Girvan, Loch Lomond Grain, North British, Starlaw, Strathclyde

def norm(s):
    s = s.lower().replace("'", "").replace("\u2019", "")
    return re.sub(r"[^a-z0-9]", "", s)

def strip_the(s):
    return re.sub(r"^the ", "", s.lower())

def main():
    # parse PDF
    by_num = {}
    with open(PDF_TXT, encoding="utf-8") as f:
        txt = f.read()
    for m in re.finditer(r"(\d+)\.\s+(.+?)\s+Distillery", txt):
        by_num[int(m.group(1))] = m.group(2).strip()
    pdf = sorted(by_num.items())
    assert len(pdf) == 141, f"expected 141, got {len(pdf)}"

    c = sqlite3.connect(DB)
    rows = c.execute("SELECT distillery_id,name,country,region FROM distilleries").fetchall()
    exact = {}
    for did, name, country, region in rows:
        exact.setdefault(norm(name), []).append((did, name, country, region))
    pdf_named = []
    for num, name in pdf:
        nn = norm(name); sn = norm(strip_the(name))
        ex = exact.get(nn) or exact.get(sn)
        expr = [(did, rname, region) for did, rname, country, region in rows
                if norm(rname).startswith(nn) and norm(rname) != nn]
        pdf_named.append((num, name, ex, expr))

    # Build staging + cross-reference rows
    staging = []
    xref = []
    for num, name, ex, expr in pdf_named:
        region = REGION[num]
        needs_review_region = num in REGION_REVIEW
        note = ""
        if num in GRAIN:
            note = "Grain distillery (not single malt)"
        if needs_review_region:
            note = (note + "; " if note else "") + "region derived - verify"
        if ex:
            # canonical row present
            canon_ids = [d for d,_,_,_ in ex]
            has_region = any(r for _,_,_,r in ex)
            action = "verify_backfill_region" if not has_region else "verify"
            status_present = "present"
            matched_db = ";".join(f"{d}|{rn}|{reg}" for d,rn,_,reg in ex)
            data_conf = "high"
        elif expr:
            # only product expressions exist -> reconcile
            action = "reconcile_promote_to_canonical"
            status_present = "expression_only"
            matched_db = ";".join(f"{d}|{rn}|{reg}" for d,rn,reg in expr)
            data_conf = "medium"
            note = (note + "; " if note else "") + "exists only as product expression(s)"
        else:
            action = "insert"
            status_present = "absent"
            matched_db = ""
            data_conf = "high"
        staging.append({
            "pdf_no": num,
            "name": name,
            "country": "Scotland",
            "region": region,
            "status": "Operating",
            "status_source": SOURCE_FILE,
            "action": action,
            "data_confidence": data_conf,
            "notes_for_review": note,
        })
        xref.append({
            "pdf_no": num,
            "pdf_name": name,
            "region_derived": region,
            "region_needs_review": "yes" if needs_review_region else "no",
            "db_status": status_present,
            "matched_db": matched_db,
        })

    # Write staging CSV
    stage_path = os.path.join(OUTDIR, "staging_distilleries_2022.csv")
    with open(stage_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pdf_no","name","country","region","status",
                                          "status_source","action","data_confidence","notes_for_review"])
        w.writeheader()
        for r in staging:
            w.writerow(r)

    xref_path = os.path.join(OUTDIR, "cross_reference.csv")
    with open(xref_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pdf_no","pdf_name","region_derived",
                                          "region_needs_review","db_status","matched_db"])
        w.writeheader()
        for r in xref:
            w.writerow(r)

    # Summary stats
    n_insert = sum(1 for s in staging if s["action"] == "insert")
    n_recon = sum(1 for s in staging if s["action"] == "reconcile_promote_to_canonical")
    n_verify = sum(1 for s in staging if s["action"].startswith("verify"))
    n_region_backfill = sum(1 for s in staging if s["action"] == "verify_backfill_region")
    region_counts = {}
    for s in staging:
        region_counts[s["region"]] = region_counts.get(s["region"], 0) + 1

    print("Staging written:", stage_path)
    print("Cross-ref written:", xref_path)
    print(f"TOTAL={len(staging)} insert={n_insert} reconcile={n_recon} verify(region backfill)={n_region_backfill} verify_ok={n_verify-n_region_backfill}")
    print("Region distribution:", region_counts)

    # Build report
    report = build_report(staging, xref, n_insert, n_recon, n_verify, n_region_backfill, region_counts)
    with open(os.path.join(OUTDIR, "evaluation_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("Report written:", os.path.join(OUTDIR, "evaluation_report.md"))

def build_report(staging, xref, n_insert, n_recon, n_verify, n_region_backfill, region_counts):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []
    L.append(f"# P52 - 2022 Operating Scotch Distilleries: Evaluation & Import Plan\n")
    L.append(f"_Generated: {now}_\n")
    L.append(f"**Source:** {SOURCE_TITLE}\n")
    L.append(f"**File:** {SOURCE_FILE}\n")
    L.append(f"**Target DB:** `output/import/production.db` (1823 distillery rows; 855 Scotland)\n")
    L.append("\n---\n")
    L.append("## 1. Executive Summary\n")
    L.append(f"- The PDF lists **141 currently-operating Scotch whisky distilleries (Sept 2022)**.")
    L.append(f"- Cross-referenced against production.db, the Malt Radar `distilleries` table is in a **mixed/denormalised state**: it contains both a small set of canonical distilleries (with region metadata) AND a large set of **product expressions** (e.g. *\"Laphroaig Quarter Cask\"*, *\"Glenlivet Caribbean Reserve\"*) stored in the same table.")
    L.append(f"- Of the 141:")
    L.append(f"  - **{n_verify} already present** as a canonical row (only {n_region_backfill} of these carry a region -> region backfill needed).")
    L.append(f"  - **{n_recon} present only as product expression(s)** (distillery exists in DB but has no clean canonical row -> needs reconciliation).")
    L.append(f"  - **{n_insert} entirely absent** (genuine coverage gap -> need new canonical rows).\n")
    L.append("## 2. Data-Quality Findings (pre-existing, out of scope for this import)\n")
    L.append("- **Table pollution:** the `distilleries` table mixes distilleries and bottle expressions (836 of 855 Scotland rows have `region IS NULL`; only 19 carry region metadata). Some rows are non-distillery junk (*\"Chivas Brothers\"*, *\"Çeşitli\"*).")
    L.append("- **`status` column is typed REAL** in schema but holds text status here; should be TEXT. Recommend a separate schema fix gate.")
    L.append("- Recommend a dedicated cleanup gate to split expressions into `whisky_products` and dedupe, before this source's canonical rows are trusted as the baseline.\n")
    L.append("## 3. Proposed Import Plan (PHASE 2 - requires approval)\n")
    L.append("All changes gated behind an explicit approve step. Backup first (`output/import/backups/`).\n")
    L.append(f"1. **INSERT {n_insert} new canonical rows** (status=`Operating`, country=`Scotland`, derived region, `status_source`=PDF). Assign new `D####` ids.")
    L.append(f"2. **RECONCILE {n_recon} expression-only** distilleries: add a canonical row and link existing expressions (do NOT duplicate). Manual review per case.")
    L.append(f"3. **BACKFILL region + status** for the {n_region_backfill} present rows missing region; set `status='Operating'` for all 141 present.")
    L.append("4. Record `source_audit` + `entity_sources` for traceability.\n")
    L.append("## 4. Region Distribution (derived - SWA 6-region model)\n")
    for rg, n in sorted(region_counts.items(), key=lambda x:-x[1]):
        L.append(f"- {rg}: {n}")
    L.append(f"\n> Region is **derived domain knowledge**, not from the PDF. The PDF only certifies *operating status (Sept 2022)*. 3 entries flagged `region_needs_review` (Aisla Bay #6, Lone Wolf #105, The Speyside Distillery #123).\n")
    L.append("## 5. Staging Files\n")
    L.append("- `staging_distilleries_2022.csv` - 141 DB-ready rows with `action` column.")
    L.append("- `cross_reference.csv` - match results (pdf_no, name, db_status, matched_db).\n")
    L.append("## 6. Gate\n")
    L.append("**STOP. No production.db mutation performed in this phase.** Awaiting user approval to execute Phase 2 (import).")
    return "\n".join(L)

if __name__ == "__main__":
    main()
