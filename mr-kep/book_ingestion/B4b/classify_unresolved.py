"""
B4b unresolved-entity classification (deterministic, LLM-free, staging-only).
Reads unresolved_entities.jsonl -> candidate_classification.jsonl + classification_report.md.
No DB writes; preserves original text/page/context; adds classification + confidence + reason.
"""
import os, sys, json, re
from collections import Counter

REPO = r"C:\Users\eltun\Documents\malt radar CLEAN"
OUT = os.path.join(REPO, "mr-kep", "book_ingestion", "B4b")
IN = os.path.join(OUT, "unresolved_entities.jsonl")
CLS = os.path.join(OUT, "candidate_classification.jsonl")
REP = os.path.join(OUT, "classification_report.md")

# known persons (author + recognizable)
PERSON_RE = re.compile(r"\b(jim murray|murray|jack|john|james|william|george|robert|thomas|elizabeth|michael)\b", re.I)
AWARD_RE = re.compile(r"\b(award|medal|festival|show|trophy|competition|champion)\b", re.I)
CORP_RE = re.compile(r"\b(ltd|plc|inc|company|co\.|corp|limited|gmbh|sa\b|ab\b|nv\b)\b", re.I)
# singular distillery name (incl. OCR 'distillenes'); plural 'distilleries' is a section heading
DIST_SINGULAR_RE = re.compile(r"(distiller|distillenes|distillery)$", re.I)
DIST_PLURAL_RE = re.compile(r"distilleries$", re.I)
PRODUCT_HINT = re.compile(r"\b(single malt|blend|bottling|reserved|select|reserve|special|edition|cask|aged|year old)\b", re.I)
# tightened heading vocabulary (section/chapter titles, not just 'the ' prefix)
HEADING_VOCAB = ("the history", "the basic process", "whisky terms", "whisky diaspora",
                 "the malt distilleries", "the whiskey distilleries", "the principal malt",
                 "the other principal", "other american", "the whisky distillenes",
                 "list of", "an a-z", "how to enjoy", "introduction", "contents",
                 "the world", "scottish malt whisky", "irish whiskey", "early times")
OCR_JUNK_RE = re.compile(r"[«@*%=]|vvh|vvhiskey|vvhisky|co oq")  # OCR artifacts


def classify(r):
    ent = r.get("entity", "").strip()
    ctx = (r.get("context") or "").lower()
    elow = ent.lower()
    reason = []

    # 1) BOOK_METADATA: section/chapter headings (tightened). Plural 'distilleries' = listing heading.
    if (DIST_PLURAL_RE.search(elow)
            or any(elow.startswith(h) or h in elow for h in HEADING_VOCAB)
            or any(w in ctx for w in ["chapter", "appendix", "glossary", "index", "contents", "an a-z", "how to enjoy"])):
        reason.append("section/chapter heading or book front/back-matter reference")
        return "BOOK_METADATA", "high", "; ".join(reason)

    # 2) DISTILLERY_CANDIDATE (checked before person/award so 'X Distillery' wins)
    if DIST_SINGULAR_RE.search(elow):
        reason.append("ends with distillery/distillenes (incl. OCR); real distillery name not in DB")
        return "DISTILLERY_CANDIDATE", "high", "; ".join(reason)
    # 3) PERSON (high-confidence name) -- win over loose distillery context
    if PERSON_RE.search(elow) and not CORP_RE.search(elow):
        reason.append("matches known-person name pattern (author/figure)")
        return "PERSON", "high", "; ".join(reason)

    # 4) DISTILLERY_CANDIDATE (loose context, medium)
    if re.search(r"\b(distiller|distillery|malt whisky|grain whisky)\b", ctx) or "distill" in ctx:
        reason.append("occurs in distillery-list context but name not resolved in production.db")
        return "DISTILLERY_CANDIDATE", "medium", "; ".join(reason)

    # 4) AWARD/EVENT (entity itself carries award term)
    if AWARD_RE.search(elow):
        reason.append("entity contains award/event term")
        return "AWARD/EVENT", "high", "; ".join(reason)

    # 5) COMPANY/BRAND
    if CORP_RE.search(elow):
        reason.append("corporate/brand suffix present")
        return "COMPANY/BRAND", "high", "; ".join(reason)

    # 6) WHISKY_PRODUCT_CANDIDATE
    if PRODUCT_HINT.search(ctx) or PRODUCT_HINT.search(elow):
        reason.append("near product/expression terms (bottling/cask/edition/reserve)")
        return "WHISKY_PRODUCT_CANDIDATE", "medium", "; ".join(reason)

    # 7) FALSE_POSITIVE (OCR junk)
    if OCR_JUNK_RE.search(ent) or OCR_JUNK_RE.search(ctx):
        reason.append("OCR artifact / garbled token")
        return "FALSE_POSITIVE", "low", "; ".join(reason)

    # 8) GENERIC_TERM (geographic / descriptive phrases)
    if elow.startswith(("in ", "all ", "the ")) or re.search(r"\b(scotch|irish|canadian|american|kentucky|tennessee|speyside|islay|japan|india|ireland|canada|scotland|usa|england|wales|nova scotia)\b", elow):
        reason.append("geographic/descriptive phrase, not a specific entity")
        return "GENERIC_TERM", "medium", "; ".join(reason)

    # 9) UNKNOWN fallback
    reason.append("no rule matched; needs manual review")
    return "UNKNOWN", "low", "; ".join(reason)


def main():
    rows = []
    with open(IN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    cats = Counter()
    conf = Counter()
    out = []
    for r in rows:
        c, cf, why = classify(r)
        rec = dict(r)  # preserve original text, source page, context
        rec["classification"] = c
        rec["confidence"] = cf
        rec["classification_reason"] = why
        out.append(rec)
        cats[c] += 1
        conf[cf] += 1

    with open(CLS, "w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # resolver impact / noise reduction estimate
    legit = cats["DISTILLERY_CANDIDATE"] + cats["WHISKY_PRODUCT_CANDIDATE"] + cats["COMPANY/BRAND"] + cats["PERSON"]
    noise = cats["BOOK_METADATA"] + cats["FALSE_POSITIVE"] + cats["GENERIC_TERM"]
    review = cats["UNKNOWN"] + cats["AWARD/EVENT"]
    total = len(out)

    report = f"""# B4b Candidate Classification Report

**Input:** `unresolved_entities.jsonl` ({total} rows)
**Method:** deterministic rule-based classifier (LLM-free, staging-only). No DB mutation.
**Output:** `candidate_classification.jsonl` (preserves original text/page/context + adds classification/confidence/reason).

## Category counts
"""
    for c in ["DISTILLERY_CANDIDATE", "WHISKY_PRODUCT_CANDIDATE", "COMPANY/BRAND", "PERSON",
              "AWARD/EVENT", "BOOK_METADATA", "GENERIC_TERM", "FALSE_POSITIVE", "UNKNOWN"]:
        report += f"- {c}: {cats.get(c,0)}\n"
    report += f"""
## Confidence split
- high: {conf.get('high',0)}
- medium: {conf.get('medium',0)}
- low: {conf.get('low',0)}

## Resolver impact
- **Legit entity leads (real new candidates):** {legit}
  - DISTILLERY_CANDIDATE + WHISKY_PRODUCT_CANDIDATE + COMPANY/BRAND are genuine net-new leads for the
    resolver to match/insert via staging (NOT noise).
- **Noise to suppress (route out of review queue):** {noise}
  - BOOK_METADATA (chapter/section headings) + FALSE_POSITIVE (OCR) + GENERIC_TERM (geographic phrases)
    should be auto-demoted so they never reach manual review.
- **Manual review bucket:** {review} (UNKNOWN + AWARD/EVENT) — keep in queue.

## Expected reduction in noise
- Current unresolved queue: {total}
- After routing BOOK_METADATA+FALSE_POSITIVE+GENERIC_TERM to auto-suppress:
  **{total - noise} remain** ({100*(total-noise)//total}% of original) → **noise cut by {noise} rows (~{100*noise//total}%)**.
- The resolver redesign should: (1) skip headings/metadata, (2) OCR-normalize before matching,
  (3) treat "*Distillery"/"*Distillenes" as high-confidence distillery leads.

## Caveats
- Classification is heuristic (rule precedence); spot-check before acting. PERSON may over-capture
  common given-names; DISTILLERY_CANDIDATE medium-confidence may include false leads.
- Nothing promoted; staging only.
"""
    with open(REP, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"total={total} cats={dict(cats)}")
    print(f"noise(auto-suppress)={noise} remain={total-noise} reduction={100*noise//total}%")


if __name__ == "__main__":
    main()
