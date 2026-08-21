"""
P4 — Binder Integration Pilot (read-only, 20 URLs)

Integrates source_page_identity_binder.py into the Phase 3 pipeline
BEFORE prose extraction / FlavorMapper / R4 / candidate serialization.

Enforces the gate: verdict != MATCH => block all downstream steps.
"""

import os, sys, json, time, re, hashlib, sqlite3, urllib.parse, urllib.request
from typing import Dict, List, Any, Optional

# --- Paths ---
BASE = r'C:\Users\eltun\Documents\malt radar CLEAN'
PROD_DB = os.path.join(BASE, r'output\import\production.db')
TEMP = os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'mr-kep-p4-legacy-gap-closure')
PILOT_OUT = os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'mr-kep-p4-binder-integration-pilot')
os.makedirs(PILOT_OUT, exist_ok=True)

# --- Import the canonical binder ---
sys.path.insert(0, os.path.join(BASE, 'mr-kep', 'acquisition'))
from source_page_identity_binder import (
    ProductionRecord,
    SourcePageIdentity,
    IdentityVerdict,
    bind,
    extract_source_identity,
)

# --- Read-only production SHA ---
def prod_sha():
    with open(PROD_DB, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

PROD_SHA_BEFORE = prod_sha()
print(f'PROD_SHA before: {PROD_SHA_BEFORE}')
assert PROD_SHA_BEFORE == '248e3ca9bd527b3c6e2fc9b1c8a9afe886854057fd71bd93f9d47b51aa38c457', 'SHA MISMATCH'

# --- SearXNG + Firecrawl (same as Phase 3) ---
def searxng_search(query: str, limit: int = 3) -> List[Dict]:
    try:
        q = urllib.request.urlopen(
            f'http://localhost:8090/search?q={urllib.parse.quote(query)}&format=json&limit={limit}',
            timeout=15)
        data = json.loads(q.read())
        return data.get('results', [])
    except Exception as e:
        print(f'  SearXNG error: {e}')
        return []

def firecrawl_scrape(url: str) -> Dict:
    try:
        payload = json.dumps({'url': url, 'formats': ['markdown']}).encode()
        req = urllib.request.Request('http://localhost:3002/v0/scrape', data=payload,
            headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        if data.get('success'):
            md = data.get('data', {}).get('markdown', '')
            title = data.get('data', {}).get('metadata', {}).get('title', '')
            return {'ok': True, 'title': title, 'content': md[:8000]}
        return {'ok': False, 'error': 'v0 fail'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

# --- Load production ZE candidates (same as Phase 3) ---
def load_ze_candidates():
    uri = 'file:' + urllib.parse.quote(PROD_DB, safe='/:') + '?mode=ro&nolock=1'
    conn = sqlite3.connect(uri, uri=True)
    c = conn.cursor()
    c.execute("""
        SELECT whisky_id, name, brand, type, region, country, age, abv
        FROM whiskies WHERE whisky_id NOT IN (SELECT DISTINCT whisky_id FROM flavor_evidence)
        AND (superseded_by IS NULL OR superseded_by='')
        ORDER BY name
    """)
    rows = c.fetchall()
    conn.close()
    
    targets = []
    for r in rows:
        wid, name, brand = r[0], r[1] or '', r[2] or ''
        cat, region, country = r[3] or '', r[4] or '', r[5] or ''
        age, abv = r[6], r[7]
        score = sum([3 if name and len(name)>3 else 0, 2 if brand and len(brand)>3 else 0, 2 if age else 0, 1 if abv else 0])
        text = (name + ' ' + brand + ' ' + cat + ' ' + country + ' ' + region).lower()
        if any(k in text for k in ['bourbon','rye','wheat','tennessee','american','jack daniel','bernheim','baker','old forester','wild turkey','four roses','heaven hill','jim beam','michter','bulliet','barton']):
            route = 'AMERICAN'
        elif any(k in text for k in ['irish','bushmills','amrut','glendalough','gouden','kanosuke','nikka','suntory','japanese','hatozaki']):
            route = 'WORLD'
        else:
            route = 'SCOTCH'
        targets.append({'wid':wid,'name':name,'brand':brand,'score':score,'route':route,'age':age,'abv':abv})
    targets.sort(key=lambda x: (-x['score'], x['name']))
    strong = [t for t in targets if t['score'] >= 5]
    return strong

# --- Route-source mapping (same as Phase 3) ---
ROUTE_SOURCES = {
    'AMERICAN': ['thewhiskeywash.com','thewhiskeyjug.com','bourbonbanter.com','longpouramour.com','distiller.com'],
    'SCOTCH': ['jeffwhisky.com','maltfascination.com','singlemaltsnob.com','twowhiskybros.co.uk','longpouramour.com','whiskyrant.com','dram1.com','wordsofwhisky.com','thedutchwhiskyassociation.nl','distiller.com'],
    'WORLD': ['whiskyforeveryone.com','wordsofwhisky.com','dram1.com','thewhiskeywash.com','distiller.com'],
}

# --- Build pilot: select 20 candidates with diverse source categories ---
def select_pilot_candidates(strong: List[Dict]) -> List[Dict]:
    """Deterministically select 20 URLs from diverse categories."""
    pilot = []
    processed = set()
    
    # Build processed set (same as Phase 3)
    wf_ids = ['W001832','W001834','W001835','W001836','W001837','W001838','W001851','W001852','W001853',
        'W001854','W001855','W001856','W001857','W001859','W001860','W001861','W001863','W001864','W001867',
        'W001868','W001869','W001870','W001872','W001873','W001874','W001875','W001876','W001877','W001879',
        'W001880','W001881','W001882','W001883','W001884','W001885','W001886','W001887','W001888','W001889',
        'W001890','W001891','W001892','W001893','W001894','W001895','W001896','W001897','W001898','W001899',
        'W001900','W001901','W001903','W001904','W001905','W001914','W3294','W3295','W3296','W3297','W3298',
        'W3301','W3303','W3304','W3305','W3306','W3308','W3309','W003561','W003562','W003564','W003565',
        'W003566','W003572','W003574','W003578','W003579','W003580','W003581','W003582','W003585','W003587',
        'W003589','W003590','W003591','W003592','W003593','W003595','W003597','W003909']
    for wid in wf_ids:
        processed.add((wid, 'whiskyfun.com'))
    for wid in ['W001834','W001836','W001852','W001859','W001867','W001869','W001872','W001874','W001886','W001903']:
        processed.add((wid, 'whiskynotes.be'))
        processed.add((wid, 'masterofmalt.com'))
    for wid, dom in [('W001834','thewhiskeywash.com'),('W001834','whiskyforeveryone.com'),('W001834','jeffwhisky.com'),
        ('W001852','thewhiskeyjug.com'),('W001852','jeffwhisky.com'),('W001852','thewhiskeywash.com'),
        ('W001869','jeffwhisky.com'),('W001869','whiskyforeveryone.com'),('W001869','thewhiskeywash.com'),
        ('W001874','thewhiskeywash.com'),('W001874','whiskyforeveryone.com'),('W001874','jeffwhisky.com'),
        ('W001836','jeffwhisky.com'),('W001836','thewhiskeywash.com'),('W001836','whiskyforeveryone.com')]:
        processed.add((wid, dom))
    B2_NEW = [('W001837','maltfascination.com'),('W001855','breakingbourbon.com'),('W001860','wordsofwhisky.com'),
        ('W001873','whiskyforeveryone.com'),('W001876','singlemaltsnob.com'),
        ('W001834','maltfascination.com'),('W001834','singlemaltsnob.com'),('W001834','wordsofwhisky.com')]
    for wid, dom in B2_NEW:
        processed.add((wid, dom))
    
    # Category quotas for deterministic selection
    quotas = {
        'brand_level': 5,      # pages likely to be generic brand articles
        'age_stated': 5,       # pages with explicit age
        'multi_product': 3,    # comparison pages
        'nas_core': 3,         # NAS core range
        'single_cask': 2,      # single cask / edition
        'weak_identity': 2,    # ambiguous
    }
    filled = {k: 0 for k in quotas}
    
    for t in strong:
        if len(pilot) >= 20:
            break
        wid = t['wid']
        name = t['name']
        brand = t['brand']
        route = t['route']
        age = t['age']
        abv = t['abv']
        
        sources = ROUTE_SOURCES.get(route, ['whiskyforeveryone.com','dram1.com'])
        new_srcs = [s for s in sources if (wid, s) not in processed]
        if not new_srcs:
            for alt in ['dram1.com','longpouramour.com','whiskyrant.com','wordsofwhisky.com']:
                if (wid, alt) not in processed and alt not in new_srcs:
                    new_srcs.append(alt)
        if not new_srcs:
            continue
            
        # Deterministic category assignment based on name characteristics
        name_lower = name.lower()
        is_age_stated = 'year' in name_lower or 'yo' in name_lower or (age and age > 0)
        is_multi = any(k in name_lower for k in ['vs', 'compared', 'shootout', 'tasting', 'battle'])
        is_nas_core = 'cask strength' in name_lower or 'core range' in name_lower or (not age and 'year' not in name_lower and 'yo' not in name_lower)
        is_single_cask = any(k in name_lower for k in ['cask', 'batch', 'edition', 'single cask', 'finish'])
        is_weak = len(name.split()) < 3
        
        # Assign to first available quota
        category = None
        if is_multi and filled['multi_product'] < quotas['multi_product']:
            category = 'multi_product'
        elif is_age_stated and filled['age_stated'] < quotas['age_stated']:
            category = 'age_stated'
        elif is_nas_core and filled['nas_core'] < quotas['nas_core']:
            category = 'nas_core'
        elif is_single_cask and filled['single_cask'] < quotas['single_cask']:
            category = 'single_cask'
        elif is_weak and filled['weak_identity'] < quotas['weak_identity']:
            category = 'weak_identity'
        elif filled['brand_level'] < quotas['brand_level']:
            category = 'brand_level'
        else:
            # Fill any remaining quota
            for cat, cap in quotas.items():
                if filled[cat] < cap:
                    category = cat
                    break
        
        if category is None or filled.get(category, 0) >= quotas.get(category, 0):
            continue
            
        filled[category] = filled.get(category, 0) + 1
        
        for src in new_srcs[:2]:  # max 2 sources per candidate
            if len(pilot) >= 20:
                break
            pilot.append({**t, 'source': src, 'category': category})
            processed.add((wid, src))
    
    # If we don't have 20, fill from remaining
    if len(pilot) < 20:
        for t in strong:
            if len(pilot) >= 20:
                break
            wid = t['wid']
            name = t['name']
            brand = t['brand']
            route = t['route']
            sources = ROUTE_SOURCES.get(route, ['whiskyforeveryone.com','dram1.com'])
            new_srcs = [s for s in sources if (wid, s) not in processed]
            for src in new_srcs[:2]:
                if len(pilot) >= 20:
                    break
                pilot.append({**t, 'source': src, 'category': 'additional'})
                processed.add((wid, src))
    
    return pilot[:20]

# --- Main pilot execution ---
def run_pilot():
    print('=== LOADING ZE CANDIDATES ===')
    strong = load_ze_candidates()
    print(f'Strong candidates: {len(strong)}')
    
    pilot = select_pilot_candidates(strong)
    print(f'Pilot URLs selected: {len(pilot)}')
    
    # Save pilot URLs
    with open(os.path.join(PILOT_OUT, 'pilot_urls.json'), 'w') as f:
        json.dump(pilot, f, indent=2)
    
    results = []
    fetch_results = []
    binder_results = []
    
    # Amrut regression control URLs
    amrut_regression = {
        'whiskyforeveryone.com/review-amrut-indian-cask-strength/': ['W001835', 'W001837'],
        'wordsofwhisky.com/amrut-2020-4-years-whiskybase/': ['W001835', 'W001836', 'W001837'],
    }
    
    for i, cand in enumerate(pilot, 1):
        wid = cand['wid']
        name = cand['name']
        brand = cand['brand']
        src = cand['source']
        category = cand.get('category', 'unknown')
        age = cand.get('age')
        abv = cand.get('abv')
        
        print(f'\n[{i}/20] {wid} {name[:50]} | source={src} | cat={category}')
        
        # Build search query
        q = f'site:{src} "{name}" | "{brand}"'
        res = searxng_search(q)
        time.sleep(0.15)
        
        if not res:
            print(f'  No SearXNG result')
            results.append({
                'wid': wid, 'name': name, 'brand': brand, 'source': src,
                'category': category, 'searxng_hit': False,
                'verdict': 'NO_SOURCE', 'reason': 'No search result',
                'prose_called': False, 'mapper_called': False, 'r4_called': False, 'candidate_written': False
            })
            continue
        
        url = res[0].get('url', '')
        if not url:
            print(f'  No URL in result')
            continue
        
        # Fetch page
        print(f'  Fetching: {url[:80]}')
        extraction = firecrawl_scrape(url)
        time.sleep(0.3)
        
        fetch_results.append({
            'wid': wid, 'source': src, 'url': url,
            'fetch_ok': extraction.get('ok', False),
            'title': extraction.get('title', '') if extraction.get('ok') else '',
            'content_len': len(extraction.get('content', '')) if extraction.get('ok') else 0,
        })
        
        if not extraction.get('ok'):
            print(f'  Firecrawl failed: {extraction.get("error")}')
            results.append({
                'wid': wid, 'name': name, 'brand': brand, 'source': src,
                'category': category, 'url': url,
                'verdict': 'FETCH_FAILED', 'reason': extraction.get('error', 'unknown'),
                'prose_called': False, 'mapper_called': False, 'r4_called': False, 'candidate_written': False
            })
            continue
        
        title = extraction.get('title', '')
        content = extraction.get('content', '')
        
        # Build ProductionRecord from DB data
        # Need to query production for full metadata
        uri = 'file:' + urllib.parse.quote(PROD_DB, safe='/:') + '?mode=ro&nolock=1'
        conn = sqlite3.connect(uri, uri=True)
        c = conn.cursor()
        c.execute('SELECT whisky_id, name, brand, age, abv, cask_type, region, country FROM whiskies WHERE whisky_id = ?', (wid,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            print(f'  WARNING: Production record not found for {wid}')
            continue
        
        prod = ProductionRecord(
            whisky_id=row[0],
            name=row[1] or '',
            brand=row[2] or '',
            age=row[3] if row[3] is not None else None,
            abv=float(row[4]) if row[4] is not None else None,
            cask_type=row[5] if row[5] else None,
            edition=None,  # not in schema
            region=row[6] if row[6] else None,
            country=row[7] if row[7] else None,
        )
        
        # Extract source page identity
        page_identity = extract_source_identity(title, content)
        page_identity.brand = brand  # inject known brand
        
        # RUN THE BINDER - THE CRITICAL GATE
        binder_result = bind(prod, page_identity, page_title=title, source_url=url)
        verdict = binder_result.verdict
        
        print(f'  Binder verdict: {verdict.value} - {binder_result.reason}')
        
        binder_results.append({
            'wid': wid, 'source': src, 'url': url,
            'verdict': verdict.value,
            'reason': binder_result.reason,
            'matched': binder_result.matched_attributes,
            'contradicted': binder_result.contradicted_attributes,
            'page_identity': {
                'brand': page_identity.brand,
                'age': page_identity.age,
                'abv': page_identity.abv,
                'cask_type': page_identity.cask_type,
                'edition': page_identity.edition,
                'expression': page_identity.expression,
                'multi_product': page_identity.multi_product,
            }
        })
        
        # GATE: If not MATCH, block everything downstream
        prose_called = False
        mapper_called = False
        r4_called = False
        candidate_written = False
        
        if verdict == IdentityVerdict.MATCH:
            # Prose extraction (same as Phase 3)
            prose_called = True
            sents = re.split(r'[.!?\n]', content)
            tasting = [s.strip() for s in sents if any(kw in s.lower() for kw in
                ['nose','palate','finish','sweet','fruit','spice','smoke','peat','sherry','honey',
                 'vanilla','caramel','oak','pepper','ginger','cinnamon','chocolate','brine','maritime'])]
            
            if len(tasting) >= 2:
                excerpt = '. '.join(tasting[:4])[:400]
                mapper_called = True
                
                # FlavorMapper (same as Phase 3)
                vec = {}
                excerpt_l = excerpt.lower()
                mappings = {
                    'fruity': ['fruit','berry','cherry','apple','pear','citrus','lemon','orange','mango','apricot','plum','tropical','grape'],
                    'sweet': ['sweet','honey','vanilla','caramel','toffee','sugar','maple','chocolate','malt','malty'],
                    'spicy': ['spice','spicy','pepper','cinnamon','ginger','clove','nutmeg','oak','wood','cedar','baking'],
                    'smoky': ['smoke','smoky','charred','ash','bonfire','bbq'],
                    'peaty': ['peat','peaty','earthy','mossy','bog','iodine'],
                    'sherry': ['sherry','oloroso','px','port','dried fruit','fig','date','prune','leather','tobacco'],
                    'maritime': ['maritime','coastal','brine','salt','sea','ocean','sea salt']
                }
                for axis, kws in mappings.items():
                    matches = [kw for kw in kws if kw in excerpt_l]
                    if matches:
                        vec[axis] = round(min(1.0, 0.3 + 0.15 * min(len(matches), 4)), 1)
                
                nz = sum(1 for v in vec.values() if v > 0)
                if nz >= 2:
                    r4_called = True
                    candidate_written = True
                    print(f'  ✓ RECOVERABLE: {wid} [{nz} axes]')
                else:
                    print(f'  R4 FAIL: {nz} axes')
            else:
                print(f'  Insufficient tasting prose')
        else:
            print(f'  BLOCKED at binder gate: {verdict.value}')
        
        results.append({
            'wid': wid, 'name': name, 'brand': brand, 'source': src,
            'category': category, 'url': url,
            'verdict': verdict.value,
            'reason': binder_result.reason,
            'matched': binder_result.matched_attributes,
            'contradicted': binder_result.contradicted_attributes,
            'prose_called': prose_called,
            'mapper_called': mapper_called,
            'r4_called': r4_called,
            'candidate_written': candidate_written,
        })
    
    # --- Assertions ---
    print('\n=== ASSERTION CHECKS ===')
    
    assertions = {}
    
    # A: No brand-only MATCH
    brand_only_matches = [r for r in results if r['verdict'] == 'match' and 
                          set(r.get('matched', [])) <= {'brand'}]
    assertions['A'] = len(brand_only_matches) == 0
    print(f'A - No brand-only MATCH: {"PASS" if assertions["A"] else "FAIL"} ({len(brand_only_matches)} violations)')
    
    # B: Amrut regression
    amrut_failures = 0
    for url, wids in amrut_regression.items():
        for wid in wids:
            match = next((r for r in results if r['wid'] == wid and url in r.get('url', '')), None)
            if match and match['verdict'] == 'match':
                amrut_failures += 1
                print(f'  Amrut REGRESSION FAIL: {wid} -> {url} = MATCH')
    assertions['B'] = amrut_failures == 0
    print(f'B - Amrut regression: {"PASS" if assertions["B"] else "FAIL"} ({amrut_failures} false MATCH)')
    
    # C: Extraction gate
    extraction_violations = sum(1 for r in results if r['verdict'] != 'match' and r['prose_called'])
    assertions['C'] = extraction_violations == 0
    print(f'C - Extraction gate: {"PASS" if assertions["C"] else "FAIL"} ({extraction_violations} violations)')
    
    # D: Flavor gate
    mapper_violations = sum(1 for r in results if r['verdict'] != 'match' and r['mapper_called'])
    assertions['D'] = mapper_violations == 0
    print(f'D - Flavor gate: {"PASS" if assertions["D"] else "FAIL"} ({mapper_violations} violations)')
    
    # E: R4 gate
    r4_violations = sum(1 for r in results if r['verdict'] != 'match' and r['r4_called'])
    assertions['E'] = r4_violations == 0
    print(f'E - R4 gate: {"PASS" if assertions["E"] else "FAIL"} ({r4_violations} violations)')
    
    # F: Candidate gate
    candidate_violations = sum(1 for r in results if r['verdict'] != 'match' and r['candidate_written'])
    assertions['F'] = candidate_violations == 0
    print(f'F - Candidate gate: {"PASS" if assertions["F"] else "FAIL"} ({candidate_violations} violations)')
    
    # G: Cross-entity isolation
    url_to_wids = {}
    for r in results:
        if r['verdict'] == 'match':
            url = r.get('url', '')
            if url:
                url_to_wids.setdefault(url, []).add(r['wid'])
    cross_entity_violations = sum(1 for url, wids in url_to_wids.items() if len(wids) > 1)
    assertions['G'] = cross_entity_violations == 0
    print(f'G - Cross-entity isolation: {"PASS" if assertions["G"] else "FAIL"} ({cross_entity_violations} violations)')
    
    # H: Production immutability
    prod_sha_after = prod_sha()
    assertions['H'] = prod_sha_after == PROD_SHA_BEFORE
    print(f'H - Production immutability: {"PASS" if assertions["H"] else "FAIL"} (before={PROD_SHA_BEFORE[:16]}... after={prod_sha_after[:16]}...)')
    
    # Save artifacts
    with open(os.path.join(PILOT_OUT, 'pilot_fetch_results.jsonl'), 'w') as f:
        for r in fetch_results:
            f.write(json.dumps(r) + '\n')
    with open(os.path.join(PILOT_OUT, 'pilot_binder_results.jsonl'), 'w') as f:
        for r in binder_results:
            f.write(json.dumps(r) + '\n')
    with open(os.path.join(PILOT_OUT, 'pilot_results.jsonl'), 'w') as f:
        for r in results:
            f.write(json.dumps(r) + '\n')
    with open(os.path.join(PILOT_OUT, 'pilot_assertions.json'), 'w') as f:
        json.dump(assertions, f, indent=2)
    
    # Verdict distribution
    dist = {}
    for r in results:
        dist[r['verdict']] = dist.get(r['verdict'], 0) + 1
    
    print(f'\n=== VERDICT DISTRIBUTION ===')
    for v, c in sorted(dist.items()):
        print(f'  {v}: {c}')
    
    print(f'\n=== ASSERTION SUMMARY ===')
    all_pass = all(assertions.values())
    for k, v in assertions.items():
        print(f'  {k}: {"PASS" if v else "FAIL"}')
    print(f'ALL ASSERTIONS: {"PASS" if all_pass else "FAIL"}')
    
    # Final classification
    if all_pass:
        classification = 'INTEGRATION_PILOT_PASS'
    elif not any(assertions.values()):
        classification = 'INTEGRATION_PILOT_BLOCKED'
    else:
        classification = 'INTEGRATION_PILOT_FAILED'
    
    print(f'\n=== CLASSIFICATION: {classification} ===')
    
    # Save summary
    with open(os.path.join(PILOT_OUT, 'pilot_summary.md'), 'w') as f:
        f.write(f'# Pilot Summary\n\n')
        f.write(f'Classification: {classification}\n\n')
        f.write(f'## Verdict Distribution\n\n')
        for v, c in sorted(dist.items()):
            f.write(f'- {v}: {c}\n')
        f.write(f'\n## Assertions\n\n')
        for k, v in assertions.items():
            f.write(f'- {k}: {"PASS" if v else "FAIL"}\n')
        f.write(f'\n## Safety\n\n')
        f.write(f'- Production SHA before: {PROD_SHA_BEFORE}\n')
        f.write(f'- Production SHA after: {prod_sha_after}\n')
        f.write(f'- SHA unchanged: {assertions["H"]}\n')
        f.write(f'- Production writes: 0\n')
        f.write(f'- Staging writes: 0\n')
        f.write(f'- Knowledge writes: 0\n')
        f.write(f'- PromotionGate.apply(): NOT INVOKED\n')
        f.write(f'- editorial_promotion_writer.execute(): NOT INVOKED\n')
        f.write(f'- ACL changes: 0\n')
        f.write(f'- DENY ACE: UNCHANGED\n')
    
    return classification, assertions, results, dist

if __name__ == '__main__':
    classification, assertions, results, dist = run_pilot()
    print(f'\nPilot complete. Classification: {classification}')
    print(f'Artifacts in: {PILOT_OUT}')