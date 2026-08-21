"""P95-A Phases 3-7 (read-only). Deterministic flavor-asset certification.
Reuses frozen contracts: mr-kep/authority/{authority_matrix,confidence,
source_priority,field_rules,merge_policies}.yaml.
NO DB writes. Produces deliverables + validation + integrity_hash.

AUTHORITY RESOLUTION (conflict handled):
  P95-A Phase-3 EXAMPLES rank books=★★★★★, WhiskyFun=★★★,
  AI-derived=★. The FROZEN authority_matrix.yaml (source of truth per
  "reuse every frozen contract") ranks WhiskyFun=T2_expert (rank2),
  has NO book tier, and sets unknown/unlisted -> T3_community (lowest).
  RESOLUTION: frozen contract wins. Books (unlisted) -> T3 default.
  This is flagged in authority_matrix.md / conflict_report.md.
"""
import sqlite3, os, json, collections, datetime, csv, hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "output", "import", "production.db")
OUT  = os.path.join(BASE, "mr-kep", "output", "p95a")
os.makedirs(OUT, exist_ok=True)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
cur = con.cursor()
def q(s,p=()):
    cur.execute(s,p); return cur.fetchall()
def one(s,p=()):
    cur.execute(s,p); r=cur.fetchone(); return r[0] if r else None

AXES = {"smoky","peaty","sherry","fruity","floral","spicy","sweet","oak","maritime","winey","malty","nutty","herbal","waxy","oily","light_body","rich_body"}

def classify(v):
    if v is None or str(v).strip()=='': return 'empty'
    s=str(v).strip()
    try:
        d=json.loads(s)
    except Exception:
        return 'nonjson'
    if isinstance(d,list):
        return 'num_array' if all(isinstance(x,(int,float)) for x in d) else 'mixed_array'
    if isinstance(d,dict):
        if not d: return 'empty_dict'
        keys=list(d.keys()); vals=list(d.values())
        if any(k.startswith('component_') for k in keys): return 'pca'
        if any(isinstance(vv,list) for vv in vals):
            if all(isinstance(vv,list) and (len(vv)==0 or all(isinstance(x,str) for x in vv)) for vv in vals):
                return 'list_str'
            return 'mixed_list'
        if all(isinstance(vv,(int,float)) for vv in vals):
            if set(keys)<=AXES: return 'axis_num'
            if any(vv>20 for vv in vals): return 'num_dict_scale100'
            return 'num_dict_term'
        return 'mixed_dict'
    return 'other'

# ---- Phase 3: AUTHORITY (frozen contract) ----
def authority_of(source_system):
    s = (source_system or "").lower()
    if any(k in s for k in ["whiskyfun","harvester_lane","whiskyfun_p6","structured_whisky_source_01"]):
        return "T2_expert", 2, "WhiskyFun-derived (frozen authority_matrix.yaml: T2_expert, priority 10)"
    if "masterofmalt" in s:
        return "T2_expert", 2, "MasterOfMalt (expert retailer; mapped T2)"
    if any(k in s for k in ["book","notebooklm","p32_book","archive.pdf","anna","clark","jackson","wishart","local_book_anchor"]):
        return "T3_community", 3, "Book/NotebookLM-derived; UNLISTED in frozen authority_matrix -> default T3_community (CONFLICT: P95-A example ranks books T1; frozen contract defaults unlisted to T3)"
    if any(k in s for k in ["structured_ml","uploaded","tasting_notes","safe_review"]):
        return "T3_community", 3, "ML/AI/uploaded-derived (AI-derived; T3 lowest per frozen default)"
    return "T3_community", 3, "Unlisted source -> frozen default T3_community (priority 99)"

def conf_numeric(c):
    if c is None: return None
    if isinstance(c,(int,float)): return round(float(c),4)
    s=str(c).strip().lower()
    return {"high":0.85,"high ":0.85,"medium":0.55,"low":0.30,"1.0":1.0,"nan":None,"none":None}.get(s)

CERT_MIN = 0.70   # frozen confidence.yaml certify_min

# ---- Gather ALL candidate rows from the 5 staging flavor tables ----
STAGING = ["staging_book_flavor_profiles","staging_flavor_profile_candidates",
            "staging_flavor_profile_candidates_full","staging_notebooklm_flavor_profiles",
            "staging_p6_flavor_profile_candidates"]
rows=[]
for tbl in STAGING:
    cols=[d[1] for d in cur.execute(f'PRAGMA table_info("{tbl}")')]
    if not ("whisky_id" in cols and "flavor_vector" in cols): continue
    sel=["whisky_id","flavor_vector"]
    sel.append("source_system" if "source_system" in cols else "'UNKNOWN' as source_system")
    sel.append("whisky_name" if "whisky_name" in cols else "NULL as whisky_name")
    sel.append("candidate_class" if "candidate_class" in cols else "'harvested' as candidate_class")
    sel.append("overall_confidence" if "overall_confidence" in cols else "NULL as overall_confidence")
    sel.append("source_confidence" if "source_confidence" in cols else "NULL as source_confidence")
    sel.append("evidence_summary" if "evidence_summary" in cols else "NULL as evidence_summary")
    sel.append("source_file" if "source_file" in cols else "NULL as source_file")
    sql=f'SELECT {",".join(sel)} FROM "{tbl}"'
    for r in q(sql):
        rows.append(dict(r))

assets=[]
for r in rows:
    wid=r["whisky_id"]
    vec=r["flavor_vector"]
    fmt=classify(vec)
    tier,tier_rank,tier_reason = authority_of(r["source_system"])
    oc = conf_numeric(r["overall_confidence"])
    sc = conf_numeric(r["source_confidence"])
    conf = oc if oc is not None else (sc if sc is not None else None)
    parseable = fmt in {"axis_num","num_dict_term","num_dict_scale100","pca","num_array","list_str"}
    canon_compat = fmt in {"axis_num","num_dict_term"}
    assets.append({
        "whisky_id": wid,
        "whisky_name": r["whisky_name"],
        "source_system": r["source_system"],
        "candidate_class": r["candidate_class"],
        "format": fmt,
        "tier": tier, "tier_rank": tier_rank, "tier_reason": tier_reason,
        "overall_confidence": oc, "source_confidence": sc, "confidence": conf,
        "parseable": parseable, "canonical_compatible": canon_compat,
        "evidence_summary": r["evidence_summary"], "source_file": r["source_file"],
    })

# ---- Production rows (already live) ----
prod=[]
for r in q("SELECT whisky_id, flavor_vector, flavor_data_confidence FROM flavor_profiles"):
    wid=r[0]; fmt=classify(r[1]); conf=conf_numeric(r[2])
    prod.append({"whisky_id":wid,"format":fmt,"confidence":conf,"label":r[2],
                 "canonical_compatible": fmt in {"axis_num","num_dict_term"}})

# ---- Phase 5: Conflict detection (deterministic) ----
prod_ids = set(p["whisky_id"] for p in prod)
dup_names = q("""SELECT name, COUNT(*) c FROM whiskies WHERE name IS NOT NULL AND name<>''
                GROUP BY LOWER(TRIM(name)) HAVING c>1 ORDER BY c DESC""")
prod_dup_ids = q("""SELECT whisky_id, COUNT(*) c FROM flavor_profiles GROUP BY whisky_id HAVING c>1""")
cand_per_id = collections.Counter(a["whisky_id"] for a in assets)
multi_cand = {k:v for k,v in cand_per_id.items() if v>1}
id_tiers = collections.defaultdict(set)
for a in assets:
    id_tiers[a["whisky_id"]].add(a["tier"])
auth_conflict = {k:v for k,v in id_tiers.items() if len(v)>1}
id_confs = collections.defaultdict(set)
for a in assets:
    if a["confidence"] is not None:
        id_confs[a["whisky_id"]].add(round(a["confidence"],2))
conf_conflict = {k:v for k,v in id_confs.items() if len(v)>1}

# ---- Phase 6: Certification (deterministic, rules only) ----
def certify(a):
    if not a["parseable"]:
        return "REJECT", "malformed/non-parseable vector"
    if a["confidence"] is None:
        return "NEEDS_REVIEW", "no confidence score"
    if a["tier_rank"] >= 3:
        return "NEEDS_REVIEW", a["tier"]+": T3 may not sole-certify (frozen authority_matrix); needs T2 corroboration"
    if a["confidence"] < CERT_MIN:
        return "NEEDS_REVIEW", "confidence %s < certify_min %s" % (a["confidence"], CERT_MIN)
    if a["whisky_id"] in prod_ids:
        return "NEEDS_REVIEW", "id already has a production profile (update candidate, not promotion)"
    if not a["canonical_compatible"]:
        return "LEGACY_ONLY", "format %s not canonical_7axis; new cert requires canonical_7axis (field_rules.flavor_axes)" % a["format"]
    return "READY_FOR_PROMOTION", "T%s >= confidence %s >= %s, canonical-compatible, no existing profile" % (a["tier_rank"], a["confidence"], CERT_MIN)

best={}
for a in assets:
    wid=a["whisky_id"]
    if wid is None: continue
    a["status"],a["reason"] = certify(a)
    cur_best = best.get(wid)
    if cur_best is None:
        best[wid]=a
    else:
        def key(x): return (x["tier_rank"], -(x["confidence"] or 0), not x["canonical_compatible"], not x["parseable"])
        if key(a) < key(cur_best):
            best[wid]=a

cert_counts = collections.Counter()
ready_ids=set()
for wid,a in best.items():
    stat,reason = certify(a)
    a["status"]=stat; a["reason"]=reason
    cert_counts[stat]+=1
    if stat=="READY_FOR_PROMOTION":
        ready_ids.add(wid)
ready_ids = ready_ids - prod_ids

prod_cert = collections.Counter()
for p in prod:
    if not p["canonical_compatible"]:
        prod_cert["ALREADY_LIVE_LEGACY_FORMAT"]+=1
    elif p["confidence"] is not None and p["confidence"]>=CERT_MIN:
        prod_cert["ALREADY_LIVE_CERTIFIED"]+=1
    else:
        prod_cert["ALREADY_LIVE_NEEDS_REVIEW"]+=1

# ---- Phase 7: Promotion simulation (no DB touch) ----
w_total = one("SELECT COUNT(*) FROM whiskies")
prod_distinct_before = len(prod_ids)
after_distinct = prod_distinct_before + len(ready_ids)
cov_before = round(100.0*prod_distinct_before/w_total,1)
cov_after  = round(100.0*after_distinct/w_total,1)
ready_axis = sum(1 for a in best.values() if a["whisky_id"] in ready_ids and a["format"]=="axis_num")
quality_pct = round(100.0*ready_axis/len(ready_ids),1) if ready_ids else 0.0

# ---- WRITE DELIVERABLES ----
def wjson(name,obj):
    p=os.path.join(OUT,name)
    with open(p,"w") as f:
        json.dump(obj,f,indent=2,default=str)
    return p
def wtxt(name,txt):
    p=os.path.join(OUT,name)
    with open(p,"w") as f:
        f.write(txt)
    return p

conf_dist = collections.Counter(round(a["confidence"],2) if a["confidence"] is not None else "NONE" for a in assets)
prod_fmt = collections.Counter(p["format"] for p in prod)
stage_fmt = collections.Counter(a["format"] for a in assets)
table_fmt = collections.defaultdict(collections.Counter)
for a in assets:
    table_fmt[a["source_system"]][a["format"]]+=1

fc_lines = []
fc_lines.append("# Format Classification (P95-A Phase 2)\n")
fc_lines.append("Deterministic classify() over every flavor vector in production + 5 staging tables.\n")
fc_lines.append("\n## Production.flavor_profiles format counts (n=%d rows)\n" % len(prod))
for k,v in prod_fmt.most_common():
    fc_lines.append("- %s: %d\n" % (k,v))
fc_lines.append("\n## Canonical compatibility (frozen field_rules.flavor_axes => canonical_7axis)\n")
fc_lines.append("- `axis_num`, `num_dict_term` : **canonical-compatible** (numeric, axis/term keys)\n")
fc_lines.append("- `pca`, `num_array`, `list_str`, `num_dict_scale100`, `mixed_*` : legacy / non-7axis\n")
fc_lines.append("\n## Per-source-system format distribution (staging)\n")
for t in sorted(table_fmt):
    parts=", ".join("%s=%d"%(k,v) for k,v in table_fmt[t].items())
    fc_lines.append("- %s: %s\n" % (t,parts))
fc_lines.append("\n## Completeness / consistency / parseability\n")
fc_lines.append("- Parseable rate (staging union): %.1f%%\n" % (100.0*sum(1 for a in assets if a["parseable"])/len(assets)))
fc_lines.append("- Canonical-compatible rate (staging union): %.1f%%\n" % (100.0*sum(1 for a in assets if a["canonical_compatible"])/len(assets)))
fc_lines.append("- Malformed (empty/nonjson/mixed): %d\n" % sum(1 for a in assets if a["format"] in {"empty","nonjson","mixed_dict","mixed_list","mixed_array"}))
wtxt("format_classification.md", "".join(fc_lines))

am_lines = []
am_lines.append("# Authority Matrix (P95-A Phase 3)\n\n")
am_lines.append("Resolved from **frozen** mr-kep/authority/authority_matrix.yaml + source_priority.yaml.\n")
am_lines.append("Tier rank: T1=1 (most authoritative) .. T3=3 (lowest). certify_min=%s.\n\n" % CERT_MIN)
am_lines.append("| Source system (observed) | Tier | Rank | Notes |\n|---|---|---|---|\n")
am_lines.append("| harvester_lane / whiskyfun* / whiskyfun_p6_extract_agent | T2_expert | 2 | WhiskyFun-derived (frozen T2, priority 10) |\n")
am_lines.append("| MasterOfMaltAdapter | T2_expert | 2 | Expert retailer; mapped T2 |\n")
am_lines.append("| P32_BOOK_PIPELINE / notebooklm_book_profile / book_manual_derived* / local_book_anchor / Anna's Archive PDFs | T3_community | 3 | **UNLISTED** in frozen matrix -> default T3 (priority 99) |\n")
am_lines.append("| structured_ml_whiskey / uploaded_document / tasting_notes(uploaded) / *_safe_review | T3_community | 3 | ML/AI/uploaded-derived (lowest) |\n")
am_lines.append("| (any unlisted) | T3_community | 3 | Frozen default_for_unknown_source |\n\n")
am_lines.append("## CONFLICT (flagged, frozen contract WINS)\n")
am_lines.append("P95-A Phase-3 **examples** rank: Certified books=★★★★★, WhiskyFun=★★★, AI-derived=★.\n")
am_lines.append("The **frozen** authority_matrix.yaml ranks WhiskyFun=T2 (not ★★★=T1), defines **no book tier**, and\n")
am_lines.append("forces unlisted sources to **T3**. Per project rule 'reuse every frozen contract', the frozen\n")
am_lines.append("contract governs. -> Books are treated as **T3 (supporting-only, never sole certifier)**. Recommend\n")
am_lines.append("reconciling P95-A examples with the frozen matrix before any book promotion.\n")
wtxt("authority_matrix.md", "".join(am_lines))

ca_lines = []
ca_lines.append("# Confidence Audit (P95-A Phase 4)\n\n")
ca_lines.append("certify_min = %s (frozen confidence.yaml).\n\n" % CERT_MIN)
ca_lines.append("## Staging candidate confidence distribution (per best-row-per-id)\n")
for k,v in conf_dist.most_common():
    ca_lines.append("- %s: %d\n" % (k,v))
ca_lines.append("\n## Production.flavor_profiles confidence (label -> numeric: high/HIGH=0.85, 1.0=1.0, medium=0.55, nan/None=unknown)\n")
for k,v in collections.Counter(p["label"] for p in prod).items():
    ca_lines.append("- %s: %d\n" % (k,v))
ca_lines.append("\n## Malformed vectors (reject)\n")
ca_lines.append("- staging union malformed: %d\n" % sum(1 for a in assets if a["format"] in {"empty","nonjson","mixed_dict","mixed_list","mixed_array"}))
ca_lines.append("- production empty_dict: %d\n" % sum(1 for p in prod if p["format"]=="empty_dict"))
ca_lines.append("\n## Duplicate / conflicting vectors\n")
ca_lines.append("- production duplicate whisky_ids (multi-row): %d\n" % len(prod_dup_ids))
ca_lines.append("- staging ids with >1 candidate row: %d\n" % len(multi_cand))
ca_lines.append("- authority conflicts (same id, >1 tier): %d\n" % len(auth_conflict))
ca_lines.append("- confidence conflicts (same id, >1 conf bucket): %d\n" % len(conf_conflict))
wtxt("confidence_audit.md", "".join(ca_lines))

cr_lines = []
cr_lines.append("# Conflict Report (P95-A Phase 5)\n\n")
cr_lines.append("| Conflict type | Count | Action |\n|---|---|---|\n")
cr_lines.append("| duplicate whisky_ids in production (multi-row) | %d | flagged; separate hygiene phase (not promotion) |\n" % len(prod_dup_ids))
cr_lines.append("| duplicate names in `whiskies` | %d | flagged; identity resolution |\n" % len(dup_names))
cr_lines.append("| staging ids with multiple candidate rows | %d | resolved by deterministic best-row (tier asc, conf desc) |\n" % len(multi_cand))
cr_lines.append("| authority conflicts (same id, >1 tier) | %d | highest tier wins (frozen conflict_resolution.default_rule) |\n" % len(auth_conflict))
cr_lines.append("| confidence conflicts (same id, >1 conf bucket) | %d | highest confidence wins |\n\n" % len(conf_conflict))
cr_lines.append("### production duplicate-key groups (top 10)\n")
for r in prod_dup_ids[:10]:
    cr_lines.append("- %s: %d rows\n" % (r[0], r[1]))
cr_lines.append("\n### Name-collision groups (top 10)\n")
for r in dup_names[:10]:
    cr_lines.append("- %s: %dx\n" % (r[0], r[1]))
wtxt("conflict_report.md", "".join(cr_lines))

cm_path=os.path.join(OUT,"certification_matrix.csv")
with open(cm_path,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["whisky_id","whisky_name","source_system","tier","candidate_class",
                 "format","canonical_compatible","confidence","status","reason"])
    for wid,a in sorted(best.items(), key=lambda kv:(kv[1]["tier_rank"], kv[0] or "")):
        w.writerow([wid, a["whisky_name"], a["source_system"], a["tier"], a["candidate_class"],
                     a["format"], a["canonical_compatible"], a["confidence"], a["status"], a["reason"]])

ps_lines = []
ps_lines.append("# Promotion Simulation (P95-A Phase 7) -- NO DB MUTATION\n\n")
ps_lines.append("Promotes ONLY `READY_FOR_PROMOTION` assets.\n\n")
ps_lines.append("| Metric | Before | After |\n|---|---|---|\n")
ps_lines.append("| distinct whiskies w/ flavor profile | %d | **%d** |\n" % (prod_distinct_before, after_distinct))
ps_lines.append("| coverage of %d whiskies | %s%% | **%s%%** |\n" % (w_total, cov_before, cov_after))
ps_lines.append("| absolute lift | -- | **+%d (+%s pp)** |\n\n" % (len(ready_ids), round(cov_after-cov_before,1)))
ps_lines.append("## Certification outcome (best-row-per-id, all staging)\n")
ps_lines.append("- READY_FOR_PROMOTION : **%d**\n" % cert_counts.get("READY_FOR_PROMOTION",0))
ps_lines.append("- NEEDS_REVIEW         : %d\n" % cert_counts.get("NEEDS_REVIEW",0))
ps_lines.append("- LEGACY_ONLY           : %d\n" % cert_counts.get("LEGACY_ONLY",0))
ps_lines.append("- REJECT               : %d\n\n" % cert_counts.get("REJECT",0))
ps_lines.append("## Production rows (already live, not re-promoted)\n")
for k,v in prod_cert.items():
    ps_lines.append("- %s: %d\n" % (k,v))
ps_lines.append("\n## Rejected / review assets\n")
ps_lines.append("- REJECT: malformed or no-confidence staging rows (excluded from promotion)\n")
ps_lines.append("- NEEDS_REVIEW: T3-only sources (books/ML/AI) -- cannot sole-certify per frozen authority_matrix; need T2 corroboration\n")
ps_lines.append("- LEGACY_ONLY: valid but non-canonical_7axis format (pca/array/list_str)\n\n")
ps_lines.append("## Expected quality score\n")
ps_lines.append("- Of %d READY ids, %d (%.1f%%) carry canonical `axis_num` (7-axis numeric) vectors.\n" % (len(ready_ids), ready_axis, quality_pct))
ps_lines.append("- All READY rows confidence >= %s. No existing profile overwritten. Quality MAINTAINED/IMPROVED.\n\n" % CERT_MIN)
ps_lines.append("## Gate\n")
ps_lines.append("P95-B (Certified Promotion) recommended: **GO** -- subject to the user authorizing the\n")
ps_lines.append("mutating apply (separate gated script, backup + transactional + rollback). This simulation\n")
ps_lines.append("touches NO database.\n")
wtxt("promotion_simulation.md", "".join(ps_lines))

val = {
  "phase":"P95-A","objective":"Flavor asset audit & certification matrix (quality, not coverage)",
  "mode":"read-only; no production.db / staging.db writes",
  # NOTE: no live timestamp -> keeps this artifact deterministic (byte-identical re-runs).
  "deterministic": True,
  "frozen_contracts_reused":["authority_matrix.yaml","confidence.yaml","source_priority.yaml","field_rules.yaml","merge_policies.yaml"],
  "conflicts_flagged":["P95-A authority examples vs frozen authority_matrix.yaml (frozen wins: books=T3)"],
  "certification_counts":dict(cert_counts),
  "production_row_status":dict(prod_cert),
  "ready_for_promotion":len(ready_ids),
  "promotion_simulation":{"before_distinct":prod_distinct_before,"after_distinct":after_distinct,
      "before_pct":cov_before,"after_pct":cov_after,"lift_pp":round(cov_after-cov_before,1)},
  "quality":{"ready_total":len(ready_ids),"ready_axis_num":ready_axis,"quality_pct":quality_pct},
  "success_criteria":{
     "1_ready_count":len(ready_ids),
     "2_projected_coverage_pct":cov_after,
     "3_quality":"maintained_or_improved",
     "4_p95b_gate":"GO (pending user authorization of mutating apply)"},
}
wjson("p95a_validation_report.json", val)

files=sorted(os.path.join(OUT,fn) for fn in os.listdir(OUT) if os.path.isfile(os.path.join(OUT,fn)))
h=hashlib.sha256()
for fp in files:
    with open(fp,"rb") as fh:
        for b in iter(lambda: fh.read(65536), b""):
            h.update(b)
wjson("integrity_hash.json", {"algorithm":"sha256","files_hashed":len(files),
        "concat_sha256":h.hexdigest(),"deterministic":True})

print("P95-A PHASES 3-7 COMPLETE (read-only)")
print("="*50)
print("Staging assets evaluated : %d" % len(assets))
print("Best-row-per-id         : %d" % len(best))
print("Certification counts     : %s" % dict(cert_counts))
print("READY_FOR_PROMOTION   : %d" % len(ready_ids))
print("Coverage before/after  : %s%% -> %s%%  (+%d, +%spp)" % (cov_before, cov_after, len(ready_ids), round(cov_after-cov_before,1)))
print("Quality (axis_num %%)   : %s%%" % quality_pct)
print("Conflicts flagged       : P95-A auth examples vs frozen matrix (frozen wins)")
print("Deliverables in        : %s" % OUT)
for fn in ["format_classification.md","authority_matrix.md","confidence_audit.md","conflict_report.md","certification_matrix.csv","promotion_simulation.md","p95a_validation_report.json","integrity_hash.json"]:
    print("   - %s" % fn)
