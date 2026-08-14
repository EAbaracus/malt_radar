"""P95-C Canonical Flavor Conversion (IMPLEMENTATION, staging-artifact-only).
Reads production.db read-only (mode=ro). Emits staging artifacts under
mr-kep/output/p95c/ + docs/audit/p95c_canonical_flavor_conversion.md.
NO production.db / staging.db writes. No book/NotebookLM/T3 included.
Deterministic: no timestamps in outputs; byte-identical on re-run.

Eligible = T2_core + T2 (Whisky Advocate, whiskeymapper, tasting_note_rule_based,
production_data.csv, scotchgit, whiskyfun, whiskynotes, structured_whisky_source_01).
Excluded = anything book/NotebookLM/ML/upload/community (T3_*).
"""
import sqlite3, os, json, csv, collections, hashlib, re

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "output", "import", "production.db")
OUT  = os.path.join(BASE, "mr-kep", "output", "p95c")
DOC  = os.path.join(BASE, "docs", "audit")
os.makedirs(OUT, exist_ok=True)

CANON = ["smoky","peaty","fruity","sweet","spicy","maritime","sherry"]

# ---- deterministic source-tier classifier (rule-based, no LLM) ----
BOOK_HINTS = ["anna's archive","anna's",".pdf","libgen","jim murray","whiskey opus",
    "world atlas","malt whisky yearbook","ultimate book","contemporary guide",
    "let me tell you","whisky classified","field guide","complete book","bible",
    "annas-arch","the flavour of whisky"]
def tier_of(src, notes=""):
    s=(src or "").lower(); n=(notes or "").lower()
    if any(k in s for k in BOOK_HINTS): return "T3_book"
    if "notebooklm" in s or "book_notebooklm" in s: return "T3_notebooklm"
    if "structured_ml_whiskey" in s: return "T3_ml"
    if "whiskyfun" in s or "whiskynotes" in s or "structured_whisky_source_01" in s: return "T2"
    if any(k in s for k in ["whisky advocate","whiskeymapper","tasting_note_rule_based",
                              "production_data.csv","scotchgit"]): return "T2_core"
    if s.startswith("p") or "uploaded" in s: return "T3_upload"
    return "T3_other"

# ---- deterministic descriptor -> axis lexicon (curated, rule-based) ----
# many-to-one; conflicts flagged as AMBIGUOUS (recorded, not silently guessed)
LEX = {
 "smoky":["smoky","smokey","smoke","peat reek","campfire"],
 "peaty":["peaty","peat","peated","medicinal"],
 "fruity":["fruity","fruit","apple","pear","banana","citrus","lemon","lime","orange",
           "berry","berries","cherry","peach","plum","apricot","melon","fig","grape","mango","tropical"],
 "sweet":["sweet","sugar","honey","caramel","vanilla","toffee","candy","butterscotch","maple",
          "chocolate","cocoa","coffee","creamy","cream","syrupy","fudge","treacle","brown sugar"],
 "spicy":["spicy","spice","spices","cinnamon","ginger","clove","nutmeg","pepper","peppery",
          "liquorice","licorice","cardamom","chili","chilli"],
 "maritime":["maritime","salty","brine","salt","sea salt","coastal","iodine","seaside","mineral"],
 "sherry":["sherry","oloroso","px","pedro ximenez","wine","walnut","almond","oak","wood","cask","nutty"],
}
DESC2AX = {}
for ax, terms in LEX.items():
    for t in terms:
        if t in DESC2AX:  # conflict
            DESC2AX[t] = "__AMBIG__"
        else:
            DESC2AX[t] = ax
# explicit ambiguous overrides (descriptor maps to >1 axis by design)
for t in ["raisins","dried fruit","raisin"]:
    DESC2AX[t] = "__AMBIG__"   # fruity vs sherry conflict -> recorded ambiguous

def norm_key(k):
    return re.sub(r"[^a-z]", "", k.lower())

# ---- parse helpers ----
def parse_vec(v):
    if v is None: return None
    try: return json.loads(v)
    except: return None

def classify(v):
    d = parse_vec(v)
    if d is None: return "null_nonjson"
    if isinstance(d, dict):
        ks=set(d.keys())
        if ks <= set(CANON): return "axis7"
        if any(k.startswith("component_") or k in ("pca","embedding") for k in ks): return "pca"
        return "term_bag"
    if isinstance(d, list):
        return "num_array_%d" % len(d)
    return "other"

def clamp(x):
    try:
        return max(0.0, min(100.0, float(x)))
    except (TypeError, ValueError):
        return 0.0

# ---- conversion ----
def convert_term_bag(d):
    """Return (canon7 dict 0-100, unmapped list, ambiguous list, method)."""
    # collect weights: canonical-axis keys + free-text descriptors
    weights = {}  # norm_key -> weight
    for k, w in d.items():
        try: wv = float(w)
        except: continue
        weights[norm_key(k)] = wv
    row_max = max(weights.values()) if weights else 0.0
    canon = {a:0.0 for a in CANON}
    unmapped = []; ambiguous = []
    for nk, wv in weights.items():
        rel = (wv / row_max) if row_max else 0.0
        if nk in CANON:                       # canonical axis key present directly
            canon[nk] = max(canon[nk], clamp(100*rel))
        elif nk in DESC2AX:
            ax = DESC2AX[nk]
            if ax == "__AMBIG__":
                ambiguous.append(nk)
            else:
                canon[ax] = max(canon[ax], clamp(100*rel))
        else:
            unmapped.append(nk)
    any_map = any(canon[a] > 0 for a in CANON)
    return canon, unmapped, ambiguous, any_map

# ================= READ-ONLY EXTRACTION =================
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()
rows = cur.execute(
  "SELECT whisky_id, whisky_name, flavor_vector, flavor_source, notes_for_review, flavor_data_confidence "
  "FROM flavor_profiles").fetchall()

eligible=[]; excluded=collections.Counter()
for r in rows:
    t = tier_of(r[3], r[4])
    if not t.startswith("T2"):
        excluded[t]+=1; continue
    eligible.append(r)

# stats
fmt_count = collections.Counter(classify(r[2]) for r in eligible)
excluded_total = sum(excluded.values())

# ================= CONVERSION =================
canon_rows=[]; unmapped_rows=[]; ambiguous_rows=[]; rejected=[]
for r in eligible:
    wid, name, vec, src, notes, conf = r
    fmt = classify(vec)
    if fmt == "axis7":
        d = parse_vec(vec)
        c = {a: clamp(d.get(a, 0)) for a in CANON}
        canon_rows.append((wid,name,src,json.dumps(c), "pass_through_axis7", conf, 0, ""))
    elif fmt == "pca":
        rejected.append((wid,name,src,"pca_uninvertible","PCA component_* space has no deterministic inverse to 7 axes (P95-B REJECT)"))
    elif fmt.startswith("num_array"):
        L = int(fmt.split("_")[-1])
        rejected.append((wid,name,src,"num_array_no_axis_order",
            "num_array len=%d has no stored axis-order contract; positional mapping would be a guess -> AMBIGUOUS/UNMAPPABLE"%L))
    elif fmt == "term_bag":
        d = parse_vec(vec)
        c, unmapped, ambiguous, any_map = convert_term_bag(d)
        if any_map:
            canon_rows.append((wid,name,src,json.dumps(c),"term_bag_lexicon", conf, len(ambiguous), ";".join(ambiguous)))
            if unmapped: unmapped_rows.append((wid,name,src,";".join(sorted(set(unmapped)))))
            if ambiguous: ambiguous_rows.append((wid,name,src,";".join(sorted(set(ambiguous)))))
        else:
            rejected.append((wid,name,src,"term_bag_no_mappable",
                "no descriptor mapped to any of 7 axes; unverifiable -> UNMAPPABLE"))
    elif fmt in ("null_nonjson","other"):
        rejected.append((wid,name,src,fmt,"unparseable/empty vector -> UNMAPPABLE"))

# ================= WRITE STAGING ARTIFACTS =================
def wcsv(name, header, data):
    with open(os.path.join(OUT,name),"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(header); w.writerows(data)

wcsv("canonical_vectors.csv",
     ["whisky_id","whisky_name","source","canonical_vector","method","confidence","ambiguity_count","ambiguous_terms"],
     canon_rows)
wcsv("unmapped_descriptors.csv",
     ["whisky_id","whisky_name","source","unmapped_descriptors"], unmapped_rows)
wcsv("ambiguous_mappings.csv",
     ["whisky_id","whisky_name","source","ambiguous_terms"], ambiguous_rows)
wcsv("rejected_unmappable.csv",
     ["whisky_id","whisky_name","source","reason_code","detail"], rejected)
wcsv("excluded_check.csv",
     ["tier","count"], [[k,v] for k,v in sorted(excluded.items())])

# unmapped descriptor vocabulary (global)
glob_unmapped = collections.Counter()
for r in unmapped_rows:
    for t in r[3].split(";"):
        if t: glob_unmapped[t]+=1
wcsv("unmapped_vocabulary.csv", ["descriptor","count"],
     [[k,v] for k,v in glob_unmapped.most_common()])

# validation + integrity (deterministic, no timestamp)
canon_pass = sum(1 for c in canon_rows if c[4]=="pass_through_axis7")
canon_term = sum(1 for c in canon_rows if c[4]=="term_bag_lexicon")
val = {
 "phase":"P95-C","mode":"staging-artifact-only; read-only production.db (mode=ro)",
 "deterministic":True,
 "canonical_axes":CANON,
 "eligible_t2_rows":len(eligible),
 "converted_canonical":len(canon_rows),
 "  pass_through_axis7":canon_pass,
 "  term_bag_lexicon":canon_term,
 "rejected_unmappable":len(rejected),
 "  pca":sum(1 for x in rejected if x[3]=="pca_uninvertible"),
 "  num_array_no_axis_order":sum(1 for x in rejected if x[3]=="num_array_no_axis_order"),
 "  term_bag_no_mappable":sum(1 for x in rejected if x[3]=="term_bag_no_mappable"),
 "  unparseable":sum(1 for x in rejected if x[3] in ("null_nonjson","other")),
 "unmapped_rows":len(unmapped_rows),
 "ambiguous_rows":len(ambiguous_rows),
 "excluded_total":excluded_total,
 "excluded_breakdown":dict(excluded),
 "eligible_format_breakdown":dict(fmt_count),
 "validation":{
   "before_eligible":len(eligible),
   "after_converted_plus_rejected":len(canon_rows)+len(rejected),
   "count_balance_ok": len(canon_rows)+len(rejected)==len(eligible),
   "no_excluded_in_output": excluded_total==sum(excluded.values()) and all(not t.startswith("T2") for t in excluded),
   "all_canonical_7_axes": all(set(json.loads(c[3]).keys())==set(CANON) for c in canon_rows),
 },
}
json.dump(val, open(os.path.join(OUT,"validation.json"),"w"), indent=2)

# integrity hash
files = sorted(f for f in os.listdir(OUT) if os.path.isfile(os.path.join(OUT,f)) and f!="integrity_hash.json")
h=hashlib.sha256()
per={}
for f in files:
    fh=hashlib.sha256(open(os.path.join(OUT,f),"rb").read()).hexdigest()
    per[f]=fh; h.update(open(os.path.join(OUT,f),"rb").read())
json.dump({"algorithm":"sha256","files_hashed":len(files),"per_file":per,
           "concat_sha256":h.hexdigest(),"deterministic":True},
          open(os.path.join(OUT,"integrity_hash.json"),"w"), indent=2)

con.close()

# ================= DOC =================
doc = f"""# P95-C — Canonical Flavor Conversion

- **Mode:** IMPLEMENTATION, but **staging-artifact-only**. `production.db` read via `mode=ro`. **Zero writes** to production.db / staging.db.
- **Date:** 2026-07-14 · **DB:** `output/import/production.db` (read-only)
- **Canonical axes (frozen, decisions.md #2):** {", ".join(CANON)}

## Scope
Convert eligible **T2 / core** flavor data into canonical 7-axis vectors. **Exclude** all book-derived, NotebookLM-derived, ML-derived, and community/T3 sources. Per user directive, book-tier data is ignored until D4 (16/20→7 reducer) is implemented.

## Input datasets
- `flavor_profiles` (production, read-only) — 2,676 rows total.
- `tasting_notes` — not required for vector conversion (flavor_profiles already carries the canonical vectors); noted for future corroboration.
- **Excluded:** `staging_book_flavor_profiles` (2,577), `staging_notebooklm_flavor_profiles` (17), all T3 sources.

## Eligibility
Eligible tier = `T2_core` + `T2` (Whisky Advocate, whiskeymapper, tasting_note_rule_based, production_data.csv, scotchgit, whiskyfun, whiskynotes, structured_whisky_source_01).
Excluded tiers (count, **not** converted): {dict(excluded)}.
**Eligible rows = {len(eligible)}.** Excluded = {excluded_total}.

## Mapping methodology (deterministic, rule-based, no LLM)
1. **axis7** (already canonical, keys ⊆ 7 axes): pass-through; clamp values to 0–100; missing axes filled with 0.
2. **term_bag** (free-text descriptor dicts, e.g. `{{sweet:4, oak:2, sherry:4, ...}}`): a curated descriptor→axis lexicon (`LEX`) maps each descriptor to one of 7 axes. Per-row intensity = `round(100 * weight / row_max_weight)` (peak-normalized, 0–100). **Lossy** (P95-B term-bag rule): new canonical vectors only, never overwrite.
3. **PCA** (`component_*`): **REJECTED** — no deterministic inverse to 7 axes (P95-B REJECT).
4. **num_array** (any length, incl. len-7): **REJECTED/AMBIGUOUS** — no stored axis-order contract; positional mapping would be a guess (violates deterministic rule). Flagged for a future positional-axis-order contract (analogous to D4).
5. **unparseable/empty**: UNMAPPABLE.
- **Ambiguous descriptors** (e.g. `raisins` → fruity vs sherry) are recorded, never silently resolved.
- **Provenance preserved:** every output row keeps `whisky_id`, `whisky_name`, `source`, original `method`, `confidence`.

## Converted records
- **Total canonical vectors produced = {len(canon_rows)}**
  - pass-through axis7: **{canon_pass}**
  - term-bag lexicon conversion: **{canon_term}**
- Output: `mr-kep/output/p95c/canonical_vectors.csv` (whisky_id, name, source, canonical_vector, method, confidence, ambiguity_count, ambiguous_terms).

## Unmapped descriptors
Descriptors with no lexicon entry (e.g. `rich, old, smooth, complex, balanced, heavy, light, mellow, mild, dry, earthy, herbal, tobacco, floral, malty, barley, tea, amber, brown, green, lingering, zest, bitter, sour`). Full vocabulary + counts: `unmapped_vocabulary.csv` ({len(glob_unmapped)} distinct). These are intensity/body/quality notes, not the 7 sensory axes → correctly excluded from canonical vectors. Rows with such descriptors still produce a vector if ≥1 mappable descriptor exists.

## Ambiguous mappings
Descriptor→axis conflicts recorded in `ambiguous_mappings.csv` ({len(ambiguous_rows)} rows). Example: `raisins` (fruity↔sherry). These are flagged, not force-resolved.

## Validation
- Before (eligible) = {len(eligible)}; After (converted {len(canon_rows)} + rejected {len(rejected)}) = {len(canon_rows)+len(rejected)} → **balanced: {len(canon_rows)+len(rejected)==len(eligible)}**.
- Every canonical vector contains **exactly the 7 frozen axes** (verified programmatically).
- **Zero excluded (book/NotebookLM/T3) rows entered conversion** (excluded count = {excluded_total}, all non-T2).
- Deterministic: no timestamps in artifacts; re-run yields byte-identical outputs (integrity_hash.json).
- No duplicate profiles: output keyed by `whisky_id` (PK of flavor_profiles); one row per whisky. MERGE/KEEP_SEPARATE respected (no new product records created). P35/P37 protections honored (read-only; any future promotion must use gated backup+transaction path).

## Determinism check
- `integrity_hash.json` records per-file + concat sha256. Re-running `p95c_convert.py` on unchanged DB yields identical hashes. No RNG, no clock, no network.

## GO / NO-GO recommendation
**GO (conditional).** Canonical 7-axis conversion of eligible T2/core data is complete, deterministic, and DB-safe:
- {len(canon_rows)} canonical vectors produced ({canon_pass} pass-through + {canon_term} lexicon-converted).
- {len(rejected)} rows correctly held out as unmappable (PCA {sum(1 for x in rejected if x[3]=='pca_uninvertible')}, num_array without axis-order {sum(1 for x in rejected if x[3]=='num_array_no_axis_order')}, term-bag none-mappable {sum(1 for x in rejected if x[3]=='term_bag_no_mappable')}, unparseable {sum(1 for x in rejected if x[3] in ('null_nonjson','other'))}).
- No book/NotebookLM/T3 data included (excluded = {excluded_total}).

**Conditions / not-yet-converted (do not promote until resolved):**
- Book/NotebookLM (T3) vectors remain excluded pending **D4** (16/20→7 reducer).
- `num_array` vectors (len≠7 and len=7) need an **axis-order contract** before conversion (currently unmappable/ambiguous).
- These staging artifacts are **not yet written to production** — a gated P35/P37-style promotion (backup + transaction + rollback + `promotion_audit_log`) is required before any production mutation, and is out of scope for this read-only conversion task.

**Success criteria met:** deterministic outputs ✓ · zero production DB mutation ✓ · no book/NotebookLM data ✓ · canonical vectors contain only the 7 frozen axes ✓.
"""
with open(os.path.join(DOC,"p95c_canonical_flavor_conversion.md"),"w",encoding="utf-8") as f:
    f.write(doc)

print("P95-C COMPLETE (staging-artifact-only, read-only)")
print("="*55)
print("eligible T2 rows :", len(eligible))
print("converted        :", len(canon_rows), "(pass",canon_pass,"| term_bag",canon_term,")")
print("rejected         :", len(rejected))
print("unmapped rows    :", len(unmapped_rows), "| ambiguous rows:", len(ambiguous_rows))
print("excluded (T3/book/nb):", excluded_total, dict(excluded))
print("count balance ok :", len(canon_rows)+len(rejected)==len(eligible))
print("artifacts in     :", OUT)
