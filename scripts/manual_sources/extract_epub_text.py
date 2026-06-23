from pathlib import Path
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

INPUT_DIR = Path("data/manual_sources/books/input")
OUT_DIR = Path("data/manual_sources/books/raw_text")
OUT_DIR.mkdir(parents=True, exist_ok=True)

epubs = list(INPUT_DIR.glob("*.epub"))

if not epubs:
    print(f"NO EPUB FILES FOUND in {INPUT_DIR}")
    raise SystemExit(0)

for src in epubs:
    out = OUT_DIR / f"{src.stem}.txt"
    book = epub.read_epub(str(src))

    parts = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text("\n")
            if text.strip():
                parts.append(text)

    out.write_text("\n\n".join(parts), encoding="utf-8")
    print(f"WROTE {out}")
