"""P203C-FIX pytest suite (OFFLINE, no network, no DB mutation).

Run: python -m pytest mr-kep/p203c_fix/test_p203c_fix.py -q
"""
import os, sys, json, sqlite3, hashlib, re
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "mr-kep"))
from editorial.adapters import editorial_adapter_factory as factory
from editorial.editorial_knowledge_extractor import extract, CANONICAL_AXES, _sha16
from editorial.matching import WhiskyRegistryMatcher
import jsonschema
import p203cfix_harness as H

GO = factory.all_go_sources()
SCHEMA = H.SCHEMA
FIX = H.FIX

# ---------- adapter registration ----------
def test_adapter_registration():
    assert set(GO) == {"thewhiskyphiles","whiskymonster","thedramble","whiskynotes_be","thewhiskeywash","wordsofwhisky"}
    for s in GO:
        assert factory.get_adapter(s).source_id == s

# ---------- discovery selectors ----------
def test_discovery_returns_articles_only():
    for s in GO:
        adapter = factory.get_adapter(s)
        html = H.read_fix(s, "listing")
        d = adapter.discover_listing(adapter.start_urls[0], html)
        assert len(d.article_urls) > 0
        # none of the forbidden URL types leak through
        for u in d.article_urls:
            assert not re.search(r"/category/|/tag/|/author/|/about|/contact|/wp-admin", u, re.I)

def test_discovery_excludes_listing_self():
    for s in GO:
        adapter = factory.get_adapter(s)
        html = H.read_fix(s, "listing")
        d = adapter.discover_listing(adapter.start_urls[0], html)
        assert adapter.start_urls[0].rstrip("/") not in [u.rstrip("/") for u in d.article_urls]

def test_discovery_deterministic():
    for s in GO:
        adapter = factory.get_adapter(s)
        html = H.read_fix(s, "listing")
        a = adapter.discover_listing(adapter.start_urls[0], html)
        b = adapter.discover_listing(adapter.start_urls[0], html)
        assert a.article_urls == b.article_urls

# ---------- fixture loading ----------
def test_fixtures_present():
    for s in GO:
        for kind in ("listing","article"):
            p = os.path.join(FIX, f"{s}_real_{kind}.html")
            assert os.path.exists(p) and os.path.getsize(p) > 0

# ---------- article filtering ----------
def test_article_filtering_no_section_titles():
    # the discovered URLs must point to article permalinks, never section pages
    ART_RE = {
        "thewhiskyphiles": r"/20\d\d/\d\d/",
        "whiskymonster": r"/whisky/whisky-reviews/",
        "thedramble": r"/tastings/",
        "whiskynotes_be": r"/20\d\d/",
        "thewhiskeywash": r"/whiskey-reviews/",
        "wordsofwhisky": r"/20\d\d/",
    }
    for s in GO:
        adapter = factory.get_adapter(s)
        d = adapter.discover_listing(adapter.start_urls[0], H.read_fix(s,"listing"))
        for u in d.article_urls:
            assert re.search(ART_RE[s], u), f"{s}: {u} not an article permalink"

# ---------- parser extraction ----------
def test_parser_extraction_fields():
    for s in GO:
        adapter = factory.get_adapter(s)
        parsed = adapter.parse_article(adapter.start_urls[0], H.read_fix(s,"article"))
        assert parsed.raw_name
        assert parsed.conclusion

def test_parser_semantic_whisky_name():
    FORBIDDEN = {"tastings","whiskynotes","whiskey reviews","the whiskyphiles","reviews","latest reviews"}
    for s in GO:
        adapter = factory.get_adapter(s)
        parsed = adapter.parse_article(adapter.start_urls[0], H.read_fix(s,"article"))
        low = parsed.raw_name.strip().lower()
        assert low not in FORBIDDEN
        assert len(parsed.raw_name.strip()) > 0

# ---------- schema validation ----------
def test_schema_valid_for_all():
    out, _ = H.run_all()
    for s in GO:
        assert out[s]["schema_errors"] == [], f"{s}: {out[s]['schema_errors']}"

def test_schema_null_score_allowed():
    # a record with no detectable score must validate after the patch
    rec = {"schema_version":"editorial-review/1.0","evidence_id":"EDR-"+ "0"*16,
      "source":{"source_id":"x","source_type":"editorial","authority_tier":"T2_expert","url":"https://x/a","author":None,"published_date":None,"license":"copyright-attribution-required","content_hash_sha256":"0"*64},
      "whisky_identity":{"raw_name":"Test 12","normalized_name":"test 12","match_status":"unmatched","matched_master_whisky_id":None},
      "metadata":{},
      "score":{"value":None,"scale_max":100.0,"normalized":None},
      "tasting_notes":{"nose":None,"palate":None,"finish":None,"conclusion":"excerpt only"},
      "flavor_vector":{a:0.0 for a in CANONICAL_AXES},
      "evidence":{"confidence":0.8,"extraction_method":"heuristic","quotes":[],"provenance_state":"staging_unverified","ingested_by":"p203c"}}
    jsonschema.validate(instance=rec, schema=SCHEMA)  # raises if invalid

def test_schema_rejects_bad_normalized():
    rec = {"schema_version":"editorial-review/1.0","evidence_id":"EDR-"+"0"*16,
      "source":{"source_id":"x","source_type":"editorial","authority_tier":"T2_expert","url":"https://x/a","author":None,"published_date":None,"license":"copyright-attribution-required","content_hash_sha256":"0"*64},
      "whisky_identity":{"raw_name":"Test 12","normalized_name":"test 12","match_status":"unmatched","matched_master_whisky_id":None},
      "metadata":{},
      "score":{"value":50,"scale_max":100,"normalized":1.5},  # out of range
      "tasting_notes":{"nose":None,"palate":None,"finish":None,"conclusion":"x"},
      "flavor_vector":{a:0.0 for a in CANONICAL_AXES},
      "evidence":{"confidence":0.8,"extraction_method":"heuristic","quotes":[],"provenance_state":"staging_unverified","ingested_by":"p203c"}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=rec, schema=SCHEMA)

# ---------- crosswalk ----------
def test_crosswalk_resolves_all():
    out, _ = H.run_all()
    for s in GO:
        assert not out[s]["crosswalk"]["unknown"], f"{s} unresolved"

def test_crosswalk_deterministic():
    a = H.crosswalk_lookup("Glenmorangie")
    b = H.crosswalk_lookup("Glenmorangie")
    assert a == b

# ---------- matching ----------
def test_matching_deterministic():
    m = WhiskyRegistryMatcher(production_db=H.PROD)
    m.load_registry()
    d1 = m.match("Glenmorangie 18 Year Old")
    d2 = m.match("Glenmorangie 18 Year Old")
    assert d1.matched_master_whisky_id == d2.matched_master_whisky_id

# ---------- canonical axes ----------
def test_canonical_axes_valid():
    out, _ = H.run_all()
    for s in GO:
        vec = out[s]["flavor_vector"]
        for ax in CANONICAL_AXES:
            assert ax in vec
            assert 0.0 <= vec[ax] <= 1.0

# ---------- evidence_id stability ----------
def test_evidence_id_stable():
    out, _ = H.run_all()
    for eid in [out[s]["evidence_id"] for s in GO]:
        assert eid.startswith("EDR-") and len(eid) == 20

# ---------- idempotency ----------
def test_idempotency():
    out, summ = H.run_all()
    assert summ["idempotent"] is True
