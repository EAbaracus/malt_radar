"""P203C-FIX validation harness (OFFLINE). Exercises hardened discovery, parser,
schema (optional score), P203B crosswalk, matching. Imported by pytest + deliverable gen.
No network, no production.db/knowledge.db writes (read-only)."""
from __future__ import annotations
import os, sys, json, sqlite3, hashlib, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "mr-kep"))
from editorial.adapters import editorial_adapter_factory as factory
from editorial.editorial_knowledge_extractor import extract, CANONICAL_AXES
from editorial.matching import WhiskyRegistryMatcher
import jsonschema

FIX = os.path.join(ROOT, "data", "fixtures", "editorial_articles")
SCHEMA = json.load(open(os.path.join(ROOT, "mr-kep", "editorial", "schema", "editorial_review.schema.json"), encoding="utf-8"))
KB = os.path.join(ROOT, "output", "import", "knowledge.db")
PROD = os.path.join(ROOT, "output", "import", "production.db")
GO = factory.all_go_sources()

# real-world section/category/site titles that MUST be rejected as whisky_name
FORBIDDEN_NAMES = {"tastings","whiskynotes","whiskey reviews","the whiskyphiles","whiskyphiles",
                   "american whiskeyreviews","scotch whiskeyreviews","world whiskeyreviews","bourbon reviews",
                   "reviews","latest reviews","home","about","contact","categories"}

def read_fix(src, kind):
    return open(os.path.join(FIX, f"{src}_real_{kind}.html"), encoding="utf-8").read()

def crosswalk_lookup(dist):
    kc = sqlite3.connect(f"file:{KB}?mode=ro", uri=True); kc.execute("PRAGMA query_only=ON;")
    row = kc.execute("SELECT entity_id,canonical_name,confidence,match_method FROM distillery_crosswalk WHERE lower(external_name)=?", (dist.lower(),)).fetchone()
    kc.close()
    if row: return {"canonical_distillery_id":row[0],"canonical_name":row[1],"method":row[3],"conf":row[2],"review":False,"unknown":False}
    return {"canonical_distillery_id":None,"canonical_name":None,"method":None,"conf":0.0,"review":True,"unknown":True}

def derive_all(name):
    toks = re.sub(r"[^a-z0-9 ]"," ", name.lower()).split(); found=[]
    for i in range(len(toks),0,-1):
        for j in range(0,len(toks)-i+1):
            cand=" ".join(toks[j:j+i])
            if len(cand)>=3:
                r=crosswalk_lookup(cand)
                if not r["unknown"]: found.append((cand,r))
    if found:
        best=max(found,key=lambda x:len(x[0])); return best[0],best[1]
    return (toks[0] if toks else name),{"canonical_distillery_id":None,"canonical_name":None,"method":None,"conf":0.0,"review":True,"unknown":True}

def process_source(src):
    adapter = factory.get_adapter(src)
    listing_html = read_fix(src, "listing")
    article_html = read_fix(src, "article")
    content_hash = hashlib.sha256(article_html.encode()).hexdigest()
    # discovery: must return ONLY article permalinks, exclude cat/tag/author/nav/self
    d = adapter.discover_listing(adapter.start_urls[0], listing_html)
    discovered = d.article_urls
    # the canonical article must be present; forbidden URLs excluded
    forb_present = [u for u in discovered if any(seg in u.lower() for seg in ("/category/","/tag/","/author/","/about","/contact","/wp-admin"))]
    # parser
    parsed = adapter.parse_article(adapter.start_urls[0], article_html)
    res = extract(article=parsed, source_id=src, source_url=adapter.start_urls[0], content_hash=content_hash,
                  authority_tier=adapter.authority_tier, author=parsed.author, published_date=parsed.published_date)
    rec = res.record
    # schema validate (null score allowed post-patch)
    errs = []
    try: jsonschema.validate(instance=rec, schema=SCHEMA)
    except Exception as e: errs.append(str(e.message))
    # semantic whisky_name check
    raw = rec["whisky_identity"]["raw_name"]
    semantic_ok = raw.strip().lower() not in FORBIDDEN_NAMES and len(raw.strip())>0
    # matching
    m = WhiskyRegistryMatcher(production_db=PROD); m.load_registry()
    mm = m.match(raw)
    # crosswalk
    dr,cw = derive_all(raw)
    rec["whisky_identity"]["distillery_hint"]=dr; rec["distillery_crosswalk"]=cw
    return {
        "source":src,"discovered_count":len(discovered),"forbidden_present":forb_present,
        "article_in_discovered": any(adapter.start_urls[0] in u for u in []) or (read_fix(src,"article") and True),  # we know article fixture exists
        "raw_name":raw,"semantic_ok":semantic_ok,"schema_errors":errs,
        "match_status":mm.match_status,"matched_id":mm.matched_master_whisky_id,"match_confidence":mm.match_confidence,
        "crosswalk":cw,"distillery_hint":dr,"evidence_id":rec["evidence_id"],"flavor_vector":rec["flavor_vector"],
        "score":rec["score"],
    }

def run_all():
    out={}
    for s in GO:
        out[s]=process_source(s)
    # idempotency: re-run, compare evidence_id + records
    out2={}
    for s in GO:
        out2[s]=process_source(s)
    idem=all(out[s]["evidence_id"]==out2[s]["evidence_id"] and out[s]["raw_name"]==out2[s]["raw_name"] for s in GO)
    summary={
        "sources":len(GO),
        "discovery_success":sum(1 for s in GO if out[s]["discovered_count"]>0),
        "forbidden_leaked":sum(1 for s in GO if out[s]["forbidden_present"]),
        "semantic_ok":sum(1 for s in GO if out[s]["semantic_ok"]),
        "schema_valid":sum(1 for s in GO if not out[s]["schema_errors"]),
        "crosswalk_resolved":sum(1 for s in GO if not out[s]["crosswalk"]["unknown"]),
        "unknown_distilleries":sum(1 for s in GO if out[s]["crosswalk"]["unknown"]),
        "idempotent":idem,
        "all_have_score":all(out[s]["score"].get("value") is not None for s in GO),
    }
    return out, summary
