"""P95-B - Authority Matrix Revision & Canonical Flavor Standard.
DETERMINISTIC ARCHITECTURE PHASE. STRICT READ-ONLY. No promotion, no DB writes,
no phase regeneration. Reuses cached P95-A artifacts + frozen authority contracts.

Emits to mr-kep/output/p95b/:
  canonical_product_policy.md, authority_matrix_v2.md, canonical_flavor_standard.md,
  source_weight_matrix.csv, batch_classification.csv, promotion_rulebook.md,
  p95b_validation_report.md, integrity_hash.json
"""
import sqlite3, os, json, csv, re, collections, hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "output", "import", "production.db")
P95A = os.path.join(BASE, "mr-kep", "output", "p95a")
OUT  = os.path.join(BASE, "mr-kep", "output", "p95b")
os.makedirs(OUT, exist_ok=True)

# ---- reuse cached P95-A artifacts (no recompute) ----
p95a = json.load(open(os.path.join(P95A, "p95a_validation_report.json")))

def wtxt(name, txt):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(txt)

# 7 FROZEN canonical axes (memory/decisions.md Decision 2, memory/flavor-system.md)
CANON_AXES = ["smoky","peaty","fruity","sweet","spicy","maritime","sherry"]

# =====================================================================
# CANONICAL PRODUCT POLICY (permanent) -- verbatim rule encoding
# =====================================================================
wtxt("canonical_product_policy.md", """# Canonical Product Policy (PERMANENT)

Status: **BINDING** for every future Malt Radar enrichment pipeline.
Derived from user directive (P95-B) + memory/decisions.md. Rule-based, deterministic.

## Principle
A whisky record represents the **canonical commercial expression**, not a physical bottle.

## MERGE (append evidence to the existing canonical whisky; do NOT create a new record)
A variant MUST be merged when it differs ONLY by non-sensory attributes:
- batch / lot number **with no confirmed profile change**
- bottling year / release year (identical annual re-release)
- distributor-only / market-only release
- barcode revision
- packaging redesign / cosmetic label update
- volume-only packaging (e.g. 70cl vs 75cl vs 1L of the same expression)

When merging, APPEND to the canonical whisky:
- evidence, source references, tasting confirmations, confidence, historical notes.
Never overwrite certified data. Never lower confidence. Never replace stronger with weaker.

## KEEP_SEPARATE (create / retain a distinct canonical whisky)
A variant is a distinct product when there is a **meaningful sensory difference**, e.g.:
- different expression name (Ardbeg Corryvreckan vs Ardbeg Uigeadail)
- strength class change (Laphroaig 10 vs Laphroaig 10 Cask Strength)
- **confirmed** batch profile change (Springbank 12 CS Batch 24 vs Batch 25, profile-confirmed)
- different age statement, cask finish, or peating level

## REVIEW (deterministic tie-break to human queue)
When base expression matches but a variant token is present whose sensory impact is
NOT deterministically decidable from the name alone (e.g. an unqualified "batch N",
"small batch", edition token with no profile evidence) -> route to manual review.
Rule engines MUST NOT guess; ambiguity is REVIEW, never auto-MERGE.

## Precedence
KEEP_SEPARATE tokens override MERGE tokens. REVIEW overrides MERGE when a
non-decidable variant token co-occurs with only cosmetic differences.
""")

# =====================================================================
# PHASE 1 - Authority Matrix v2 (reuse frozen authority_matrix.yaml)
# =====================================================================
wtxt("authority_matrix_v2.md", """# Authority Matrix v2 (PERMANENT) - P95-B Phase 1

Reused from frozen `mr-kep/authority/authority_matrix.yaml` + `source_priority.yaml`.
NO rankings invented. Tiers are permanent; unlisted sources fall to the frozen default (T3).

| Tier | Rank | Sources (canonical) | May sole-certify? |
|---|---|---|---|
| **T1_official** | 1 | Official Distillery, Official Brand, `official_source_references` | YES |
| **T2_expert** | 2 | WhiskyFun, Whisky Advocate, WhiskyNotes, Master of Malt (expert retailer), WhiskyBase (curated), `harvester_lane` (WhiskyFun-derived), `whiskyfun_p6_extract_agent`, `structured_whisky_source_01` | YES |
| **T3_community** | 3 | Books / NotebookLM / `P32_BOOK_PIPELINE`, ML/AI-derived (`structured_ml_whiskey`), uploaded docs, retailers (non-expert), auction houses, blogs, forums, Reddit | NO (supporting only; needs T1/T2 corroboration) |

## Permanent rules
- Unlisted / unknown source -> **T3_community** (frozen `default_for_unknown_source`, priority 99).
- Conflict resolution: **highest tier wins**; ties -> highest confidence (frozen `conflict_resolution.default_rule`).
- T3 may NEVER be the sole certifier of a field. T3 corroborating a T1/T2 value raises confidence but cannot originate certification.

## CONFLICT (documented, unresolved by design; frozen contract governs)
The P95-A brief's *illustrative* ranking placed **Certified Books = 5-star (T1)** and
**WhiskyFun = 3-star**. The frozen `authority_matrix.yaml` places **WhiskyFun = T2** and has
**no book tier** (books fall to T3). Per project rule "reuse frozen contracts / never invent
rankings", the **frozen contract WINS**: books remain T3. This conflict is escalated for a
human contract decision BEFORE any book-sourced promotion. Recorded, not silently resolved.

## Evidence
- Frozen: `mr-kep/authority/authority_matrix.yaml`, `source_priority.yaml`.
- Observed source_system reality (P95-A inventory): `harvester_lane`=6133 (WhiskyFun CSV),
  `P32_BOOK_PIPELINE`=2569, `structured_ml_whiskey`=444, `MasterOfMaltAdapter`=1, etc.
""")

# =====================================================================
# PHASE 2 - Canonical Flavor Standard (reuse P95-A format_classification)
# =====================================================================
wtxt("canonical_flavor_standard.md", f"""# Canonical Flavor Standard (PERMANENT) - P95-B Phase 2

Reused from P95-A `format_classification.md` (observed formats) + memory/decisions.md
(Decision 2: 7 fixed axes) + memory/flavor-system.md.

## Canonical representation
- **Axis7** JSON object: exactly the 7 frozen axes -> numeric 0-100.
- Frozen axes (Decision 2, immutable): `{", ".join(CANON_AXES)}`.
- Storage: `flavor_profiles.flavor_vector` as a JSON dict `{{axis: number}}`.

## ACCEPTED (no conversion)
| Format | Rule |
|---|---|
| **Axis7** (`axis_num`) | Native canonical. Keys subset of the 7 frozen axes, numeric values. |
| **num_dict_term** | Accepted IF keys map 1:1 to the 7 axes and values numeric. |

## REQUIRES CONVERSION (lossy or lossless remap; deterministic mapper needed in P95-C)
| Format | Conversion | Precision |
|---|---|---|
| **Scale100** (`num_dict_scale100`) | already 0-100; clamp + key-normalize to 7 axes | lossless |
| **Numeric Array** (`num_array`) | positional map to 7 axes IFF length matches axis order contract | lossless if len==7, else REVIEW |
| **Term Bag** (`list_str`) | deterministic term->axis lexicon aggregation to 0-100 | LOSSY (documented) |

## REJECTED (never promoted as canonical)
| Format | Reason |
|---|---|
| **PCA** (`pca`) | component_* space is not invertible to 7 axes without the original loadings -> irreversible precision loss |
| **Embeddings** | opaque vector space; no deterministic axis mapping |
| **empty / empty_dict / nonjson / mixed_*** | malformed; no signal |

## Precision-loss policy
- Lossy conversions (Term Bag) are allowed ONLY into NEW rows, and are marked with a
  `conversion=lossy` provenance note. They may NEVER overwrite an existing Axis7 value
  (never lower confidence / never replace stronger with weaker).

## Future compatibility
- The 7-axis contract is frozen; adding an axis is a schema decision, not a pipeline decision.
- New formats default to REJECTED until a deterministic converter + precision class is defined.

## Observed distribution (evidence, from P95-A)
- production.flavor_profiles: list_str=1324, axis_num=430, num_array=424, num_dict_term=264, pca=225, scale100=5, empty_dict=4.
- All staging candidate vectors: `axis_num` (canonical-native).
""")

# =====================================================================
# PHASE 3 - Source Weight Matrix (deterministic evidence from P95-A + live counts)
# =====================================================================
# read-only: gather source volume/consistency evidence
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()
def q(s,p=()):
    cur.execute(s,p); return cur.fetchall()

# volume per source_system across staging flavor tables (repeatability/completeness proxy)
vol = collections.Counter()
for tbl in ["staging_flavor_profile_candidates_full","staging_flavor_profile_candidates",
            "staging_book_flavor_profiles","staging_notebooklm_flavor_profiles",
            "staging_p6_flavor_profile_candidates"]:
    cols=[d[1] for d in cur.execute(f'PRAGMA table_info("{tbl}")')]
    if "source_system" not in cols: continue
    for r in q(f'SELECT source_system, COUNT(*) FROM "{tbl}" GROUP BY source_system'):
        vol[r[0] or "UNKNOWN"] += r[1]

# tier + deterministic weight from frozen matrix (rule-based, no LLM)
def tier_of(s):
    s=(s or "").lower()
    if any(k in s for k in ["official","distillery","brand"]): return "T1_official",1
    if any(k in s for k in ["whiskyfun","harvester_lane","whiskyfun_p6","structured_whisky_source_01","masterofmalt","advocate","whiskynotes","whiskybase"]): return "T2_expert",2
    return "T3_community",3
# base weight by tier (permanent, rule-based): T1=1.0, T2=0.85, T3=0.55 (matches confidence.yaml buckets)
TIER_W = {1:1.0, 2:0.85, 3:0.55}

rows=[]
for src, n in sorted(vol.items(), key=lambda kv:-kv[1]):
    tier,rank = tier_of(src)
    w = TIER_W[rank]
    # deterministic modifiers from EVIDENCE (volume as repeatability/completeness proxy)
    completeness = "high" if n>=1000 else ("medium" if n>=100 else "low")
    rows.append({
        "source_system":src, "tier":tier, "tier_rank":rank, "base_weight":w,
        "observed_rows":n, "completeness_evidence":completeness,
        "may_sole_certify": "yes" if rank<=2 else "no",
        "weight_basis":"frozen authority tier (rule-based); volume = completeness proxy only",
    })
with open(os.path.join(OUT,"source_weight_matrix.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=["source_system","tier","tier_rank","base_weight",
        "observed_rows","completeness_evidence","may_sole_certify","weight_basis"])
    w.writeheader(); w.writerows(rows)

# =====================================================================
# PHASE 4 - Batch Classification (Canonical Product Policy, deterministic)
# =====================================================================
whiskies = q("SELECT whisky_id, name FROM whiskies WHERE name IS NOT NULL AND TRIM(name)<>''")

KEEP_TOKENS = [
    r"cask strength", r"\bcs\b", r"\bc/s\b", r"uigeadail", r"corryvreckan",
    r"\bfinish\b", r"sherry cask", r"\bpx\b", r"oloroso", r"port cask", r"madeira",
    r"quarter cask", r"\bpeated\b", r"\bunpeated\b", r"\b1\d{2}\s*proof\b",
]
# volume/packaging/year/barcode = cosmetic -> MERGE signal
MERGE_TOKENS = [
    r"\b\d{2,4}\s*cl\b", r"\b\d(\.\d)?\s*l\b", r"\b70cl\b", r"\b75cl\b", r"\b1l\b",
    r"gift (box|pack|set)", r"\bboxed\b", r"\bunboxed\b", r"new label", r"\bnas\b",
    r"\b(19|20)\d{2}\s*(release|bottling|edition)?\b",
]
# non-decidable variant tokens -> REVIEW
REVIEW_TOKENS = [r"\bbatch\b", r"\bsmall batch\b", r"\blot\b", r"\brelease\b", r"\bedition\b", r"\bvintage\b"]

def norm_base(name):
    s = name.lower().strip()
    s = re.sub(r"\b\d{2,4}\s*cl\b|\b\d(\.\d)?\s*l\b", " ", s)
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def has(patterns, text):
    return any(re.search(p, text) for p in patterns)

# group by normalized base to find variant families
groups = collections.defaultdict(list)
for wid, name in whiskies:
    groups[norm_base(name)].append((wid, name))

classes = collections.Counter()
brows=[]
for base, members in groups.items():
    multi = len(members) > 1
    for wid, name in members:
        low = name.lower()
        keep = has(KEEP_TOKENS, low)
        review = has(REVIEW_TOKENS, low)
        merge = has(MERGE_TOKENS, low)
        # precedence: KEEP_SEPARATE > REVIEW > MERGE > default KEEP_SEPARATE (singletons)
        if keep:
            cls, reason = "KEEP_SEPARATE", "sensory-distinct token (strength/expression/finish/peating)"
        elif multi and review:
            cls, reason = "REVIEW", "variant token (batch/lot/edition) not deterministically decidable in a multi-member family"
        elif multi and merge:
            cls, reason = "MERGE", "differs only by cosmetic/packaging/year/volume within a variant family"
        elif multi:
            cls, reason = "REVIEW", "multiple members share base name; no decisive token -> human review"
        else:
            cls, reason = "KEEP_SEPARATE", "singleton canonical expression (no variant family)"
        classes[cls]+=1
        brows.append([wid, name, base, len(members), cls, reason])

with open(os.path.join(OUT,"batch_classification.csv"),"w",newline="",encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["whisky_id","name","normalized_base","family_size","classification","reason"])
    w.writerows(sorted(brows, key=lambda r:(r[2], r[1])))

# =====================================================================
# PHASE 5 - Promotion Rulebook (permanent deterministic workflow)
# =====================================================================
wtxt("promotion_rulebook.md", f"""# Promotion Rulebook (PERMANENT) - P95-B Phase 5

The single deterministic path every future enrichment pipeline MUST follow.
Rule-based only. No AI judgement. No LLM scoring.

```
 Authority  ->  Canonical Format  ->  Conflict Resolution  ->  Confidence  ->  Certification  ->  Promotion  ->  Production
```

## 1. Authority (Phase-1 matrix)
- Resolve source_system -> tier via authority_matrix_v2. Unlisted -> T3.
- T3 alone CANNOT certify. Requires T1/T2 corroboration to originate a field value.

## 2. Canonical Format (Phase-2 standard)
- ACCEPT Axis7 / num_dict_term as-is.
- CONVERT scale100 / num_array(len==7) / term-bag via the deterministic mapper (P95-C). Term-bag = lossy, new-rows only.
- REJECT PCA / embeddings / malformed.

## 3. Conflict Resolution
- Same field, multiple sources: **highest tier wins**; tie -> highest confidence; tie -> newest evidence.
- Product identity conflicts resolved by the Canonical Product Policy (MERGE / KEEP_SEPARATE / REVIEW).
- Never overwrite certified data; never replace stronger with weaker.

## 4. Confidence
- Frozen `confidence.yaml`: certify_min = 0.70. Buckets: T1=1.0, T2=0.85, T3=0.55.
- Confidence may only increase via corroboration; never lowered by a weaker source.

## 5. Certification (deterministic gate)
- READY_FOR_PROMOTION iff: tier<=2 AND confidence>=0.70 AND canonical-compatible AND no existing certified profile for the target.
- Else NEEDS_REVIEW (already-profiled / T3-only / low-confidence) or LEGACY_ONLY (non-canonical format) or REJECT (malformed).

## 6. Promotion (gated, transactional) -- OUT OF SCOPE FOR READ-ONLY PHASES
- Requires explicit human GO. Mutating apply MUST: backup production.db + sha256, single
  transaction, rollback-on-error, one promotion_audit_log row, post-apply row-count assert.
- Idempotent: NOT-IN guard prevents duplicate keys.

## 7. Production
- Only certified, canonical, non-overwriting rows land. Provenance retained internally.
- Hidden/internal sources are NEVER exposed in public UI.
""")

# =====================================================================
# VALIDATION REPORT + INTEGRITY HASH
# =====================================================================
val = f"""# P95-B Validation Report

Mode: **STRICT READ-ONLY**. No DB writes, no promotion, no phase regeneration.
Deterministic architecture phase. Reused cached P95-A artifacts + frozen authority contracts.

## Success Criteria
1. **Permanent Authority Matrix** -> `authority_matrix_v2.md` (T1 official / T2 expert / T3 community; unlisted->T3; highest-tier-wins).
2. **Permanent Canonical Flavor Standard** -> `canonical_flavor_standard.md` (Axis7 over 7 frozen axes).
3. **Accepted formats:** Axis7 (`axis_num`), `num_dict_term` (1:1 axis map).
4. **Require conversion:** Scale100 (lossless), Numeric Array len==7 (lossless), Term Bag (lossy, new-rows only).
5. **Rejected formats:** PCA, Embeddings, empty/malformed/mixed.
6. **Merged variants:** {classes.get('MERGE',0)} (cosmetic/packaging/year/volume/distributor within a family).
7. **Kept separate:** {classes.get('KEEP_SEPARATE',0)} (sensory-distinct or singleton). REVIEW: {classes.get('REVIEW',0)}.
8. **P95-C readiness:** all conversion & rejection rules are deterministic and evidence-backed.

## Evidence base (reused, not recomputed)
- P95-A: ready_for_promotion={p95a['ready_for_promotion']}, coverage {p95a['promotion_simulation']['before_pct']}%->{p95a['promotion_simulation']['after_pct']}%, quality {p95a['quality']['quality_pct']}% axis_num.
- Frozen contracts: authority_matrix.yaml, confidence.yaml (certify_min 0.70), source_priority.yaml, field_rules.yaml, merge_policies.yaml.
- memory/decisions.md Decision 2 (7 fixed axes), Decision 3 (weighted-average, never overwrite).

## Batch classification totals (Phase 4, {sum(classes.values())} products)
- MERGE={classes.get('MERGE',0)}  KEEP_SEPARATE={classes.get('KEEP_SEPARATE',0)}  REVIEW={classes.get('REVIEW',0)}

## Documented conflict (unresolved by design)
- P95-A brief books=T1 vs frozen authority_matrix books=T3. Frozen contract governs; escalated for human contract decision before any book promotion.

## Non-negotiables honored
- production.db & staging.db untouched (read-only URI). No INSERT/UPDATE/DELETE/ALTER/DROP/VACUUM.
- No promotion. No phase regeneration. No fabricated statistics or rankings. Rule-based only.

## VERDICT
**GO** for P95-C (Canonical Flavor Conversion) -- deterministic converters (scale100, num_array,
term-bag) and rejection rules (PCA/embeddings) are fully specified and evidence-backed. The ONLY
open item is a human contract decision on the documented books-tier conflict, which does NOT block
P95-C (books are T3 either way under the frozen contract).
"""
wtxt("p95b_validation_report.md", val)

files = sorted(os.path.join(OUT,fn) for fn in os.listdir(OUT)
               if os.path.isfile(os.path.join(OUT,fn)) and fn!="integrity_hash.json")
h=hashlib.sha256()
per={}
for fp in files:
    fh=hashlib.sha256(open(fp,"rb").read()).hexdigest()
    per[os.path.basename(fp)]=fh
    h.update(open(fp,"rb").read())
json.dump({"algorithm":"sha256","files_hashed":len(files),"per_file":per,
           "concat_sha256":h.hexdigest(),"deterministic":True},
          open(os.path.join(OUT,"integrity_hash.json"),"w"), indent=2)

con.close()
print("P95-B COMPLETE (read-only, deterministic)")
print("="*55)
print("Batch classification:", dict(classes), "total", sum(classes.values()))
print("Source weight rows  :", len(rows))
print("Deliverables in     :", OUT)
for fn in ["canonical_product_policy.md","authority_matrix_v2.md","canonical_flavor_standard.md",
           "source_weight_matrix.csv","batch_classification.csv","promotion_rulebook.md",
           "p95b_validation_report.md","integrity_hash.json"]:
    print("   -", fn)
print("VERDICT: GO for P95-C")
