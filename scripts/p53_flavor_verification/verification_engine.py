# =============================================================================
# P53 - Flavor & Tasting Verification Engine (READ-ONLY)
# -----------------------------------------------------------------------------
# Reads production.db via a temp copy (never the live file), plus the P52 ledger
# for cross-reference. Emits a P53 verification ledger + conflict/manual/low-conf
# queues. Also derives recommendation neighbors (cosine over 7-axis flavor_profile)
# for the impact analyzer. No writes to production data, ever.
# =============================================================================

import sqlite3
import csv
import json
import os
import sys
import shutil
import tempfile
import math
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config.source_authority_matrix as M

CON = None  # module-level handle to temp db copy


def _prepare_db_copy():
    """Copy live DB to a temp file so the live file is NEVER opened/written.
    Returns path to the temp copy; cleaned up by caller."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db",
                                      prefix="p53_prod_", dir=tempfile.gettempdir())
    tmp.close()
    shutil.copyfile(M.LIVE_DB, tmp.name)
    return tmp.name


def _norm_conf(v):
    return M._norm_conf(v)


def _parse_json(s):
    if not s:
        return {}
    try:
        d = json.loads(s)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _to_float(x):
    try:
        if x is None or x == "":
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def _axis_vec(d):
    """Build a fixed-length 7-axis vector from a flavor_profile dict."""
    return [float(d.get(a, 0) or 0) for a in M.PROFILE_AXES]


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------
def verify():
    tmp = _prepare_db_copy()
    global CON
    CON = sqlite3.connect(tmp)
    CON.text_factory = str
    cur = CON.cursor()

    ledger = []          # per-row verification records
    conflicts = []       # (entity, wid, name, field, current, authority, note)
    manual = []          # manual_review_queue rows
    low_conf = []        # low_confidence_flavors rows
    tn_conflicts = []    # tasting note conflicts
    missing = []         # missing flavor profiles
    disagreements = []   # source disagreements (low tier asserting high)

    def add(entity, wid, name, field, value, status, conf, src, prov, note):
        ledger.append({
            "entity": entity, "entity_id": wid, "entity_name": name,
            "field": field, "current_value": value, "verification_status": status,
            "confidence": conf, "authority_source": src or "legacy_repository",
            "provenance": prov or "", "last_verified": M.RUN_DATE, "note": note,
        })
        if conf == "X":
            conflicts.append((entity, wid, name, field, value, src, note))
            manual.append({"entity": entity, "entity_id": wid, "entity_name": name,
                           "field": field, "current_value": value,
                           "verification_status": "conflict", "confidence": "X",
                           "authority_source": src or "legacy_repository",
                           "note": note, "manual_review_required": "true"})
        elif status == "unverified":
            manual.append({"entity": entity, "entity_id": wid, "entity_name": name,
                           "field": field, "current_value": value,
                           "verification_status": "unverified", "confidence": conf,
                           "authority_source": src or "legacy_repository",
                           "note": note, "manual_review_required": "true"})

    # ---------------- FLAVOR PROFILES ----------------
    cur.execute("SELECT whisky_id, whisky_name, flavor_profile, flavor_vector, "
                "flavor_tags, flavor_source, flavor_data_confidence, source_count "
                "FROM flavor_profiles")
    fps = cur.fetchall()
    axis_rows = []  # (wid, name, vec7, src_family, tier, conf_letter) for impact
    prod_by_key = defaultdict(list)  # batch-policy grouping

    for wid, name, fp, fv, ft, src, conf, sc in fps:
        fam, tier = M.source_family(src)
        conf_label = _norm_conf(conf)
        ai = M.is_ai_source(src)
        prof = _parse_json(fp)
        vec = _parse_json(fv)
        v7 = _axis_vec(prof)
        has_profile = any(v7)
        # confidence decision
        cl, status, note = M.flavor_confidence(src, conf_label)
        # record 7-axis values individually
        if has_profile:
            for ax in M.PROFILE_AXES:
                val = prof.get(ax, 0) or 0
                if val:
                    add("flavor", wid, name, f"axis:{ax}", val, status, cl, src, src, note)
            axis_rows.append((wid, name, v7, fam, tier, cl))
        else:
            missing.append({"entity": "flavor", "entity_id": wid, "entity_name": name,
                            "field": "flavor_profile", "current_value": "",
                            "authority_source": src or "legacy_repository",
                            "note": "flavor_profile empty / all-zero"})
            add("flavor", wid, name, "flavor_profile", "(empty)", "unverified", "D",
                src, src, "flavor_profile empty")
        # vector-level requested terms (smoky/peaty/sherry/maritime etc.)
        for term in M.VECTOR_TERMS:
            tv = vec.get(term)
            if tv is not None:
                tfam, ttier = M.source_family(src)
                if ai:
                    add("flavor_vector", wid, name, f"term:{term}", tv, "unverified",
                        "E", src, src, "vector term from AI/legacy source")
                else:
                    add("flavor_vector", wid, name, f"term:{term}", tv, status, cl,
                        src, src, note)
        # low confidence flag
        if cl in ("D", "E") or status == "unverified":
            low_conf.append({"entity_id": wid, "entity_name": name,
                             "field": "flavor_profile", "confidence": cl,
                             "authority_source": src or "legacy_repository",
                             "data_confidence": conf or "", "source_count": sc or 0,
                             "note": note})
        # AI labelled high -> disagreement (source disagreement)
        if ai and conf_label == "high":
            disagreements.append((wid, name, "flavor_data_confidence", conf,
                                  "low (tier 9)", src, "label_policy"))
        # batch policy grouping by normalized name prefix
        base = (name or "").lower()
        for tok in ("year old", "yo", "cask", "edition", "batch", "release"):
            base = base.replace(tok, "")
        prod_by_key[base.split("(")[0].strip()[:20]].append((wid, name, v7, cl, tier))

    # ---------------- BATCH POLICY: divergent same-key profiles ----------------
    batch_flags = []
    for key, rows in prod_by_key.items():
        if len(rows) < 2:
            continue
        vecs = [r[2] for r in rows]
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                c = _cosine(vecs[i], vecs[j])
                if c < 0.85:  # meaningfully different flavor despite same key
                    batch_flags.append((rows[i][0], rows[i][1], rows[j][0], rows[j][1], round(c, 3)))
                    manual.append({"entity": "flavor_batch", "entity_id": rows[i][0],
                                   "entity_name": rows[i][1], "field": "batch_policy",
                                   "current_value": f"similar key to {rows[j][1]} cosine={round(c,3)}",
                                   "verification_status": "review", "confidence": "X",
                                   "authority_source": "batch_policy",
                                   "note": "same product key, divergent flavor profile -> verify real batch difference",
                                   "manual_review_required": "true"})

    # ---------------- TASTING NOTES ----------------
    cur.execute("SELECT whisky_id, normalized_name, distillery_id, source_url, "
                "source_name, data_confidence, nose_notes, palate_notes, finish_notes, "
                "source_system, source_doc FROM tasting_notes")
    for wid, nname, did, surl, sname, dconf, nose, palate, finish, ssys, sdoc in cur.fetchall():
        fam, tier = M.source_family(ssys or sname or "")
        ai = M.is_ai_source(ssys or "")
        c_letter = "C" if not ai else "E"
        add("tasting", wid, nname, "nose", (nose or "")[:80], "verified" if nose else "unverified",
            c_letter if nose else "D", ssys, surl, "nose present" if nose else "nose missing")
        add("tasting", wid, nname, "palate", (palate or "")[:80], "verified" if palate else "unverified",
            c_letter if palate else "D", ssys, surl, "palate present" if palate else "palate missing")
        add("tasting", wid, nname, "finish", (finish or "")[:80], "verified" if finish else "unverified",
            c_letter if finish else "D", ssys, surl, "finish present" if finish else "finish missing")
        # generic / short checks
        for part, txt in (("nose", nose), ("palate", palate), ("finish", finish)):
            if txt:
                t = txt.strip()
                low = t.lower()
                if any(g in low for g in M.GENERIC_PHRASES):
                    tn_conflicts.append((wid, nname, part, "generic_boilerplate", ssys, txt[:60]))
                    manual.append({"entity": "tasting", "entity_id": wid, "entity_name": nname,
                                   "field": part, "current_value": txt[:60],
                                   "verification_status": "conflict", "confidence": "X",
                                   "authority_source": ssys, "note": "generic/boilerplate text",
                                   "manual_review_required": "true"})
                elif len(t) < M.SHORT_LEN:
                    tn_conflicts.append((wid, nname, part, "too_short", ssys, txt[:60]))
        # light product-match signal -> manual
        if sdoc and did:
            dname = did.lower().replace("d", "").replace("0", "")
            if dname and dname not in (sdoc.lower().replace(" ", "")):
                manual.append({"entity": "tasting", "entity_id": wid, "entity_name": nname,
                               "field": "product_match", "current_value": did,
                               "verification_status": "review", "confidence": "X",
                               "authority_source": ssys, "note": "distillery_id vs source_doc naming mismatch",
                               "manual_review_required": "true"})

    # ---------------- RECOMMENDATION IMPACT (cosine neighbors) ----------------
    impact = _recommendation_impact(axis_rows)

    CON.close()
    os.remove(tmp)
    return ledger, conflicts, manual, low_conf, tn_conflicts, missing, disagreements, batch_flags, impact


def _recommendation_impact(axis_rows):
    """Compute top-N cosine neighbors BEFORE and AFTER a confidence-weighted
    sensitivity adjustment. No production change: what-if on a deep copy."""
    ids = [r[0] for r in axis_rows]
    names = {r[0]: r[1] for r in axis_rows}
    vecs = {r[0]: r[2] for r in axis_rows}
    conf = {r[0]: r[5] for r in axis_rows}
    WEIGHT = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 0.6, "E": 0.4, "X": 0.5}

    def neighbors(weight_fn):
        out = {}
        for a in ids:
            sims = []
            for b in ids:
                if a == b:
                    continue
                va = [x * weight_fn(a) for x in vecs[a]]
                vb = [x * weight_fn(b) for x in vecs[b]]
                sims.append((_cosine(va, vb), b))
            sims.sort(reverse=True)
            out[a] = [b for _, b in sims[:5]]
        return out

    cur_neigh = neighbors(lambda x: 1.0)
    adj_neigh = neighbors(lambda x: WEIGHT.get(conf[x], 1.0))

    changed = 0
    examples = []
    for a in ids:
        if cur_neigh[a] != adj_neigh[a]:
            changed += 1
            if len(examples) < 40:
                examples.append((a, names[a], cur_neigh[a][:3], adj_neigh[a][:3]))
    return {
        "total": len(ids),
        "neighbors_changed": changed,
        "pct_changed": round(100.0 * changed / max(1, len(ids)), 1),
        "examples": examples,
        "weight_model": WEIGHT,
    }


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    led, conf, man, low, tnc, miss, disag, bf, imp = verify()
    print("flavor ledger rows:", len(led))
    print("flavor conflicts (X):", len(conf))
    print("manual review rows:", len(man))
    print("low confidence rows:", len(low))
    print("tasting note flags:", len(tnc))
    print("missing flavor profiles:", len(miss))
    print("batch-policy divergences:", len(bf))
    print("source disagreements:", len(disag))
    print("neighbor rankings changed under confidence weighting:",
          imp["neighbors_changed"], f"({imp['pct_changed']}%)")
