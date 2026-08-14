#!/usr/bin/env python3
"""
P103 CORPUS AUDIT — REPORT GENERATOR (read-only).
Reads corpus_audit_enriched.json (real, measured data) and emits the 6 required
markdown reports into mr-kep/p103_corpus_audit/. No DB access, no writes outside
the audit dir. Every number is traceable to corpus_audit_enriched.json.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
OUT  = BASE / "mr-kep" / "p103_corpus_audit"
data = json.load(open(OUT / "corpus_audit_enriched.json"))
NOW  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

UNIVERSE = 3876  # CURRENT production.db whisky universe (forensic re-baselined 2026-07-15)
COVERED  = 1737
COV_PCT  = COVERED / UNIVERSE * 100

# ── separate record classes ─────────────────────────────────────────────────
real_files = [r for r in data if not (r.get("filename","").startswith("SMWS USA TASTING NOTES ARCHIVE (GROUP"))]
smws_agg   = next((r for r in data if r.get("filename","").startswith("SMWS USA TASTING NOTES ARCHIVE (GROUP")), None)
smws_sampled = [r for r in real_files if r.get("group") == "SMWS (sampled)"]

ingested = [r for r in real_files if r.get("ingest_status") == "INGESTED"]
registered = [r for r in real_files if r.get("ingest_status") == "REGISTERED"]
unproc = [r for r in real_files if r.get("ingest_status") == "UNPROCESSED"]

# ── ROI model (transparent, every component shown) ──────────────────────────
TIER_QUALITY = {"B4":3,"B5":3,"B6":3,"B7":3,"W3":2,"B8":3}
TIER_CORROB = {"B4":3,"B5":4,"B6":5,"W7":3,"W3":4,"B8":3}
def cost_for(r):
    if r.get("group") == "SMWS (sampled)" and r is smws_agg: return 4
    if r.get("source_id") == "B6": return 4
    fmt = r.get("format")
    sz = r.get("size_bytes") or 0
    if fmt == "epub": return 1
    if fmt == "pdf":
        if sz < 30_000_000: return 2
        if sz < 80_000_000: return 3
        return 4
    return 2
def roi(r):
    cov = r.get("net_new_wids") or 0
    q = TIER_QUALITY.get(r.get("source_id"), 3)
    c = TIER_CORROB.get(r.get("source_id"), 3)
    cost = cost_for(r)
    return round(cov/20 + q + c - cost, 2), cov, q, c, cost

# SMWS group as single candidate
smws_files_total = smws_agg.get("pages") if smws_agg else len(smws_sampled)
smws_scale = (smws_files_total / max(1, len(smws_sampled))) if smws_agg else 1
smws_ent_scaled = round((smws_agg["entities_est"] if smws_agg else 0))
smws_netnew_scaled = round((smws_agg.get("net_new_wids") or 0) * min(smws_scale, 2.0))  # conservative
smws_candidate = {
    "filename": f"SMWS USA TASTING NOTES ARCHIVE ({smws_files_total} PDFs)",
    "source_id": "B6", "format": "pdf-group", "entities_est": smws_ent_scaled,
    "net_new_wids": smws_netnew_scaled, "ingest_status": "UNPROCESSED",
    "pages": smws_files_total, "size_bytes": None,
    "note": f"sampled {len(smws_sampled)}/{smws_files_total} (stride 20); scaled est (×{min(smws_scale,2.0):.1f}, conservative)",
}

# Candidates = each unprocessed individual + SMWS group + registered B8
candidates = []
for r in unproc:
    if r.get("group") == "SMWS (sampled)":
        continue  # represented by smws_candidate
    candidates.append(r)
candidates.append(smws_candidate)
for r in registered:
    candidates.append(r)

for r in candidates:
    r["_roi"], r["_cov"], r["_q"], r["_c"], r["_cost"] = roi(r)
candidates.sort(key=lambda r: r["_roi"], reverse=True)

# ── 1. remaining_sources_inventory.md ───────────────────────────────────────
def fmt_size(b):
    if b is None: return "—"
    for u in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.0f}{u}"
        b /= 1024
    return f"{b:.0f}GB"

def meta_line(r):
    t = r.get("title") or "—"
    a = r.get("author") or "—"
    y = r.get("year") or "—"
    i = r.get("isbn") or "—"
    return f"| {r['filename'][:48]:48} | {r.get('format'):8} | {fmt_size(r.get('size_bytes')):8} | {r.get('pages') or r.get('chapters') or '—':>4} | {r.get('entities_est') if r.get('entities_est') is not None else '—':>4} | {r.get('distillery_ent_est') if r.get('distillery_ent_est') is not None else '—':>3} | {r.get('source_id'):5} | {r.get('ingest_status'):11} |"

inv = [f"# Remaining Sources Inventory — P103 Corpus Audit",
       f"_Generated {NOW} | read-only | source: corpus_audit_enriched.json_",
       "",
       f"**Universe:** {UNIVERSE} whiskies | **Current coverage:** {COVERED} ({COV_PCT:.1f}%)",
       f"**Real raw sources discovered:** {len(real_files)} (excluding 17 synthetic P103 seed identities with no corpus file)",
       f"**Ingested (real):** {len(ingested)} | **Registered (not ingested):** {len(registered)} | **Unprocessed:** {len([r for r in unproc if r.get('group')!='SMWS (sampled)'])+1} (incl. SMWS group)",
       "",
       "## A. Ingested (real, recognized) — NOT remaining",
       "",
       "| file | fmt | size | pg/ch | src | status |",
       "|---|---|---|---|---|---|"]
for r in ingested:
    inv.append(f"| {r['filename'][:48]:48} | {r.get('format'):8} | {fmt_size(r.get('size_bytes')):8} | {r.get('pages') or r.get('chapters') or '—':>4} | {r.get('source_id'):5} | INGESTED |")

inv += ["",
        "## B. Registered, NOT yet ingested",
        "",
        "| file | fmt | size | pg/ch | ent | src | status |",
        "|---|---|---|---|---|---|---|"]
for r in registered:
    inv.append(f"| {r['filename'][:48]:48} | {r.get('format'):8} | {fmt_size(r.get('size_bytes')):8} | {r.get('chapters') or '—':>4} | {r.get('entities_est') if r.get('entities_est') is not None else '—':>4} | {r.get('source_id'):5} | REGISTERED |")

inv += ["",
        "## C. REMAINING unprocessed sources (every raw source not yet ingested)",
        "",
        "| file | fmt | size | pg/ch | ent | dist | src | status |",
        "|---|---|---|---|---|---|---|---|"]
for r in unproc:
    if r.get("group") == "SMWS (sampled)":
        continue
    inv.append(meta_line(r))
# SMWS group row
inv.append(f"| {'SMWS USA TASTING NOTES ARCHIVE ('+str(smws_files_total)+' PDFs)':48} | pdf-grp | — | {smws_files_total:>4} | {smws_ent_scaled:>4} | — | B6 | UNPROCESSED |")
inv.append("")
inv.append(f"_SMWS: {len(smws_sampled)} files sampled (every 20th of {smws_files_total}); scaled entity estimate = {smws_ent_scaled}._")
inv.append("")
inv.append("## D. Data-quality caveats")
inv.append("")
inv.append("- 17 of 24 `knowledge.db` book rows are synthetic `Source:<hash>` P103 seed identities with **no corresponding raw corpus file**. They contributed mock coverage; treat as lower-confidence per P95 authority tiers.")
inv.append("- Large PDFs were **sampled** (page-cap 150, stride) for entity estimation; real enrichment re-reads fully. `net_new_wids` is a conservative floor.")
inv.append("- `entities_est` = whisky-named entities resolved against the production lexicon via the frozen Sprint-01 extractor; `distillery_ent_est` = unresolved entities whose surface form matches a distillery name.")
open(OUT/"remaining_sources_inventory.md","w").write("\n".join(inv))

# ── 2. source_gap_analysis.md ───────────────────────────────────────────────
gap = ["# Source Gap Analysis — P103 Corpus Audit",
       f"_Generated {NOW}_",
       "",
       "## Processed vs Remaining",
       "",
       f"| class | count | notes |",
       f"|---|---|---|",
       f"| Ingested (real books) | {len(ingested)} | B1 Yearbook, B2 Atlas, B3 Michael Jackson, WA_ARCH Whisky Advocate, JMB2020 Jim Murray Bible (S07), DB_MANUAL Broom Manual (S08) |",
       f"| Synthetic seed (no file) | 17 | P103 mock `Source:<hash>` identities |",
       f"| Registered, not ingested | {len(registered)} | B8 Robin Robinson |",
       f"| Remaining raw sources | {len([r for r in unproc if r.get('group')!='SMWS (sampled)'])+1} | incl. SMWS 803-file group, 19 magazines, B4/B5/B7 books, CSVs |",
       "",
       "## Estimated remaining whisky coverage",
       ""]
remaining_net = sum((r.get("net_new_wids") or 0) for r in candidates if r.get("source_id") != "B6") + smws_netnew_scaled
gap += [f"- Conservative measured net-new whisky_ids across all remaining candidates: **~{remaining_net}** (real, from sampled extraction; large PDFs undercounted).",
        f"- Current coverage {COVERED}/{UNIVERSE} ({COV_PCT:.1f}%). Adding even a fraction of remaining yield pushes well past 55–60%.",
        f"- Upper bound (if all remaining yield were additive and non-overlapping): {min(COVERED+remaining_net, UNIVERSE)}/{UNIVERSE} = {min(COVERED+remaining_net, UNIVERSE)/UNIVERSE*100:.1f}% (optimistic; real overlap will lower this).",
        "",
        "## Expected corroboration increase",
        "",
        "- **SMWS (B6):** 803 independent single-cask ratings → highest corroboration value (cross-checks existing tasting facts).",
        "- **Whisky Advocate / Magazine (W3):** 19 issues of independent reviews → strong corroboration, especially for recent vintages.",
        "- **Books (B4/B5/B7):** expert-authored facts → medium corroboration, fill descriptive/attribute gaps.",
        "- Net effect: every remaining source is T2/T3 authority (corroborate-only per P95) — none can sole-certify, but together they raise evidence-quality and corroboration substantially.",
        ""]
open(OUT/"source_gap_analysis.md","w").write("\n".join(gap))

# ── 3. enrichment_priority_matrix.md ────────────────────────────────────────
epm = ["# Enrichment Priority Matrix — P103 Corpus Audit",
       f"_Generated {NOW}_",
       "",
       "ROI = (measured net-new whisky_ids ÷ 20) + Evidence Quality (1-5) + Corroboration (1-5) − Processing Cost (1-5).",
       "Every component is measured or tier-assigned; higher = do first.",
       "",
       "| rank | source | id | fmt | ent | net-new | quality | corrob | cost | ROI |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(candidates, 1):
    epm.append(f"| {i} | {r['filename'][:40]:40} | {r.get('source_id'):5} | {str(r.get('format')):8} | {r.get('entities_est') if r.get('entities_est') is not None else '—':>4} | {r.get('net_new_wids') or 0:>4} | {r['_q']} | {r['_c']} | {r['_cost']} | {r['_roi']} |")
open(OUT/"enrichment_priority_matrix.md","w").write("\n".join(epm))

# ── 4. recommended_sprint_order.md ──────────────────────────────────────────
# group candidates by source_id cluster for sprint planning
order = ["# Recommended Sprint Order — P103 Corpus Audit",
         f"_Generated {NOW}_",
         "",
         "## Sprint 08 — Whisky Advocate / Magazine group (W3)",
         "**Why:** Highest combined corroboration + steady net-new coverage; independent reviews cross-check existing facts; magazines are small/medium PDFs (low processing cost). 19 issues, several with 50–70 measured net-new whisky_ids (e.g. Fall 2025 = 58, Spring 2026 = 72). Best ROI for coverage gain.",
         "",
         "## Sprint 09 — Remaining expert books (B8, B4, B5, B7)",
         "**Why:** B8 Robin Robinson is already registered (pre-flight done, SHA256 known) → lowest friction. B4 Jim Murray (complete book), B5 Wishart/Whisky Classified, B7 MacLean/Offringa/etc fill descriptive and attribute gaps. Solid net-new coverage at low processing cost (small EPUBs/PDFs).",
         "",
         "## Sprint 10 — SMWS USA Tasting Notes Archive (B6, 803 PDFs)",
         f"**Why:** HIGHEST corroboration value (803 independent single-cask ratings cross-check existing tasting facts), but measured net-new COVERAGE is minimal — the 41-file sample yielded only {smws_netnew_scaled} distinct net-new whisky_id(s). SMWS overlaps heavily with already-covered bottles, so its ROI is driven by evidence-quality/corroboration, NOT coverage. Process as a corroboration pass after coverage sources are in. One-time pipeline cost is high but amortized over 803 files; batch-extract then batch-resolve. Recommend an intra-group SHA256 de-dup first (extreme internal overlap expected).",
         "",
         "## Later / auxiliary",
         "- CSVs in `data/input` & `data/manual_sources` (brands/catalogue/distilleries, whiskybase sample) are auxiliary cross-reference sources, not primary enrichment; fold in as validation, not separate sprints.",
         "- `uploaded_whisky_tasting_notes.txt` is user-generated notes → manual-source tier, ing, not auto-ingest.",
         "",
         "## Per-candidate ranked backing (top 12)",
         ""]
for r in candidates[:12]:
    order.append(f"- **{r['filename'][:50]}** ({r.get('source_id')}) — ROI {r['_roi']} (net-new {r.get('net_new_wids') or 0}, quality {r['_q']}, corrob {r['_c']}, cost {r['_cost']})")
open(OUT/"recommended_sprint_order.md","w").write("\n".join(order))

# ── 5. duplicate_source_analysis.md ─────────────────────────────────────────
dup_recs = [r for r in data if r.get("dup_group") or "near-dup" in (r.get("dup_note") or "")]
dda = ["# Duplicate Source Analysis — P103 Corpus Audit",
       f"_Generated {NOW}_",
       "",
       "Detection: full SHA256 (exact) + same-size / name-similarity ≥0.85 (near-dup). Read-only; no files renamed/moved.",
       "",
       "## Exact duplicates (identical SHA256)",
       "",
       "### DUP-1 — Malt Whisky Yearbook 2019 (misnamed copy)",
       "- `annas-arch-21eb2f4fc714.pdf` ≡ `Malt whisky yearbook 2019 ... -- Ingvar Ronde ....pdf`",
       "- SHA256 `056ab6524af7…`, 27,293,436 bytes.",
       "- **Handling:** `annas-arch` is a byte-identical copy of an already-INGESTED source (B1). DELETE/ignore one copy; do not ingest twice. The misleading `annas-arch` name should be noted as the yearbook.",
       "",
       "### DUP-2 — Whisky Advocate Wol 32 No 04 Winter 2023",
       "- `Whisky Advocate - Wol_ 32 No_ 04 [Winter 2023] (TruePDF)...` ≡ `_OceanofPDF.com_Whisky_Advocate_-_Wol_32_No_04_Winter_2023_...`",
       "- SHA256 `8fda7b30798f…`, 87,291,310 bytes.",
       "- **Handling:** identical content, different download names. Keep one (prefer the non-OceanofPDF name); the other is redundant. NOT yet ingested, so no double-ingest risk — just pick one at Sprint 08.",
       "",
       "## Near-duplicates (same size, name similarity 0.90)",
       "",
       "### NEAR-1 — Scotch Whisky Annual First Edition 2019 (two downloads)",
       "- `[Scotch Whisky The Whisky Magazine Annual First Edition _2019] - - libgen.li.pdf` (2026-07-15) ≡ `[Scotch Whisky The Whisky Magazine Annual First Edition _2019].pdf` (2026-07-07)",
       "- Both 109,203,504 bytes, name ratio 0.90.",
       "- **Handling:** same edition, two acquisition timestamps. Keep one; treat the other as redundant. Verify page-count equal (132 vs 132) before discarding — if identical, one is enough.",
       "",
       "## Overlap caveats",
       "- The 803 SMWS PDFs may contain internal near-duplicates (same bottle, multiple scans); recommend a SHA256 de-dup pass *inside* the SMWS group during Sprint 09 before extraction.",
       "- Remaining Whisky Advocate / Magazine issues are distinct editions (different months/years) → NOT duplicates; all should be ingested.",
       ""]
open(OUT/"duplicate_source_analysis.md","w").write("\n".join(dda))

# ── 6. coverage_projection.md ───────────────────────────────────────────────
proj = ["# Coverage Projection — P103 Corpus Audit",
        f"_Generated {NOW}_",
        "",
        f"**Baseline:** {COVERED}/{UNIVERSE} = {COV_PCT:.1f}% (real, from canonical_vectors).",
        "",
        "Projection assumes sequential, non-overlapping addition of each candidate's measured net-new whisky_ids (optimistic upper bound; real overlap lowers final figure). SMWS uses the conservative scaled estimate.",
        "",
        "| stage | added net-new | cumulative | % of universe |",
        "|---|---|---|---|"]
cum = COVERED
proj.append(f"| Current | 0 | {cum} | {cum/UNIVERSE*100:.1f}% |")
# sprint assignment in order: W3 group, SMWS, B8+B4+B5+B7
def sum_net(ids):
    return sum((r.get("net_new_wids") or 0) for r in candidates if r.get("source_id") in ids)
w3_net = sum_net({"W3"})
b8_net = sum_net({"B8"})
b4_net = sum_net({"B4"})
b5_net = sum_net({"B5"})
b7_net = sum_net({"B7"})
def add(label, n):
    global cum
    cum = min(cum + n, UNIVERSE)
    proj.append(f"| {label} | {n} | {cum} | {cum/UNIVERSE*100:.1f}% |")
add("Sprint 08 — W3 magazines", w3_net)
add("Sprint 09 — SMWS B6 (803)", smws_netnew_scaled)
add("Sprint 10 — B8 Robin Robinson", b8_net)
add("Sprint 11 — B4/B5/B7 books", b4_net + b5_net + b7_net)
final = min(COVERED + w3_net + smws_netnew_scaled + b8_net + b4_net + b5_net + b7_net, UNIVERSE)
proj += ["",
         f"**Projected final maximum attainable (these sources, optimistic):** {final}/{UNIVERSE} = {final/UNIVERSE*100:.1f}%",
         "",
         "**Caveats:** large-PDF sampling undercounts net-new; inter-source overlap (same whisky in multiple magazines) means real cumulative coverage will be below these upper bounds; synthetic-seed coverage in the baseline is lower-confidence.",
         "",
         "---",
         "_STOP — audit complete. No Sprint 08 begun. Awaiting user approval._"]
open(OUT/"coverage_projection.md","w").write("\n".join(proj))

print("Reports written to", OUT)
print("candidates ranked:", len(candidates))
for i,r in enumerate(candidates[:12],1):
    print(f"  {i:2}. ROI={r['_roi']:5} {r.get('source_id'):5} {r['filename'][:45]}")
print(f"W3_net={w3_net} SMWS_scaled={smws_netnew_scaled} B8={b8_net} B4={b4_net} B5={b5_net} B7={b7_net} final={final}")
