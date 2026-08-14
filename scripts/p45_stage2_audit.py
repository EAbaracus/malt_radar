#!/usr/bin/env python
"""
P45 PHASE 2 — EXTRACTION AUDIT
Reads:  output/import/smws/smws_pages.jsonl        (per-page text)
        output/import/smws/smws_raw_records.jsonl  (per-doc text)
        source PDFs (pypdf for image-layer detection)
Writes: output/reports/smws_usa_pdf_manifest.csv   (REFINED: corrected pdf_type)
        output/reports/smws_usa_extraction_quality.md

Purpose: understand PDF structure, OCR need, template variance, field coverage,
duplicate cask detection. Read-only on sources.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

import pypdf

ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
SRC = ROOT / "data/books/SMWS USA TASTING NOTES ARCHIVE"
PAGES = ROOT / "output/import/smws/smws_pages.jsonl"
RAW = ROOT / "output/import/smws/smws_raw_records.jsonl"
MANIFEST = ROOT / "output/reports/smws_usa_pdf_manifest.csv"
QUALITY = ROOT / "output/reports/smws_usa_extraction_quality.md"

CASK_RE = re.compile(r"CASK\s*(?:No\.?|#)\s*([Gg]?\d{1,4}(?:\.\d{1,4})?)", re.IGNORECASE)
FNAME_CASK_RE = re.compile(r"^([Gg]?\d{1,4})[ .](\d{1,4})")

def page_has_image(path: Path, idx: int) -> bool:
    try:
        reader = pypdf.PdfReader(str(path))
        if idx < 0 or idx >= len(reader.pages):
            return False
        page = reader.pages[idx]
        try:
            imgs = list(page.images)
            return len(imgs) > 0
        except Exception:
            # fallback: inspect resources
            res = page.get("/Resources")
            if res is not None and "/XObject" in res:
                xo = res["/XObject"].get_object()
                for obj in xo.values():
                    o = obj.get_object()
                    if o.get("/Subtype") == "/Image":
                        return True
            return False
    except Exception:
        return False

def main():
    # load per-page text keyed by (file_name, page_number)
    page_text = {}
    per_doc_pages = {}
    with open(PAGES, encoding="utf-8") as f:
        for ln in f:
            o = json.loads(ln)
            fn = o["file_name"]
            per_doc_pages.setdefault(fn, 0)
            if o["extraction_method"] != "failed":
                per_doc_pages[fn] += 1
            txt = o.get("raw_text", "")
            page_text[(fn, o["page_number"])] = txt

    # load per-doc raw
    docs = {}
    with open(RAW, encoding="utf-8") as f:
        for ln in f:
            o = json.loads(ln)
            docs[o["file_name"]] = o

    refined = []
    n_text = n_scanned = n_mixed = n_error = 0
    template_counter = Counter()
    field_cov = Counter()
    cask_to_files = {}

    all_files = sorted(docs.keys(), key=str.lower)
    for fn in all_files:
        rec = docs[fn]
        raw = rec.get("raw_text", "")
        npages = per_doc_pages.get(fn, 0)
        method = rec.get("extraction_method", "")
        has_text_layer = bool(raw.strip())
        # image presence per page (sample up to npages)
        has_image = False
        if method != "failed":
            for i in range(npages):
                if page_has_image(SRC / fn, i):
                    has_image = True
                    break
        # classification
        if method == "failed" or not raw.strip():
            ptype = "scanned"  # needs OCR
            n_scanned += 1
        elif has_image:
            ptype = "mixed"
            n_mixed += 1
        else:
            ptype = "text"
            n_text += 1

        # cask detection (body + filename fallback, normalized)
        # NOTE: regex mirrors Phase 4's CASK_RE — must capture G-prefix for grain series
        cm = re.search(r"CASK\s*(?:No\.?|#)\s*([Gg]?\d{1,4}(?:\.\d{1,4})?)", raw, re.IGNORECASE)
        if cm:
            cask = cm.group(1)
            gm = re.match(r"^([Gg])?0*(\d{1,4})(?:\.0*(\d{1,4}))?$", cask)
            if gm:
                if gm.group(1):
                    pref = "G" + str(int(gm.group(2)))
                    cask = pref + ("." + str(int(gm.group(3))) if gm.group(3) else "")
                else:
                    cask = str(int(gm.group(2))) + ("." + str(int(gm.group(3))) if gm.group(3) else "")
        else:
            fm = FNAME_CASK_RE.match(fn)
            if fm:
                cask = f"{int(fm.group(1))}.{int(fm.group(2))}" if not fm.group(1).lower().startswith('g') else f"G{int(fm.group(1)[1:])}.{int(fm.group(2))}"
        if cask:
            cask_to_files.setdefault(cask, []).append(fn)
            field_cov["cask_no"] += 1

        # template detection
        up = raw.upper()
        if "THE SCOTCH MALT WHISKY SOCIETY" in up and "PROOF:" in up:
            tmpl = "T1_classic"
        elif re.search(r"SPICY|SWEET|DRY|SMOKY", up) and "REFILL" in up:
            tmpl = "T2_modern_category"
        elif "ISLAY" in up or ("COLOUR:" in up and "DATE DISTILLED" in up):
            tmpl = "T3_islay_block"
        elif "DIST:" in up and "ALC.:" in up:
            tmpl = "T4_essay"
        else:
            tmpl = "T0_unknown"
        template_counter[tmpl] += 1

        # field coverage
        if re.search(r"(\d{2,3}\.\d{1,2})\s*%", raw): field_cov["abv"] += 1
        if re.search(r"(\d{1,3})\s*(?:YEARS|YEAR|YO\b)", raw, re.IGNORECASE): field_cov["age"] += 1
        if re.search(r"\b(SPEYSIDE|HIGHLAND|ISLAY|LOWLAND|CAMPBELTOWN|ISLANDS|SPEYSIDE SPEY)\b", up): field_cov["region"] += 1
        if re.search(r"REFILL|FIR?ST[\s-]?FILL|SHERRY|BUTT|HOGSHEAD|BARREL", up): field_cov["cask_type"] += 1
        if re.search(r"SPICY|SWEET|DRY|SMOKY|FRUITY|MALTLY|WOODY|LIGHT|OILY", up): field_cov["flavour_profile"] += 1
        if raw.strip(): field_cov["tasting_notes"] += 1

        refined.append({
            "file_name": fn, "pages": npages, "pdf_type": ptype,
            "extraction_method": method, "template": tmpl, "cask_no": cask,
        })

    # duplicate cask detection
    dup_casks = {c: fs for c, fs in cask_to_files.items() if len(fs) > 1}

    # write refined manifest (preserve original columns, add template)
    orig_rows = []
    with open(MANIFEST, encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            orig_rows.append(r)
    by_fn = {r["file_name"]: r for r in orig_rows}
    cols = ["file_name", "relative_path", "size_bytes", "sha256", "pages",
            "pdf_type", "text_ratio", "cask_no", "abv", "age", "region",
            "extraction_ok", "error", "template"]
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in refined:
            base = by_fn.get(r["file_name"], {})
            w.writerow({
                "file_name": r["file_name"],
                "relative_path": base.get("relative_path", ""),
                "size_bytes": base.get("size_bytes", ""),
                "sha256": base.get("sha256", ""),
                "pages": r["pages"],
                "pdf_type": r["pdf_type"],
                "text_ratio": base.get("text_ratio", ""),
                "cask_no": r["cask_no"],
                "abv": base.get("abv", ""),
                "age": base.get("age", ""),
                "region": base.get("region", ""),
                "extraction_ok": base.get("extraction_ok", "true"),
                "error": base.get("error", ""),
                "template": r["template"],
            })

    total = len(all_files)
    # -------- write extraction_quality.md --------
    md = []
    md.append("# SMWS USA — Extraction Quality Audit (PHASE 2)\n")
    md.append(f"Source: `data/books/SMWS USA TASTING NOTES ARCHIVE`  ")
    md.append(f"Total PDFs: **{total}**\n")
    md.append("## 1. PDF type classification\n")
    md.append(f"| Type | Count | Needs OCR |")
    md.append(f"|------|-------|-----------|")
    md.append(f"| text (full text layer) | {n_text} | no |")
    md.append(f"| mixed (text + image layer) | {n_mixed} | partial/verify |")
    md.append(f"| scanned (image only) | {n_scanned} | **YES** |")
    md.append(f"| error | {n_error} | retry |\n")
    ocr_list = [r["file_name"] for r in refined if r["pdf_type"] == "scanned"]
    md.append(f"**OCR-required ({len(ocr_list)}):** " + (", ".join(ocr_list[:40]) or "none") +
              (f" … (+{len(ocr_list)-40} more)" if len(ocr_list) > 40 else "") + "\n")
    md.append("\n## 2. Template variance\n")
    md.append("Detected SMWS layout templates (heuristic):\n")
    md.append("| Template | Count | Notes |")
    md.append("|----------|-------|-------|")
    notes = {
        "T1_classic": "Society header + Dist/Alc/Proof footer",
        "T2_modern_category": "Flavour category line + REFILL footer",
        "T3_islay_block": "Islay/region block + Colour/Cask/Age/Alcohol fields",
        "T4_essay": "Essay style, Dist/Alc footer, no top cask line",
        "T0_unknown": "No recognised template — manual review",
    }
    for t, c in template_counter.most_common():
        md.append(f"| {t} | {c} | {notes.get(t,'')} |")
    md.append("\n## 3. Field extraction coverage\n")
    md.append("(count of docs where field signature found in extracted text)\n")
    md.append("| Field | Docs with signal | Coverage % |")
    md.append("|-------|------------------|------------|")
    for fld in ["cask_no", "tasting_notes", "flavour_profile", "age", "abv", "region", "cask_type"]:
        c = field_cov.get(fld, 0)
        md.append(f"| {fld} | {c} | {100*c/total:.1f}% |")
    md.append("\n## 4. Cask-number pattern\n")
    md.append("Pattern `\\d{{1,3}}\\.\\d{{1,4}}` (SMWS cask code). Detected in body or "
              "filename for **{} / {}** docs.\n".format(field_cov.get("cask_no",0), total))
    md.append("\n## 5. Duplicate cask candidates\n")
    if dup_casks:
        md.append(f"{len(dup_casks)} cask code(s) appear in more than one file:\n")
        md.append("| Cask | Files |")
        md.append("|------|-------|")
        for c, fs in sorted(dup_casks.items()):
            md.append(f"| {c} | {', '.join(fs)} |")
    else:
        md.append("No duplicate cask codes detected.\n")
    md.append("\n## 6. Recommendations\n")
    md.append(f"- {len(ocr_list)} PDF(s) require OCR before parsing (image-only).")
    md.append("- Text-layer PDFs parse reliably via `pdftotext -layout`.")
    md.append("- Use filename as cask fallback for docs without an in-body CASK line.")
    md.append("- Distillery must be inferred from the SMWS cask-code prefix and flagged "
              "for human verification (public code→distillery table is inference aid only).")
    md.append("- All parsed rows carry `review_status = pending_review`; no production write.\n")

    with open(QUALITY, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"[phase2] text={n_text} mixed={n_mixed} scanned={n_scanned} error={n_error}", flush=True)
    print(f"[phase2] templates={dict(template_counter)}", flush=True)
    print(f"[phase2] duplicate casks={len(dup_casks)}", flush=True)

if __name__ == "__main__":
    main()
