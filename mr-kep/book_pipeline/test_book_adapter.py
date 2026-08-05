#!/usr/bin/env python3
"""PHASE 6 — BookDomainAdapter unit tests (10 cases) + editorial regression.
No production write. Uses in-memory / temp DBs only.
"""
import sys, os, json, sqlite3, tempfile
BASE = r"C:\Users\eltun\Documents\malt radar CLEAN"
TEMP = os.environ.get("LOCALAPPDATA", r"C:\Users\eltun\AppData\Local\Temp")
sys.path.insert(0, os.path.join(BASE, "mr-kep"))
sys.path.insert(0, os.path.join(BASE, "mr-kep", "common"))
from domain_adapter import (BookDomainAdapter, EditorialDomainAdapter,
                            list_adapters, get_adapter, PromotionPlan)

PROD = os.path.join(BASE, "output", "import", "production.db")
VECTOR_OK = json.dumps({"smoky":0.5,"peaty":0.3,"fruity":0.2,"sweet":0.4,"spicy":0.1,"maritime":0.0,"sherry":0.6})
VECTOR_MISSING_AXIS = json.dumps({"smoky":0.5,"peaty":0.3})  # missing 5 axes
VECTOR_MALFORMED = "{not json"
VECTOR_OOR = json.dumps({"smoky":5.0,"peaty":0.3,"fruity":0.2,"sweet":0.4,"spicy":0.1,"maritime":0.0,"sherry":0.6})

SCHEMA = """
CREATE TABLE staging_book_reviews (
    evidence_id TEXT PRIMARY KEY, matched_master_whisky_id TEXT,
    match_status TEXT NOT NULL, provenance_state TEXT NOT NULL DEFAULT 'staging_unverified',
    flavor_vector_json TEXT NOT NULL, evidence_confidence REAL, source TEXT, book_id TEXT,
    original_fact_id TEXT, entity_key_raw TEXT, er_class TEXT);
"""
# Pick a real valid whisky_id from production for positive tests
_p = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
VALID_WID = _p.execute("SELECT whisky_id FROM whiskies LIMIT 1").fetchone()[0]
BAD_WID = "WZZZZZZ"  # not in production
_p.close()


def fresh_staging(rows):
    db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db.close()
    c = sqlite3.connect(db.name)
    c.executescript(SCHEMA)
    for r in rows:
        c.execute("INSERT OR IGNORE INTO staging_book_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?)", r)
    c.commit(); c.close()
    return db.name


def plan_on(rows):
    sd = fresh_staging(rows)
    ad = BookDomainAdapter()
    plan = ad.plan(staging_db=sd, production_db=PROD)
    os.remove(sd)
    return plan


results = []
def check(name, cond):
    results.append((name, cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")


# 1. valid Book row -> PASS
p = plan_on([("BK-1", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f1", "Lagavulin", "MATCH")])
check("1. valid Book row -> accepted", p.new_evidence_rows == 1 and len(p.rejected) == 0)

# 2. missing whisky_id -> FAIL
p = plan_on([("BK-2", None, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f2", "X", "MATCH")])
check("2. missing whisky_id -> rejected", len(p.rejected) == 1 and p.new_evidence_rows == 0)

# 3. AMBIGUOUS identity -> FAIL
p = plan_on([("BK-3", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f3", "X", "AMBIGUOUS")])
check("3. AMBIGUOUS -> rejected (not promotable)", len(p.rejected) == 1 and "AMBIGUOUS" in p.rejected[0]["reason"])

# 4. NO_MATCH identity -> FAIL
p = plan_on([("BK-4", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f4", "X", "NO_MATCH")])
check("4. NO_MATCH -> rejected (not promotable)", len(p.rejected) == 1 and "NO_MATCH" in p.rejected[0]["reason"])

# 5. malformed descriptor JSON -> FAIL
p = plan_on([("BK-5", VALID_WID, "exact", "staging_unverified", VECTOR_MALFORMED, 0.9, "book", "BK_x", "f5", "X", "MATCH")])
check("5. malformed descriptor -> rejected", len(p.rejected) == 1)

# 6. missing required axis -> FAIL
p = plan_on([("BK-6", VALID_WID, "exact", "staging_unverified", VECTOR_MISSING_AXIS, 0.9, "book", "BK_x", "f6", "X", "MATCH")])
check("6. missing axis -> rejected", len(p.rejected) == 1)

# 7. duplicate fact (same evidence_id in staging -> INSERT OR IGNORE keeps 1 row)
p = plan_on([
    ("BK-DUP", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f7", "X", "MATCH"),
    ("BK-DUP", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f7", "X", "MATCH"),
])
check("7. duplicate evidence_id -> 1 accepted (INSERT OR IGNORE)", p.new_evidence_rows == 1 and len(p.accepted) == 1)

# 8. invalid FK (whisky_id not in production) -> FAIL
p = plan_on([("BK-8", BAD_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f8", "X", "MATCH")])
check("8. invalid FK (wid not in prod) -> rejected", len(p.rejected) == 1)

# 9. missing provenance (rejected provenance_state) -> FAIL
p = plan_on([("BK-9", VALID_WID, "exact", "rejected", VECTOR_OK, 0.9, "book", "BK_x", "f9", "X", "MATCH")])
check("9. rejected provenance -> rejected", len(p.rejected) == 1)

# 10. deterministic same input -> identical output
r1 = plan_on([("BK-10", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f10", "X", "MATCH")])
r2 = plan_on([("BK-10", VALID_WID, "exact", "staging_unverified", VECTOR_OK, 0.9, "book", "BK_x", "f10", "X", "MATCH")])
check("10. deterministic output", r1.plan_hash == r2.plan_hash and r1.new_evidence_rows == r2.new_evidence_rows)

# --- Editorial regression ---
reg_ok = True
try:
    adapters = list_adapters()
    assert "editorial" in adapters, "editorial adapter missing"
    assert "book" in adapters, "book adapter missing"
    # Editorial adapter still instantiable + has plan()
    ea = get_adapter("editorial")
    assert hasattr(ea, "plan") and hasattr(ea, "apply_plan")
    # Book adapter similarly
    ba = get_adapter("book")
    assert hasattr(ba, "plan") and hasattr(ba, "apply_plan")
    print(f"  [PASS] editorial regression: adapters={adapters}")
except Exception as e:
    reg_ok = False
    print(f"  [FAIL] editorial regression: {e}")

n_pass = sum(1 for _, c in results if c)
print(f"\nUNIT TESTS: {n_pass}/{len(results)} passed | editorial regression: {'PASS' if reg_ok else 'FAIL'}")
if n_pass != len(results) or not reg_ok:
    print("RESULT: FAIL")
    sys.exit(1)
print("RESULT: PASS")
