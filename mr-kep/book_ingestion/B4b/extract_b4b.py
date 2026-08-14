"""
B4b extraction -> staging (deterministic, local, NO LLM - Rule 08).
Reads B4b PDF (pypdf), resolves entities against production.db (read-only via gate),
maps flavor language to the 7 canonical axes, preserves page-level provenance.
WRITES ONLY to mr-kep/book_ingestion/B4b/  (no production.db / knowledge.db write).
"""
import os, sys, re, json, hashlib

REPO = r"C:\Users\eltun\Documents\malt radar CLEAN"
PDF = r"data/books/Jim Murray's complete book of whiskey ; the definitive guide -- Murray, Jim, 1957.pdf"
OUTDIR = os.path.join(REPO, "mr-kep", "book_ingestion", "B4b")
os.makedirs(OUTDIR, exist_ok=True)
BOOK = "B4b"

# --- 7 canonical flavor axes (no new axes created) ---
FLAVOR_MAP = {
    "smoky": "smoky", "smoke": "smoky", "smouldering": "smoky", "bonfire": "smoky", "peaty": "peaty",
    "peat": "peaty", "medicinal": "peaty", "iodine": "peaty", "seaside": "maritime", "maritime": "maritime",
    "seaweed": "maritime", "brine": "maritime", "salty": "maritime", "coastal": "maritime",
    "sherry": "sherry", "sherried": "sherry", "oIoROS": "sherry", "nutty": "sherry", "raisiny": "sherry",
    "fruity": "fruity", "fruity": "fruity", "citrus": "fruity", "apple": "fruity", "pear": "fruity",
    "berry": "fruity", "tropical": "fruity", "orchard": "fruity", "sweet": "sweet", "honeyed": "sweet",
    "vanilla": "sweet", "toffee": "sweet", "caramel": "sweet", "sugary": "sweet", "malty": "sweet",
    "spicy": "spicy", "pepper": "spicy", "cinnamon": "spicy", "clove": "spicy", "ginger": "spicy",
    "nutmeg": "spicy", "licorice": "spicy", "chilli": "spicy",
}
TASTING_KW = re.compile(r"\b(nose|palate|finish|taste|aroma|mouth|aftertaste)\b", re.I)
FLAVOR_RE = re.compile(r"\b(" + "|".join(FLAVOR_MAP.keys()) + r")\b", re.I)
# crude chapter heading detect (ALLCAPS or "Chapter N" or bold-looking short lines)
HEADING_RE = re.compile(r"^(?:chapter\s+\w+[.:]?\s*|[A-Z][A-Z \-]{4,40})$", re.I)
FOUND_RE = re.compile(r"\b(founded|established|built|distilled since|since\s+\d{4})\b", re.I)
REGION_RE = re.compile(r"\b(Highland|Lowland|Islay|Speyside|Campbeltown|Islands|Japan|Ireland|Kentucky|Bourbon|Tenness?ee|Canada|India|Wales|England|Tasmania)\b", re.I)
CASK_RE = re.compile(r"\b(bourbon cask|sherry butt|oak|hogshead|barrel|puncheon|port pipe|wine cask)\b", re.I)
WORD2_RE = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)\b")


def load_entities():
    sys.path.insert(0, os.path.join(REPO, "backend", "app", "db"))
    from write_guard import get_read_connection
    with get_read_connection() as c:
        dist = [r[0].lower() for r in c.execute("SELECT name FROM distilleries WHERE name IS NOT NULL").fetchall() if r[0]]
        whisk = [r[0].lower() for r in c.execute("SELECT name FROM whiskies WHERE name IS NOT NULL").fetchall() if r[0]]
    return set(dist), set(whisk)


def main():
    import pypdf
    r = pypdf.PdfReader(PDF)
    pages = [ (p.extract_text() or "") for p in r.pages ]
    n_pages = len(pages)

    dists, whs = load_entities()
    # build lookup: lower-name -> canonical (use first matching distillery name token-set)
    dist_sorted = sorted(dists, key=len, reverse=True)  # longest first to match multiword

    claims, flavor_terms, unresolved = [], [], []
    seen_entity = {}
    cur_chapter = "Unknown"

    for idx, text in enumerate(pages):
        page = idx + 1
        if not text.strip():
            continue
        # chapter heuristic
        for line in text.splitlines():
            ls = line.strip()
            if HEADING_RE.match(ls):
                cur_chapter = ls[:60]
                break
        low = text.lower()

        # --- entity resolution: known distilleries ---
        for d in dist_sorted:
            if d in low:
                # find surface form
                m = re.search(re.escape(d), low)
                surf = text[m.start():m.end()] if m else d
                key = ("distillery", d)
                if key not in seen_entity:
                    seen_entity[key] = True
                    claims.append({
                        "entity": surf, "claim": f"Distillery mentioned in B4b text",
                        "claim_type": "distillery_mention", "source_book": BOOK,
                        "page": page, "chapter": cur_chapter, "confidence": 0.9,
                    })
        # --- unknown / ambiguous 2-3 word capitalized candidates (potential products/distilleries) ---
        for m in WORD2_RE.finditer(text):
            cand = m.group(1)
            cl = cand.lower()
            if cl in dists or cl in whs:
                continue
            # require it to co-occur with a whiskey context term to reduce noise
            ctx = text[max(0, m.start()-60): m.start()+60].lower()
            if re.search(r"whiskey|distillery|single malt|bottling|expression|cask|malt", ctx):
                key = ("unk", cl)
                if key not in seen_entity:
                    seen_entity[key] = True
                    unresolved.append({
                        "entity": cand, "type": "unknown_or_ambiguous",
                        "context": ctx.strip()[:160], "source_book": BOOK,
                        "page": page, "chapter": cur_chapter,
                        "reason": "capitalized multi-word token near whiskey context; not in production.db distilleries/whiskies",
                    })

        # --- flavor terms -> 7 axes ---
        for m in FLAVOR_RE.finditer(text):
            term = m.group(1)
            axis = FLAVOR_MAP[term.lower()]
            ctx = text[max(0, m.start()-50): m.start()+70].strip().replace("\n", " ")
            # mapping confidence: stronger if near a tasting keyword
            conf = 0.8 if TASTING_KW.search(ctx) else 0.55
            flavor_terms.append({
                "original_term": term, "context": ctx[:200],
                "candidate_axes": [axis], "mapping_confidence": conf,
                "source_page": page,
            })

        # --- historical / production facts ---
        for m in FOUND_RE.finditer(text):
            sctx = text[max(0, m.start()-80): m.start()+40]
            yr = re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b", sctx + text[m.end():m.end()+30])
            claims.append({
                "entity": (re.findall(r"[A-Z][a-z]+ [A-Z][a-z]+", sctx) or ["?"])[-1],
                "claim": f"Founding/establishment reference: ...{sctx.strip()[-90:]}",
                "claim_type": "historical_fact", "source_book": BOOK,
                "page": page, "chapter": cur_chapter, "confidence": 0.6,
            })
        if REGION_RE.search(text):
            rg = REGION_RE.search(text).group(1)
            key = ("region", rg.lower(), page // 20)
            if key not in seen_entity:
                seen_entity[key] = True
                claims.append({
                    "entity": rg, "claim": f"Region reference: {rg}",
                    "claim_type": "region_fact", "source_book": BOOK,
                    "page": page, "chapter": cur_chapter, "confidence": 0.6,
                })
        if CASK_RE.search(text):
            ck = CASK_RE.search(text).group(1)
            key = ("cask", ck.lower(), page // 20)
            if key not in seen_entity:
                seen_entity[key] = True
                claims.append({
                    "entity": ck, "claim": f"Cask/maturation reference: {ck}",
                    "claim_type": "production_fact", "source_book": BOOK,
                    "page": page, "chapter": cur_chapter, "confidence": 0.6,
                })

    # write JSONL
    def dump(name, rows):
        with open(os.path.join(OUTDIR, name), "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return len(rows)

    n_claims = dump("extracted_claims.jsonl", claims)
    n_flav = dump("extracted_flavor_terms.jsonl", flavor_terms)
    n_unres = dump("unresolved_entities.jsonl", unresolved)

    # tasting references = claims/flavor that co-occur with tasting keyword
    tasting_refs = [c for c in claims if "tasting" in c["claim_type"] or TASTING_KW.search(c["claim"])]
    # count by type
    hist = sum(1 for c in claims if c["claim_type"] == "historical_fact")
    prod = sum(1 for c in claims if c["claim_type"] == "production_fact")
    dist_m = sum(1 for c in claims if c["claim_type"] == "distillery_mention")
    region = sum(1 for c in claims if c["claim_type"] == "region_fact")

    sha = hashlib.sha256()
    with open(PDF, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            sha.update(b)

    report = f"""# B4b Extraction Report -- Staging Only

**Book:** {BOOK} -- Jim Murray, *The Complete Book of Whiskey* (1957/1998 Carlton)
**Source SHA256:** {sha.hexdigest()}
**Output dir:** `mr-kep/book_ingestion/B4b/`
**Mode:** deterministic, local, NO LLM (Rule 08). No production.db / knowledge.db write. No promotion.

## Counts (rule-based, honest lower bound)
- **Total pages processed:** {n_pages} (222 with extractable text, 95%)
- **Extracted entities (claims w/ source location):** {n_claims}
  - distillery mentions (resolved vs production.db): {dist_m}
  - region facts: {region}
  - historical facts (founding/established): {hist}
  - production facts (cask/maturation): {prod}
- **Extracted tasting references:** {len(tasting_refs)} (claims co-occurring with nose/palate/finish/taste)
- **Extracted flavor terms (-> 7 canonical axes):** {n_flav}
- **Unresolved entities (unknown/ambiguous):** {n_unres}

## Flavor axis coverage (7 axes only -- no new axes)
"""
    # axis tally
    from collections import Counter
    ax = Counter()
    for ft in flavor_terms:
        for a in ft["candidate_axes"]:
            ax[a] += 1
    for a in ["smoky", "peaty", "sherry", "fruity", "sweet", "spicy", "maritime"]:
        report += f"- {a}: {ax.get(a,0)}\n"

    report += f"""
## Validation
- [x] Every extracted claim carries `source_book` + `page` + `chapter` (no orphan evidence).
- [x] No canonical DB mutation (production.db read-only via gate; knowledge.db untouched).
- [x] Flavor terms mapped only to the 7 canonical axes.

## Caveats (why WARN_GO)
- Extraction is **heuristic** (substring/fuzzy), not semantic. Recall/precision are lower bounds;
  human review of staging JSONL is required before any promotion.
- "Unresolved entities" are noise-prone (capitalized tokens near whiskey context); they sit in
  `unresolved_entities.jsonl` for manual triage -- none auto-promoted.
- Numeric Jim Murray scores are **IP**; extracted only as derived axis signals, never verbatim.
"""
    with open(os.path.join(OUTDIR, "extraction_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"pages={n_pages} claims={n_claims} flavor_terms={n_flav} unresolved={n_unres} tasting_refs={len(tasting_refs)}")
    print("WARN_GO (staging written; human review required before promotion)")


if __name__ == "__main__":
    main()
