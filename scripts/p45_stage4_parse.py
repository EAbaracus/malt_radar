#!/usr/bin/env python
"""
P45 PHASE 4 — SMWS-specific PARSER
Reads:  output/import/smws/smws_raw_records.jsonl
Writes: output/import/smws/staging_smws_tasting_notes.csv
         output/import/smws/_parse_issues.jsonl  (diagnostics, not used by import)

Schema (staging_smws_tasting_notes):
  id, source, file_name, cask_no, distillery, product_name, age, abv, region,
  cask_type, flavour_profile, tasting_notes_raw, extraction_confidence, review_status

All rows: review_status = 'pending_review'. No production mutation.

NOTE on distillery: SMWS encodes the distillery in the cask-number PREFIX.
The code->distillery mapping below is the well-known PUBLIC SMWS reference table.
It is provided as an *inference aid* only; every inferred distillery MUST be verified
by a human reviewer (review_status=pending_review). If the code is unknown or the
distillery appears explicitly in the text, text wins.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
IN = ROOT / "output/import/smws/smws_raw_records.jsonl"
OUT = ROOT / "output/import/smws/staging_smws_tasting_notes.csv"
ISSUES = ROOT / "output/import/smws/_parse_issues.jsonl"

# ---- Public SMWS code -> distillery reference (inference aid ONLY) ----
# Only CONFIDENT, widely-documented public SMWS code mappings are asserted.
# Codes that are disputed / not publicly documented are intentionally OMITTED so
# the pipeline never fabricates a distillery. Omitted codes stay empty and are
# flagged for human review (review_status = pending_review).
SMWS_CODE_DISTILLERY = {
    "1": "Glenfarclas", "2": "The Glenlivet", "3": "Bowmore", "4": "Highland Park",
    "5": "Aberlour", "6": "Tullibardine", "7": "Longmorn", "8": "Aberfeldy",
    "9": "Loch Lomond", "10": "Ben Nevis", "12": "Benriach", "13": "Caperdonich",
    "14": "Talisker", "15": "Glen Grant", "16": "Glen Spey", "17": "Scapa",
    "18": "Inchgower", "19": "Glenrothes", "21": "Macallan", "22": "Glendullan",
    "23": "Bruichladdich", "24": "Macduff", "25": "Benrinnes", "26": "Clynelish",
    "27": "Springbank", "28": "Glenburgie", "29": "Coleburn", "37": "Cragganmore",
    "38": "Strathisla", "39": "Strathmill", "41": "Dailuaine", "42": "Cardhu",
    "43": "Mannochmore", "44": "Royal Brackla", "49": "Rosebank", "53": "Caol Ila",
    "54": "Teaninich", "55": "Royal Lochnagar", "58": "Bladnoch", "106": "Glenturret",
    "107": "Laphroaig", "108": "Bunnahabhain", "110": "Ardbeg", "118": "Kilchoman",
    "103": "Lagavulin", "83": "Kilchoman", "G1": "Cameronbridge",
}

def normalize_cask(s):
    """SMWS cask codes have no leading zeros: '001.139' -> '1.139'; '094 3' -> '94.3'.
    'G' prefix (grain series) is preserved: 'G1.10' stays 'G1.10'."""
    if not s:
        return ""
    s = s.strip()
    gm = re.match(r"^([Gg])(\d{1,4})\.?(\d{0,4})$", s)
    if gm:
        prefix = "G" + str(int(gm.group(2)))
        if gm.group(3):
            return f"{prefix}.{int(gm.group(3))}"
        return prefix
    s = s.replace(" ", ".")
    m = re.match(r"^(\d{1,4})\.(\d{1,4})$", s)
    if not m:
        return s
    return f"{int(m.group(1))}.{int(m.group(2))}"

CASK_RE = re.compile(r"CASK\s*(?:No\.?|#)\s*([Gg]?\d{1,4}(?:\.\d{1,4})?)", re.IGNORECASE)
FNAME_CASK_RE = re.compile(r"^([Gg]?\d{1,4})[ .](\d{1,4})")
ABV_RE = re.compile(r"(\d{2,3}\.\d{1,2})\s*%", re.IGNORECASE)
AGE_RE = re.compile(r"(\d{1,3})\s*(?:YEARS|YEAR|YO\b)", re.IGNORECASE)
AGE_RE2 = re.compile(r"Age:\s*(\d{1,3})\s*years", re.IGNORECASE)
REGION_RE = re.compile(r"Region:\s*([A-Za-z/ ]+?)\s*(?:/|District|$)", re.IGNORECASE)
REGION_LINE_RE = re.compile(r"\b(SPEYSIDE SPEY|SPEYSIDE|ISLAY|HIGHLAND|LOWLAND|CAMPBELTOWN|ISLANDS)\b")
CASKTYPE_RE = re.compile(r"(?:Cask:\s*|Colour[^\n]*?)(REFILL|FIR?ST[\s-]?FILL|SHERRY|PORT|WINE|BOURBON|OLO?ROSO|AMONTILLADO|PEDRO XIMENEZ|PX|MADEIRA|VIRGIN|NEW\b)[^\n]*?(HOGSHEAD|BARREL|BUTT|Barrique|PIPE|PUNCHEON|GORDON?|CASK)", re.IGNORECASE)
CASKTYPE_RE2 = re.compile(r"\b(REFILL HOGSHEAD|REFILL BARREL|REFILL BUTT|FIRST[\s-]?FILL [A-Z ]+|SHERRY BUTT|OLO?ROSO [A-Z ]+|PX [A-Z ]+)\b", re.IGNORECASE)
FLAVOUR_CAT_RE = re.compile(r"\b(SPICY|SWEET|DRY|SMOKY|FRUITY|MALTLY|WOODY|LIGHT|OILY|WINEY|DELICATE|BODY|YOUNG|OLD|FRESH|RICH|DEEP|QUICK)[ \-]*(?:&[ \-]*(SPICY|SWEET|DRY|SMOKY|FRUITY|MALTLY|WOODY|LIGHT|OILY|WINEY|DELICATE|BODY|YOUNG|OLD|FRESH|RICH|DEEP|QUICK))?\b")
DRINKING_TIP_RE = re.compile(r"Drinking Tip:.*$", re.IGNORECASE | re.DOTALL)
COLOUR_RE = re.compile(r"Colour[^\n]*$", re.MULTILINE | re.IGNORECASE)
DISTILLERY_EXPLICIT_RE = re.compile(r"\b(Islay,\s*[A-Za-z ]+?|Lochindaal|Bowmore|Bruichladdich|Lagavulin|Laphroaig|Ardbeg|Kilchoman|Bunnahabhain|Caol Ila|Clynelish|Springbank|Glenfarclas|Glenlivet|Highland Park|Talisker|Arran|Ailsa Bay|Tobermory|Ledaig|Blair Athol|Ben Nevis|Benrinnes|Benriach|Glenrothes|Glen? [A-Za-z]+)\b")

def first_or_none(x):
    return x[0] if x else None

def parse_record(rec):
    raw = rec.get("raw_text", "")
    file_name = rec.get("file_name", "")
    method = rec.get("extraction_method", "")
    cask = first_or_none(CASK_RE.findall(raw))
    if not cask:
        fm = FNAME_CASK_RE.match(file_name)
        if fm:
            cask = f"{fm.group(1)}.{fm.group(2)}"
    cask = normalize_cask(cask)
    abvs = ABV_RE.findall(raw)
    abv = abvs[-1] if abvs else None
    age = first_or_none(AGE_RE.findall(raw)) or first_or_none(AGE_RE2.findall(raw))
    region = None
    m = REGION_RE.search(raw)
    if m:
        region = m.group(1).strip().title()
    else:
        rl = REGION_LINE_RE.search(raw.upper())
        if rl:
            region = rl.group(1).title()
    # cask_type
    ct = None
    m2 = CASKTYPE_RE2.search(raw)
    if m2:
        ct = m2.group(1).strip().title()
    else:
        m3 = CASKTYPE_RE.search(raw)
        if m3:
            ct = m3.group(0).strip().title()
    # flavour profile category
    # T2 templates use letter-spaced headers: "S P I C Y & S W E E T"
    # Compact them so the regex can match: remove inter-letter whitespace
    fp = None
    compact_raw = re.sub(r'(?<=[A-Z])\s(?=[A-Z])', '', raw)
    fm = FLAVOUR_CAT_RE.search(raw) or FLAVOUR_CAT_RE.search(compact_raw)
    if fm:
        fp = fm.group(0).strip().title()
    # product_name (title) — heuristic: explicit distillery line, else a short title-ish line
    product_name = ""
    dm = DISTILLERY_EXPLICIT_RE.search(raw)
    explicit_dist = dm.group(1).strip() if dm else None
    # distillery resolution
    distillery = None
    if explicit_dist:
        # normalize "Islay, Lochindaal" -> Lochindaal
        if "," in explicit_dist:
            distillery = explicit_dist.split(",")[-1].strip()
        else:
            distillery = explicit_dist
    if not distillery and cask:
        prefix = cask.split(".")[0]
        inferred = SMWS_CODE_DISTILLERY.get(prefix)
        if inferred:
            distillery = inferred
    # tasting notes raw: strip meta lines (cask header, age/abv/region footer, casktype/colour, drinking tip)
    notes = raw
    notes = DRINKING_TIP_RE.sub("", notes)
    notes = COLOUR_RE.sub("", notes)
    # remove the CASK No line and the flavour category header line and region/distillery header
    notes = re.sub(r"CASK\s*(?:No\.?|#)\s*[0-9.]+\s*", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Region:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"District:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Colour[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Cask:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Age:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Alcohol:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Date distilled:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Dist:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Alc\.?:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"Proof:\s*[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"\d{1,3}\s*YEARS[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"\d{2,3}\.\d{1,2}\s*%[^\n]*\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"REFILL [A-Z ]+\n?", "", notes, flags=re.IGNORECASE)
    notes = re.sub(r"THE SCOTCH MALT WHISKY SOCIETY\s*", "", notes, flags=re.IGNORECASE)
    # collapse whitespace
    notes = re.sub(r"[ \t]+", " ", notes)
    notes = re.sub(r"\n{2,}", "\n", notes).strip()
    # product_name heuristic: pick the most title-like surviving line
    if not product_name:
        cand = [ln.strip(" \"'") for ln in notes.split("\n") if ln.strip()]
        # prefer a line that is short and not a sentence (no terminal period, has capitals)
        for ln in cand[:6]:
            if 3 <= len(ln) <= 60 and not ln.endswith(".") and ln[0:1].isupper():
                product_name = ln
                break
        if not product_name and cand:
            product_name = cand[0][:60]
    # extraction confidence
    conf = 0.0
    if method == "pdf_text":
        conf = 0.5
        if cask: conf += 0.2
        if abv: conf += 0.1
        if age: conf += 0.1
        if region: conf += 0.05
        if ct: conf += 0.05
    else:
        conf = 0.1  # OCR needed
    conf = min(conf, 1.0)
    return {
        "source": "SMWS USA",
        "file_name": file_name,
        "cask_no": cask or "",
        "distillery": distillery or "",
        "product_name": product_name or "",
        "age": age or "",
        "abv": abv or "",
        "region": region or "",
        "cask_type": ct or "",
        "flavour_profile": fp or "",
        "tasting_notes_raw": notes,
        "extraction_confidence": round(conf, 2),
        "review_status": "pending_review",
    }

def main():
    if not IN.exists():
        raise SystemExit("missing input; run stage1 first")
    rows = []
    issues = []
    with open(IN, encoding="utf-8") as f:
        for ln in f:
            rec = json.loads(ln)
            if rec.get("extraction_method") == "failed":
                issues.append({"file_name": rec["file_name"], "issue": "extraction_failed"})
                continue
            if rec.get("extraction_method") == "ocr":
                issues.append({"file_name": rec["file_name"], "issue": "needs_ocr"})
            parsed = parse_record(rec)
            rows.append(parsed)
            if not parsed["cask_no"]:
                issues.append({"file_name": rec["file_name"], "issue": "no_cask_no"})

    cols = ["id", "source", "file_name", "cask_no", "distillery", "product_name",
            "age", "abv", "region", "cask_type", "flavour_profile",
            "tasting_notes_raw", "extraction_confidence", "review_status"]
    with open(OUT, "w", newline="", encoding="utf-8") as cf:
        w = csv.DictWriter(cf, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            r2 = {"id": i, **r}
            w.writerow(r2)
    with open(ISSUES, "w", encoding="utf-8") as f:
        for it in issues:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"[phase4] wrote {len(rows)} staging rows; {len(issues)} issues", flush=True)
    # quick field coverage
    cov = {k: sum(1 for r in rows if str(r.get(k, "")).strip()) for k in
           ["cask_no", "distillery", "product_name", "age", "abv", "region", "cask_type", "flavour_profile", "tasting_notes_raw"]}
    print("[phase4] coverage:", json.dumps(cov), flush=True)

if __name__ == "__main__":
    main()
