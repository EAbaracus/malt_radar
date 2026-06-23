from pathlib import Path
import fitz

INPUT_DIR = Path("data/manual_sources/books/input")
OUT_DIR = Path("data/manual_sources/books/raw_text")
OUT_DIR.mkdir(parents=True, exist_ok=True)

pdfs = list(INPUT_DIR.glob("*.pdf"))

if not pdfs:
    print(f"NO PDF FILES FOUND in {INPUT_DIR}")
    raise SystemExit(0)

for src in pdfs:
    out = OUT_DIR / f"{src.stem}.txt"
    doc = fitz.open(src)

    parts = []
    for page_no, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            parts.append(f"\n\n--- PAGE {page_no} ---\n{text}")

    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"WROTE {out}")
