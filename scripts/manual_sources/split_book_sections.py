from pathlib import Path
import re
import json
from ftfy import fix_text

RAW_DIR = Path("data/manual_sources/books/raw_text")
OUT_DIR = Path("data/manual_sources/books/chunks")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_DISTILLERIES = [
    "Ardbeg", "Laphroaig", "Lagavulin", "Talisker", "Highland Park",
    "Macallan", "Balvenie", "Dalmore", "Springbank", "Benromach",
    "Bunnahabhain", "Caol Ila", "Glenfarclas", "Glenfiddich",
    "Glenlivet", "Oban", "Glenmorangie", "Clynelish", "Cragganmore",
    "Aberlour"
]

QUALITY_TERMS = [
    "nose", "palate", "finish", "tasting", "flavour", "flavor",
    "aroma", "body", "mouthfeel", "aftertaste",
    "peat", "peated", "smoke", "smoky", "smokiness",
    "sherry", "bourbon", "cask", "oak", "matured",
    "sweet", "spice", "spicy", "fruit", "fruity",
    "floral", "maritime", "salt", "seaweed",
    "honey", "malt", "malty", "oil", "oily", "wax", "waxy"
]

LOW_VALUE_TERMS = [
    "contents", "index", "copyright", "all rights reserved",
    "introduction", "auction", "investment", "collecting whisky",
    "recommended references", "glossary"
]

def clean(s: str) -> str:
    s = fix_text(s)
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{4,}", "\n\n", s)
    return s.strip()

def score_chunk(chunk: str, target: str) -> int:
    low = chunk.lower()
    score = 0

    score += low.count(target.lower()) * 10

    for term in QUALITY_TERMS:
        if term in low:
            score += 5

    for term in LOW_VALUE_TERMS:
        if term in low:
            score -= 30

    if re.search(r"\b\d{1,2}\s*(yo|year|years|yr|old)\b", low):
        score += 10

    if re.search(r"\b\d{2}(\.\d)?\s*%\b", low):
        score += 8

    if len(chunk) < 800:
        score -= 20

    if len(chunk) > 9000:
        score -= 10

    return score

def window_around(text: str, keyword: str, radius: int = 2800):
    matches = []
    seen = set()

    for m in re.finditer(re.escape(keyword), text, flags=re.IGNORECASE):
        start = max(0, m.start() - radius)
        end = min(len(text), m.end() + radius)
        chunk = clean(text[start:end])

        # near-duplicate guard
        fingerprint = re.sub(r"\W+", "", chunk[:800].lower())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        matches.append(chunk)

    return matches

txts = list(RAW_DIR.glob("*.txt"))

if not txts:
    print(f"NO RAW TEXT FILES FOUND in {RAW_DIR}")
    raise SystemExit(0)

for txt in txts:
    raw = txt.read_text(encoding="utf-8", errors="ignore")
    text = clean(raw)
    book_name = clean(txt.stem)

    records = []
    for distillery in TARGET_DISTILLERIES:
        chunks = window_around(text, distillery)

        scored = []
        for idx, chunk in enumerate(chunks, start=1):
            score = score_chunk(chunk, distillery)
            if score < 10:
                continue
            scored.append((score, idx, chunk))

        scored.sort(reverse=True, key=lambda x: x[0])

        for rank, (score, idx, chunk) in enumerate(scored[:8], start=1):
            records.append({
                "book_source": book_name,
                "target": distillery,
                "chunk_id": f"{book_name}__{distillery}__{rank}",
                "quality_score": score,
                "text": chunk
            })

    out = OUT_DIR / f"{book_name}_chunks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"WROTE {out} records={len(records)}")
