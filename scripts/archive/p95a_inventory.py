"""P95-A Phase 1+2 read-only: inventory + format classification across
every flavor-related dataset in production.db. No writes. Reuses frozen
contracts (mr-kep/authority/*). Deterministic classify()."""
import sqlite3, os, json, collections, datetime, csv

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "output", "import", "production.db")
OUT = os.path.join(BASE, "mr-kep", "output", "p95a")
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
    try: d=json.loads(s)
    except Exception: return 'nonjson'
    if isinstance(d,list):
        return 'num_array' if all(isinstance(x,(int,float)) for x in d) else 'mixed_array'
    if isinstance(d,dict):
        if not d: return 'empty_dict'
        keys=list(d.keys()); vals=list(d.values())
        if any(k.startswith('component_') for k in keys): return 'pca'
        if any(isinstance(vv,list) for vv in vals):
            return 'list_str' if all(isinstance(vv,list) and (len(vv)==0 or all(isinstance(x,str) for x in vv)) for vv in vals) else 'mixed_list'
        if all(isinstance(vv,(int,float)) for vv in vals):
            if set(keys)<=AXES: return 'axis_num'
            if any(vv>20 for vv in vals): return 'num_dict_scale100'
            return 'num_dict_term'
        return 'mixed_dict'
    return 'other'

# ---- Phase 1: Inventory of flavor datasets ----
flavor_tables = {
  "flavor_profiles": "production",
  "staging_book_flavor_profiles": "staging_book",
  "staging_flavor_profile_candidates": "staging_candidates",
  "staging_flavor_profile_candidates_full": "staging_candidates_full",
  "staging_notebooklm_flavor_profiles": "staging_notebooklm",
  "staging_p6_flavor_profile_candidates": "staging_p6",
}
inv_rows=[]
print("=== PHASE 1 — FLAVOR ASSET INVENTORY ===")
for tbl, kind in flavor_tables.items():
    cols=[d[1] for d in cur.execute(f'PRAGMA table_info("{tbl}")')]
    n=one(f'SELECT COUNT(*) FROM "{tbl}"')
    n_vec = one(f'SELECT COUNT(*) FROM "{tbl}" WHERE flavor_vector IS NOT NULL AND TRIM(flavor_vector) <> \'\'') if 'flavor_vector' in cols else 0
    # distinct whisky ids
    wid_col = 'whisky_id' if 'whisky_id' in cols else None
    n_ids = one(f'SELECT COUNT(DISTINCT {wid_col}) FROM "{tbl}"') if wid_col else 0
    # source_system / source_file dist
    src_info=""
    if 'source_system' in cols:
        sd=collections.Counter(r[0] for r in q(f'SELECT source_system FROM "{tbl}"'))
        src_info="sys="+",".join(f"{k}={v}" for k,v in sd.most_common(5))
    inv_rows.append((tbl, kind, n, n_vec, n_ids, src_info))
    print(f"  {tbl:42s} rows={n:5d} vec={n_vec:5d} ids={n_ids:5d} {src_info}")

# canonical production vector format dist
print("\n=== PHASE 2 — FORMAT CLASSIFICATION (production.flavor_profiles) ===")
fmt_prod=collections.Counter()
for r in q("SELECT flavor_vector FROM flavor_profiles WHERE flavor_vector IS NOT NULL AND TRIM(flavor_vector)<>''"):
    fmt_prod[classify(r[0])]+=1
print("  production.flavor_profiles:", dict(fmt_prod))

# Build canonical-7axis compatibility per class
CANON_OK = {'axis_num','num_dict_term'}   # numeric, axis/term keys, parseable
print("\n=== PHASE 2 — PER-TABLE FORMAT DISTRIBUTION ===")
table_fmts={}
for tbl, kind in flavor_tables.items():
    cols=[d[1] for d in cur.execute(f'PRAGMA table_info("{tbl}")')]
    if 'flavor_vector' not in cols:
        table_fmts[tbl]=None; continue
    fc=collections.Counter()
    for r in q(f'SELECT flavor_vector FROM "{tbl}"'):
        fc[classify(r[0])]+=1
    table_fmts[tbl]=dict(fc)
    print(f"  {tbl}: {dict(fc)}")

# source_system reality across candidate tables (for authority matrix)
print("\n=== SOURCE SYSTEM / FILE REALITY (for authority matrix) ===")
for tbl in ["staging_flavor_profile_candidates_full","staging_flavor_profile_candidates","staging_book_flavor_profiles","staging_notebooklm_flavor_profiles"]:
    cols=[d[1] for d in cur.execute(f'PRAGMA table_info("{tbl}")')]
    syss=collections.Counter(r[0] for r in q(f'SELECT source_system FROM "{tbl}"')) if 'source_system' in cols else collections.Counter()
    files=collections.Counter(r[0] for r in q(f'SELECT source_file FROM "{tbl}"')) if 'source_file' in cols else collections.Counter()
    print(f"  {tbl}:")
    print(f"     source_system = {dict(syss.most_common(8))}")
    print(f"     source_file   = {dict(files.most_common(8))}")

# Write inventory csv
with open(os.path.join(OUT,"flavor_asset_inventory.csv"),"w",newline="") as f:
    w=csv.writer(f); w.writerow(["dataset","kind","rows","rows_with_vector","distinct_whisky_ids","source_summary"])
    for tbl,kind,n,nv,nids,si in inv_rows:
        w.writerow([tbl,kind,n,nv,nids,si])
print(f"\nWrote {os.path.join(OUT,'flavor_asset_inventory.csv')}")

# stash for later phases
with open(os.path.join(OUT,"_fmt_prod.json"),"w") as f: json.dump(dict(fmt_prod),f)
with open(os.path.join(OUT,"_table_fmts.json"),"w") as f: json.dump(table_fmts,f)
with open(os.path.join(OUT,"_inventory.json"),"w") as f:
    json.dump([{"tbl":t,"kind":k,"rows":n,"vec":nv,"ids":ni,"src":si} for t,k,n,nv,ni,si in inv_rows], f)
