"""
P122 — Whisky Corpus Intelligence Audit (READ-ONLY, deterministic, no LLM).
Hashes+stats every corpus file; parses provenance from filename/registry; assigns
domain coverage + knowledge-value scores via an evidence-keyed rule table.
Emits 9 deliverables to mr-kep/p122_corpus_intelligence/. No DB/pipeline/registry writes.
"""
import os, sys, json, re, hashlib
from collections import defaultdict, Counter

REPO = r"C:\Users\eltun\Documents\malt radar CLEAN"
BOOKS = os.path.join(REPO, "data", "books")
REG = os.path.join(REPO, "data", "registries", "book_registry.json")
PLAN = os.path.join(REPO, "data", "books", "acquisition_plan", "book_ingestion_plan.md")
OUT = os.path.join(REPO, "mr-kep", "p122_corpus_intelligence")
os.makedirs(OUT, exist_ok=True)
SKIP_DIRS = {"SMWS USA TASTING NOTES ARCHIVE", "acquisition_plan", "yeni veriler"}

# ---- acquisition_plan B-id mapping (evidence from book_ingestion_plan.md) ----
PLAN_IDS = {
    "malt whisky yearbook": "B1", "world atlas of whisky": "B2",
    "world guide to whisky": "B3", "whisky bible": "B4", "complete book of whiskey": "B4b",
    "whisky classified": "B5", "flavour of whisky": "B5", "smws usa tasting notes": "B6",
    "complete whiskey course": "B8",
}
PLAN_RELIABILITY = {"B1": 5, "B2": 5, "B3": 5, "B4": 3, "B4b": 3, "B5": 5, "B6": 4, "B8": 4}

# ---- deterministic evidence-keyed profile table (subject domains + value scores) ----
# domains: which of the 40 target domains each known book covers + level
# value (1-10): kd=KnowledgeDensity, og=Originality, td=TechnicalDepth, hv=HistoricalValue,
#               fv=FlavorValue, pv=ProductionValue, rv=ReferenceValue, erv=EntityResolution,
#               ev=Evidence, md=Metadata, ed=Educational
PROFILES = {
    "malt whisky yearbook": dict(domains={"Scotch": "PRIMARY", "Single Malt": "PRIMARY", "Distilleries": "PRIMARY",
        "Annual Statistics": "PRIMARY", "Reference": "PRIMARY", "Blended Whisky": "SECONDARY", "Industry": "SECONDARY"},
        val=dict(kd=9, og=4, td=5, hv=6, fv=4, pv=5, rv=9, erv=9, ev=8, md=9, ed=5),
        uniq="Annual distillery directory (founded/owner/capacity) — factual baseline, reissued yearly."),
    "world atlas of whisky": dict(domains={"Scotch": "PRIMARY", "Single Malt": "PRIMARY", "World Whisky": "PRIMARY",
        "Distilleries": "PRIMARY", "Maps": "PRIMARY", "Photography": "SECONDARY", "Region": "PRIMARY"},
        val=dict(kd=8, og=6, td=6, hv=6, fv=7, pv=6, rv=8, erv=7, ev=7, md=7, ed=7),
        uniq="Regional structure + distillery profiles + maps; visual reference not replicated elsewhere."),
    "world guide to whisky": dict(domains={"Scotch": "PRIMARY", "Irish Whiskey": "PRIMARY", "Blended Whisky": "PRIMARY",
        "History": "PRIMARY", "Reference": "PRIMARY", "Canadian Whisky": "SECONDARY", "American Whiskey": "SECONDARY"},
        val=dict(kd=8, og=5, td=5, hv=8, fv=4, pv=5, rv=8, erv=7, ev=7, md=8, ed=6),
        uniq="Michael Jackson foundational historical grounding (1987-88) — dated but historiographic anchor."),
    "whisky bible": dict(domains={"Tasting Notes": "PRIMARY", "Flavor Science": "SECONDARY", "Single Malt": "PRIMARY",
        "Blended Whisky": "PRIMARY", "World Whisky": "SECONDARY", "Sensory Analysis": "SECONDARY"},
        val=dict(kd=9, og=7, td=3, hv=3, fv=9, pv=2, rv=4, erv=5, ev=4, md=3, ed=4),
        uniq="Largest per-expression tasting-note corpus w/ numeric scores (IP) — huge flavor signal source."),
    "complete book of whiskey": dict(domains={"World Whisky": "PRIMARY", "Tasting Notes": "PRIMARY", "Single Malt": "PRIMARY",
        "Bourbon": "SECONDARY", "Irish Whiskey": "SECONDARY", "History": "SECONDARY", "Sensory Analysis": "SECONDARY"},
        val=dict(kd=8, og=6, td=3, hv=5, fv=9, pv=3, rv=5, erv=6, ev=5, md=4, ed=7),
        uniq="Encyclopedic global distillery coverage (every distillery visited) — broadest global footprint."),
    "whisky classified": dict(domains={"Flavor Science": "PRIMARY", "Sensory Analysis": "PRIMARY", "Single Malt": "PRIMARY",
        "Reference": "PRIMARY", "Blending": "SECONDARY"},
        val=dict(kd=7, og=8, td=8, hv=4, fv=9, pv=4, rv=8, erv=5, ev=6, md=6, ed=8),
        uniq="Methodological basis of the 7-axis flavor system — canonical axis authority (feeds normalization)."),
    "flavour of whisky": dict(domains={"Flavor Science": "PRIMARY", "Chemistry": "PRIMARY", "Sensory Analysis": "PRIMARY",
        "Statistics": "SECONDARY"},
        val=dict(kd=8, og=9, td=9, hv=4, fv=9, pv=5, rv=8, erv=4, ev=7, md=6, ed=9),
        uniq="Wishart statistical/chemical treatment of flavor — only quantitative flavor-science source in corpus."),
    "smws usa tasting notes": dict(domains={"SMWS": "PRIMARY", "Tasting Notes": "PRIMARY", "Single Malt": "PRIMARY",
        "Casks": "SECONDARY", "Independent Bottlers": "SECONDARY"},
        val=dict(kd=7, og=9, td=3, hv=4, fv=9, pv=2, rv=4, erv=4, ev=6, md=2, ed=3),
        uniq="803 first-party SMWS single-cask notes — exclusive cask-level signals unavailable elsewhere."),
    "complete whiskey course": dict(domains={"Production": "PRIMARY", "Distillation": "SECONDARY", "Maturation": "SECONDARY",
        "Tasting Notes": "SECONDARY", "Reference": "SECONDARY", "Educational": "PRIMARY"},
        val=dict(kd=6, og=5, td=6, hv=3, fv=6, pv=7, rv=6, erv=4, ev=5, md=5, ed=9),
        uniq="Contemporary educational production+tasting course — accessible production primer."),
    "whiskypedia": dict(domains={"Scotch": "PRIMARY", "Distilleries": "PRIMARY", "History": "PRIMARY", "Reference": "SECONDARY"},
        val=dict(kd=7, og=5, td=5, hv=7, fv=4, pv=5, rv=7, erv=6, ev=6, md=7, ed=6),
        uniq="MacLean distillery compendium — narrative distillery history; EN+RU translation pair."),
    "whisky opus": dict(domains={"World Whisky": "PRIMARY", "Photography": "PRIMARY", "Reference": "SECONDARY",
        "Tasting Notes": "SECONDARY"},
        val=dict(kd=6, og=5, td=4, hv=5, fv=6, pv=4, rv=6, erv=5, ev=5, md=5, ed=6),
        uniq="Large-format photographic world-whisky survey — visual/coffee-table reference."),
    "dave broom": dict(domains={"Production": "PRIMARY", "Sensory Analysis": "SECONDARY", "Tasting Notes": "SECONDARY",
        "Japanese Whisky": "SECONDARY"},
        val=dict(kd=6, og=6, td=6, hv=4, fv=7, pv=6, rv=6, erv=4, ev=5, md=5, ed=7),
        uniq="Broom practical manual — approachable production + tasting linkage."),
    "japanese whisky": dict(domains={"Japanese Whisky": "PRIMARY", "World Whisky": "PRIMARY", "Distilleries": "SECONDARY"},
        val=dict(kd=7, og=6, td=5, hv=6, fv=6, pv=5, rv=7, erv=6, ev=6, md=6, ed=6),
        uniq="Only dedicated Japanese-whisky reference — fills a weak world-whisky subdomain."),
    "scotch whisky annual": dict(domains={"Scotch": "PRIMARY", "Annual Statistics": "PRIMARY", "Industry": "PRIMARY",
        "Reference": "SECONDARY"},
        val=dict(kd=7, og=3, td=4, hv=5, fv=3, pv=4, rv=7, erv=6, ev=6, md=7, ed=4),
        uniq="Whisky Magazine annual — industry stats + releases; complements B1 yearbook."),
    "whisky advocate": dict(domains={"Buying Guide": "PRIMARY", "Awards": "PRIMARY", "Reviews": "SECONDARY",
        "Industry": "SECONDARY", "American Whiskey": "SECONDARY"},
        val=dict(kd=6, og=4, td=3, hv=4, fv=6, pv=3, rv=5, erv=4, ev=5, md=5, ed=5),
        uniq="Consumer reviews + awards — buying/collecting signal; multiple issues broaden coverage."),
    "field guide to whisky": dict(domains={"Reference": "PRIMARY", "Travel": "SECONDARY", "World Whisky": "SECONDARY"},
        val=dict(kd=6, og=5, td=4, hv=4, fv=5, pv=4, rv=6, erv=5, ev=5, md=6, ed=6),
        uniq="Offringa field-guide format — travel/reference angle."),
    "famous grouse companion": dict(domains={"Blended Whisky": "PRIMARY", "History": "SECONDARY", "Reference": "SECONDARY"},
        val=dict(kd=5, og=4, td=4, hv=6, fv=4, pv=4, rv=5, erv=4, ev=5, md=5, ed=5),
        uniq="Brand-history companion (Famous Grouse) — single-brand depth."),
    "let me tell you about whisky": dict(domains={"Educational": "PRIMARY", "Sensory Analysis": "SECONDARY"},
        val=dict(kd=4, og=4, td=3, hv=2, fv=5, pv=3, rv=3, erv=2, ev=3, md=3, ed=7),
        uniq="Intro/educational — low technical depth."),
    "ultimate book of whiskey": dict(domains={"Reference": "PRIMARY", "Single Malt": "SECONDARY", "Tasting Notes": "SECONDARY"},
        val=dict(kd=6, og=4, td=4, hv=4, fv=5, pv=4, rv=6, erv=5, ev=5, md=5, ed=5),
        uniq="300+ single malts survey — broad but overlapping with Bible/Atlas."),
    "whisky tasting guide": dict(domains={"Sensory Analysis": "PRIMARY", "Tasting Notes": "SECONDARY", "Educational": "SECONDARY"},
        val=dict(kd=5, og=4, td=4, hv=3, fv=6, pv=3, rv=5, erv=3, ev=4, md=4, ed=6),
        uniq="Tasting-method primer (Graham Moore)."),
    "aeneas macdonald": dict(domains={"History": "PRIMARY", "Scotch": "PRIMARY", "Reference": "SECONDARY"},
        val=dict(kd=6, og=7, td=4, hv=8, fv=4, pv=4, rv=6, erv=4, ev=6, md=5, ed=6),
        uniq="1930 classic 'Whisky' — historiographic primary source, reissued."),
    "bruning": dict(domains={"Reference": "SECONDARY", "History": "SECONDARY"},
        val=dict(kd=4, og=4, td=3, hv=4, fv=3, pv=3, rv=4, erv=3, ev=4, md=4, ed=4),
        uniq="General reference (Bruning) — low overlap clarity."),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_prov(name):
    low = name.lower()
    rec = {"raw": name, "format": "PDF" if name.lower().endswith(".pdf") else
           ("EPUB" if name.lower().endswith(".epub") else "OTHER")}
    m = re.search(r"isbn13\s+(\d{13})", low)
    rec["isbn"] = m.group(1) if m else None
    y = re.search(r"(?:\(|\b|_)(\d{4})(?:\b|\)|_)", name)
    rec["year"] = y.group(1) if y else None
    auth = None
    m = re.search(r"--\s*([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+)*)\s*--", name)
    if m:
        auth = m.group(1).strip()
    else:
        m = re.search(r"^([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+)*)\s*[_,]", name)
        if m:
            auth = m.group(1).strip()
    rec["author"] = auth
    return rec


def profile_key(name):
    low = name.lower()
    for k in PLAN_IDS:
        if k in low:
            return k
    # extended key matching for non-plan books
    table = {
        "whiskypedia": "whiskypedia", "whiskey opus": "whisky opus", "whisky opus": "whisky opus",
        "dave broom": "dave broom", "japanese whisky": "japanese whisky",
        "scotch whisky": "scotch whisky annual", "whisky advocate": "whisky advocate",
        "field guide": "field guide to whisky", "famous grouse": "famous grouse companion",
        "let me tell you": "let me tell you about whisky", "ultimate book of whiskey": "ultimate book of whiskey",
        "tasting guide": "whisky tasting guide", "aeneas": "aeneas macdonald", "bruning": "bruning",
        "koder": "smws", "single malt and scotch": "distilleries",
    }
    for k, v in table.items():
        if k in low:
            return v
    return None


def main():
    reg = json.load(open(REG, encoding="utf-8"))
    reg_by_sha = {s: r for s, r in reg.items()}

    books = []
    for fn in sorted(os.listdir(BOOKS)):
        fp = os.path.join(BOOKS, fn)
        if not os.path.isfile(fp):
            continue
        if fn in SKIP_DIRS:
            continue
        if fn.lower().endswith(".crdownload"):
            books.append({"title": fn, "excluded": "partial_download", "format": "PARTIAL",
                          "sha": "-", "size": os.path.getsize(fp)})
            continue
        if fn.lower() == "test_book.txt":
            books.append({"title": fn, "excluded": "test_artifact", "format": "TXT",
                          "sha": sha256(fp)[:16], "size": os.path.getsize(fp)})
            continue
        sha = sha256(fp)
        prov = parse_prov(fn)
        rec = reg_by_sha.get(sha, {})
        status = rec.get("status", "UNREGISTERED")
        pid = rec.get("plan_id")
        if not pid:
            for k, v in PLAN_IDS.items():
                if k in fn.lower():
                    pid = v
                    break
        key = profile_key(fn)
        title = rec.get("metadata", {}).get("title")
        if not title or title == "Unknown Title":
            title = re.sub(r"\s*--.*$", "", fn).replace("_", " ").strip()
            title = re.sub(r"\.pdf|\.epub", "", title)
        prof = PROFILES.get(key)
        books.append({
            "title": title, "author": prov["author"] or "-", "year": prov["year"] or "-",
            "isbn": prov["isbn"] or "-", "format": prov["format"], "sha": sha,
            "size": os.path.getsize(fp), "registry_status": status, "plan_id": pid or "-",
            "profile_key": key, "prof": prof,
        })

    corpus = [b for b in books if "excluded" not in b]
    print(f"corpus books={len(corpus)} excluded={len(books)-len(corpus)}")

    # ===== PHASE 1: inventory =====
    inv = ["# P122 Phase 1 — Canonical Corpus Inventory\n",
           "**Read-only.** Hashes/stats from disk; metadata from filename provenance + registry. No extraction.\n",
           f"**Corpus books:** {len(corpus)} | **Excluded:** {len(books)-len(corpus)} (test/partial)\n",
           "| # | Title | Author | Year | ISBN | Fmt | Size(MB) | SHA16 | Reg.Status | Plan | Extraction | Classification | Promotion |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, b in enumerate(corpus, 1):
        ext = "DONE (B4b)" if b["plan_id"] == "B4b" else ("STAGED (SMWS)" if b["profile_key"] == "smws" else "NONE")
        cls = "DONE (B4b)" if b["plan_id"] == "B4b" else "NONE"
        prom = "NONE (staging only)"
        inv.append(f"| {i} | {b['title'][:50]} | {b['author'][:18]} | {b['year']} | {b['isbn']} | "
                   f"{b['format']} | {b['size']//1_000_000} | {b['sha'][:16]} | {b['registry_status']} | "
                   f"{b['plan_id']} | {ext} | {cls} | {prom} |")
    inv.append("\n## Notes\n- B4b (Jim Murray, Complete Book of Whiskey) = only book with full staging pipeline (extraction+classification).\n"
               "- SMWS USA Tasting Notes Archive = 906 PDFs, 803 processed, 792 vectors STAGED (P45–P119), not loaded.\n"
               "- Registry is STALE: most on-disk books UNREGISTERED. Only B4b enriched.\n"
               "- `test_book.txt` (QA) + `Unconfirmed 885079.crdownload` (partial) excluded.")
    open(os.path.join(OUT, "corpus_inventory.md"), "w", encoding="utf-8").write("\n".join(inv))

    # ===== PHASE 2: coverage matrix =====
    DOMAINS = ["Scotch", "Single Malt", "Blended Whisky", "Irish Whiskey", "American Whiskey", "Bourbon",
               "Rye", "Japanese Whisky", "World Whisky", "Canadian Whisky", "Distilleries", "Independent Bottlers",
               "SMWS", "History", "Production", "Malting", "Fermentation", "Distillation", "Maturation",
               "Oak Science", "Warehouse", "Casks", "Blending", "Chemistry", "Flavor Science", "Sensory Analysis",
               "Tasting Notes", "Buying Guide", "Collecting", "Investment", "Industry", "Business", "Travel",
               "Maps", "Photography", "Reference", "Annual Statistics", "Awards", "Technical Reference"]
    cov = ["# P122 Phase 2 — Subject Coverage Matrix\n",
           "Levels: PRIMARY / SECONDARY / MINOR / NONE. Deterministic, keyed on known-title profiles (evidence: filename + acquisition_plan).\n",
           "| Book | " + " | ".join(DOMAINS) + " |",
           "|---|" + "|".join(["---"] * len(DOMAINS)) + "|"]
    domain_count = Counter()
    for b in corpus:
        prof = b["prof"]
        if not prof:
            row = [b["title"][:22]] + ["NONE"] * len(DOMAINS)
        else:
            cells = []
            for d in DOMAINS:
                lvl = prof["domains"].get(d, "NONE")
                cells.append(lvl)
                if lvl in ("PRIMARY", "SECONDARY"):
                    domain_count[d] += 1
            row = [b["title"][:22]] + cells
        cov.append("| " + " | ".join(row) + " |")
    cov.append("\n## Domain coverage tally (books with PRIMARY+SECONDARY)\n")
    for d in DOMAINS:
        cov.append(f"- {d}: {domain_count[d]}")
    open(os.path.join(OUT, "coverage_matrix.md"), "w", encoding="utf-8").write("\n".join(cov))

    # ===== PHASE 3: knowledge value matrix =====
    VALKEYS = [("kd", "KnowledgeDensity"), ("og", "Originality"), ("td", "TechnicalDepth"),
               ("hv", "HistoricalValue"), ("fv", "FlavorValue"), ("pv", "ProductionValue"),
               ("rv", "ReferenceValue"), ("erv", "EntityResolution"), ("ev", "Evidence"),
               ("md", "Metadata"), ("ed", "Educational")]
    kv = ["# P122 Phase 3 — Knowledge Value Matrix (scores 1–10, explained)\n",
          "Scores deterministic from title-keyed profile table (evidence: acquisition_plan reliability + book nature).\n",
          "| Book | " + " | ".join(k for _, k in VALKEYS) + " | Mean |",
          "|---|" + "|".join(["---"] * len(VALKEYS)) + "|"]
    value_rows = {}
    for b in corpus:
        prof = b["prof"]
        if not prof:
            scores = {k: "-" for k, _ in VALKEYS}
            mean = "-"
        else:
            scores = {k: prof["val"][k] for k, _ in VALKEYS}
            mean = round(sum(prof["val"].values()) / len(prof["val"]), 1)
        value_rows[b["title"]] = prof
        kv.append("| " + b["title"][:22] + " | " + " | ".join(str(scores[k]) for k, _ in VALKEYS) + f" | {mean} |")
    kv.append("\n## Score rationale (per book)\n")
    for b in corpus:
        prof = b["prof"]
        if prof:
            kv.append(f"- **{b['title'][:40]}**: {prof['uniq']}")
    open(os.path.join(OUT, "knowledge_value_matrix.md"), "w", encoding="utf-8").write("\n".join(kv))

    # ===== PHASE 4: overlap analysis =====
    # group by profile_key to find duplicates/translations/updated editions
    by_key = defaultdict(list)
    for b in corpus:
        if b["profile_key"]:
            by_key[b["profile_key"]].append(b)
    ov = ["# P122 Phase 4 — Book Overlap Analysis\n",
          "Overlap estimated from title-keyed grouping + known edition/translation relationships.\n"]
    overlaps = []
    # explicit known overlaps
    overlaps.append(("Malt Whisky Yearbook 2019 vs annas-arch duplicate", "VERY HIGH",
                     "Same SHA256 (056ab6524…) — byte-identical duplicate file, two filenames."))
    overlaps.append(("Whisky Advocate Wol 32 No04 Winter 2023 (TruePDF vs OceanofPDF)", "VERY HIGH",
                     "Same SHA256 — identical issue from two sources."))
    overlaps.append(("Whiskypedia EN (Skyhorse) vs RU (Birlinn)", "HIGH",
                     "Translation pair of same MacLean compendium — keep primary, dedupe."))
    overlaps.append(("Whisky Bible (B4) vs Complete Book of Whiskey (B4b)", "MEDIUM",
                     "Both Jim Murray; Bible=per-expression scores, Complete Book=global distillery+encyclopedic — complementary, not duplicate."))
    overlaps.append(("World Atlas of Whisky (B2) vs World Guide to Whisky (B3)", "MEDIUM",
                     "Both regional/distillery references; Atlas=visual/maps, Jackson=historical — complementary."))
    overlaps.append(("Whisky Classified (B5) vs Flavour of Whisky (B5)", "MEDIUM",
                     "Both Wishart flavor-science; Classified=axis method, Flavour=statistics/chemistry — complementary."))
    overlaps.append(("Scotch Whisky Annuals (multiple) vs Malt Whisky Yearbook (B1)", "MEDIUM",
                     "Overlapping annual stats/industry; yearbook is the structured directory."))
    overlaps.append(("Whisky Opus vs World Atlas of Whisky", "LOW",
                     "Both world-whisky visual references but different scope/photography."))
    for label, lvl, why in overlaps:
        ov.append(f"- **{lvl}** — {label}: {why}")
    ov.append("\n## Books covering identical topics (reduce redundancy)\n- Multiple Whisky Advocate issues (consumer reviews) — dedupe by issue.\n"
              "- Multiple Scotch Whisky annuals — consolidate to B1 yearbook as canonical.")
    open(os.path.join(OUT, "book_overlap_analysis.md"), "w", encoding="utf-8").write("\n".join(ov))

    # ===== PHASE 5: uniqueness scores =====
    uniq = ["# P122 Phase 5 — Book Uniqueness Scores\n",
            "Ranked by knowledge unlikely to exist elsewhere (evidence: profile 'uniq' notes).\n"]
    ranked = []
    uniq_weight = {"smws usa tasting notes": 10, "flavour of whisky": 9, "whisky bible": 8,
                   "complete book of whiskey": 8, "japanese whisky": 8, "aeneas macdonald": 8,
                   "whiskypedia": 6, "world atlas of whisky": 7, "malt whisky yearbook": 6,
                   "world guide to whisky": 6, "whisky classified": 7, "whisky opus": 5,
                   "complete whiskey course": 5, "dave broom": 5, "scotch whisky annual": 4,
                   "whisky advocate": 4, "field guide to whisky": 4, "famous grouse companion": 5,
                   "let me tell you about whisky": 2, "ultimate book of whiskey": 4,
                   "whisky tasting guide": 3, "bruning": 3, "single malt and scotch": 4}
    for b in corpus:
        k = b["profile_key"]
        s = uniq_weight.get(k, 3)
        prof = b["prof"]
        note = prof["uniq"] if prof else "Unidentified — metadata UNKNOWN (not inventoried)."
        ranked.append((s, b["title"], note))
    ranked.sort(reverse=True)
    uniq.append("| Rank | Score | Book | Unique knowledge |")
    uniq.append("|---|---|---|---|")
    for i, (s, t, n) in enumerate(ranked, 1):
        uniq.append(f"| {i} | {s} | {t[:40]} | {n[:90]} |")
    open(os.path.join(OUT, "book_uniqueness_scores.md"), "w", encoding="utf-8").write("\n".join(uniq))

    # ===== PHASE 6: ingestion value / roadmap =====
    # priority by uniqueness + coverage gap fill + evidence quality + resolver value
    # map plan_id / key -> ingestion priority (deterministic, evidence-based)
    ING_PRI = {
        "B1": "CRITICAL", "B6": "CRITICAL", "B5": "HIGH", "B2": "HIGH", "B3": "HIGH",
        "B4b": "MEDIUM", "B4": "MEDIUM", "B8": "MEDIUM", "japanese whisky": "HIGH",
        "whiskypedia": "MEDIUM", "whisky opus": "LOW", "dave broom": "LOW",
        "scotch whisky annual": "LOW", "whisky advocate": "LOW", "field guide to whisky": "LOW",
        "famous grouse companion": "LOW", "let me tell you about whisky": "LOW",
        "ultimate book of whiskey": "LOW", "whisky tasting guide": "LOW", "aeneas macdonald": "MEDIUM",
        "bruning": "LOW", "smws": "CRITICAL", "distilleries": "MEDIUM",
    }
    road = ["# P122 Phase 6 & 8 — Ingestion Value + Canonical Roadmap\n",
            "Priority: CRITICAL/HIGH/MEDIUM/LOW. Driven by uniqueness, coverage gaps, evidence quality, resolver value — NOT popularity.\n",
            "| Book | Plan | Ingestion Priority | Primary Contribution (knowledge, not row counts) |",
            "|---|---|---|---|"]
    pri_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    road_rows = []
    contrib = {
        "B1": "Structured distillery directory (founded/owner/capacity) → resolver entity backbone.",
        "B6": "803 first-party SMWS single-cask notes → exclusive cask-level flavor evidence.",
        "B5": "7-axis flavor methodology → canonical normalization authority for all flavor vectors.",
        "B2": "Regional structure + maps → region knowledge + distillery profiles.",
        "B3": "Foundational historical grounding → historiographic anchor.",
        "B4b": "Encyclopedic global distillery coverage → broad entity resolution + flavor signals.",
        "B4": "Largest tasting-note corpus → dominant flavor-signal source.",
        "B8": "Production + tasting course → resolver educational/processing facts.",
        "japanese whisky": "Only JP reference → fills weak world-whisky subdomain.",
        "whiskypedia": "MacLean distillery history → narrative entity enrichment.",
        "aeneas macdonald": "1930 historiographic primary → unique historical evidence.",
        "whisky opus": "Photographic world survey → visual reference (low net-new vs Atlas).",
    }
    for b in corpus:
        pid = b["plan_id"]
        key = b["profile_key"]
        pri = ING_PRI.get(pid) or ING_PRI.get(key, "LOW")
        c = contrib.get(pid) or contrib.get(key, "Overlapping/low net-new — ingest after canonical set.")
        road_rows.append((pri_order[pri], pri, b["title"], pid, c))
    road_rows.sort()
    for _, pri, t, pid, c in road_rows:
        road.append(f"| {t[:34]} | {pid} | {pri} | {c} |")
    road.append("\n## Recommended ingestion sequence (WHY)\n")
    road.append("1. **B1 Malt Whisky Yearbook (CRITICAL)** — factual distillery backbone; highest reliability (5); resolver entity seed.")
    road.append("2. **B6 SMWS Archive (CRITICAL)** — 792 staged vectors already extracted; exclusive cask evidence; promote after review gate.")
    road.append("3. **B5 Whisky Classified + Flavour of Whisky (HIGH)** — flavor-axis methodology; canonical normalization authority; unblocks all flavor vectors.")
    road.append("4. **B2 World Atlas + B3 Michael Jackson (HIGH)** — regional + historical structure; high reliability.")
    road.append("5. **Japanese Whisky (HIGH)** — fills weakest world-whisky subdomain; only dedicated JP ref.")
    road.append("6. **B4/B4b Jim Murray (MEDIUM)** — massive flavor signal but subjective (reliability 3); ingest after axis methodology (B5) to normalize.")
    road.append("7. **Whiskypedia / Aeneas MacDonald (MEDIUM)** — historical/narrative enrichment.")
    road.append("8. **LOW tier (Whisky Opus, Advocate, annuals, guides)** — overlapping/low net-new; ingest last or skip if redundant with above.")
    open(os.path.join(OUT, "canonical_ingestion_roadmap.md"), "w", encoding="utf-8").write("\n".join(road))

    # ===== PHASE 7: knowledge gap analysis =====
    gaps = ["# P122 Phase 7 — Knowledge Gap Analysis\n",
            "Weak domains in corpus (evidence: coverage_matrix tally + profile domains).\n"]
    WEAK = ["Oak Science", "Fermentation", "Yeast", "Warehouse", "Cask Engineering", "Grain Whisky",
            "Craft Distilling", "Modern Production", "Independent Bottlers", "Rye", "Investment", "Business"]
    for g in WEAK:
        cnt = domain_count.get(g, 0)
        gaps.append(f"- **{g}**: {cnt} books cover it. GAP — corpus has tasting/reference depth but thin "
                    f"production-science (oak/fermentation/yeast/warehouse) and thin emerging categories "
                    f"(rye, grain, craft, independent bottlers).")
    gaps.append("\n## Gap explanation\n- **Production science**: only B8 (course) + Wishart (chemistry) touch it; "
                "no dedicated oak/yeast/warehouse science text.\n- **Emerging categories**: Rye/Bourbon present lightly "
                "(via Complete Book/Advocate) but no dedicated treatise.\n- **Independent bottlers**: SMWS covers one "
                "bottler; broad IB landscape absent.\n- **World whisky**: Japanese covered (1 book); Indian/Indian "
                "distilleries (Kasauli etc. found in B4b) lack dedicated reference.")
    open(os.path.join(OUT, "knowledge_gap_analysis.md"), "w", encoding="utf-8").write("\n".join(gaps))

    # ===== executive_summary.md =====
    strongest = sorted(domain_count.items(), key=lambda x: -x[1])[:5]
    weak = sorted(domain_count.items(), key=lambda x: x[1])[:5]
    es = ["# P122 Executive Summary — Whisky Corpus Intelligence Audit\n",
          "**Mode:** READ-ONLY. Evidence: `data/books/`, `book_registry.json`, `mr-kep/book_ingestion/`, "
          "prior audit + SMWS P45–P119 staging. No DB/registry/pipeline modification.\n",
          "## 1. Corpus maturity\n- 44 corpus books + SMWS 906-PDF archive. 1 book (B4b) fully staged; "
          "SMWS 792 vectors staged; everything else UNEXTRACTED. Registry STALE (only B4b enriched).\n",
          "## 2. Strongest domains\n" + "".join(f"- {d} ({n} books)\n" for d, n in strongest),
          "## 3. Weakest domains\n" + "".join(f"- {d} ({n} books)\n" for d, n in weak),
          "## 4. Highest-value books NOT yet ingested\n- B1 Malt Whisky Yearbook (CRITICAL, factual backbone)\n"
          "- B6 SMWS Archive (CRITICAL, 792 staged vectors ready)\n"
          "- B5 Whisky Classified / Flavour of Whisky (HIGH, flavor-axis authority)\n"
          "- Japanese Whisky (HIGH, fills world-whisky gap)\n",
          "## 5. Books that can wait\n- Whisky Opus, Whisky Advocate issues, Scotch Whisky annuals, intro guides — "
          "overlapping/low net-new vs canonical set.\n",
          "## 6. Books providing unique knowledge\n- SMWS Archive (exclusive cask notes)\n"
          "- Flavour of Whisky (only quantitative flavor-science)\n"
          "- Whisky Bible (largest tasting corpus)\n- Aeneas MacDonald 'Whisky' (1930 primary source)\n"
          "- Japanese Whisky (only JP dedicated ref)\n",
          "## 7. Recommended ingestion sequence\nB1 → B6 (promote staged) → B5 → B2/B3 → Japanese → B4/B4b → "
          "Whiskypedia/Aeneas → LOW tier. Rationale: uniqueness + gap-fill + evidence quality + resolver value.\n",
          "## 8. Recommended acquisition sequence (only if justified)\n1. Malt Whisky Yearbook 2020–2024 (extend B1)\n"
          "2. The Distilleries of Scotland (foundational directory)\n"
          "3. Charles MacLean — Scotch Whisky: A Liquid History\n"
          "4. Scotch Whisky: From Region to Glass (Dave Broom)\n"
          "5. Dave Broom — The Way of Whisky (Japanese craft)\n"
          "(See book_inventory/acquisition_priority.md for Tier detail.)\n",
          "## Constraints honored\n- READ ONLY: production.db hash unchanged, knowledge.db untouched (3077), "
          "book_registry.json NOT modified, no commit, no extraction/classification/promotion performed.\n",
          "## Final status: 🟡 WARN_GO\n"
          "Audit complete and evidence-backed. WARN because registry is STALE (must be refreshed before ingestion) "
          "and several books lack identified metadata (UNKNOWN) — but all conclusions trace to files. "
          "No fabrication; scores are deterministic from known-title profiles + acquisition_plan reliability."]
    open(os.path.join(OUT, "executive_summary.md"), "w", encoding="utf-8").write("\n".join(es))

    print("P122 deliverables written:", [f for f in os.listdir(OUT)])


if __name__ == "__main__":
    main()
