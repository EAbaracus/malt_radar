"""Generator orkestrasyon testleri — sentetik DB, determinizm, read-only."""
import hashlib, sqlite3, tempfile
from pathlib import Path
from seo.generator import generate, db_sha256, _assert_readonly


def _seed_db(path: Path):
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE whiskies (whisky_id TEXT, name TEXT, distillery_id TEXT,
          region TEXT, country TEXT, type TEXT, age INTEGER,
          brand TEXT, meta_critic_score REAL);
        CREATE TABLE flavor_profiles (whisky_id TEXT, flavor_profile TEXT,
          production_price REAL);
        CREATE TABLE flavor_evidence (whisky_id TEXT, original_tasting_note TEXT);
        CREATE TABLE distilleries (distillery_id TEXT, name TEXT);
        INSERT INTO whiskies VALUES
          ('W1','Test Whisky A','D1','Speyside','Scotland','Single Malt',12,'BrandX',87.0),
          ('W2','Test Whisky B','D1','Speyside','Scotland','Single Malt',NULL,'BrandX',NULL),
          ('W3','Test Whisky C',NULL,NULL,NULL,NULL,NULL,NULL,NULL);
        INSERT INTO flavor_profiles VALUES
          ('W1','{"fruity":0.8,"sweet":0.6}',99.9),
          ('W2','{"fruity":0.5}',NULL);
        INSERT INTO flavor_evidence VALUES ('W1','Armut, vanilya, meşe');
        INSERT INTO distilleries VALUES ('D1','Test Distillery');
    """)
    c.commit(); c.close()


def test_generate_deterministic_and_no_price():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        o1 = Path(td) / "o1"; o2 = Path(td) / "o2"
        r1 = generate(str(db), str(o1), build_date="2026-08-10")
        r2 = generate(str(db), str(o2), build_date="2026-08-10")
        h1 = hashlib.sha256(b"".join(sorted(p.read_bytes() for p in o1.rglob("*") if p.is_file()))).hexdigest()
        h2 = hashlib.sha256(b"".join(sorted(p.read_bytes() for p in o2.rglob("*") if p.is_file()))).hexdigest()
        assert h1 == h2
        assert r1["pages"] == r2["pages"] > 0
        for out in (o1, o2):
            for p in out.rglob("*.html"):
                assert "99.9" not in p.read_text(encoding="utf-8")  # fiyat sızıntısı YOK
        assert r1["tiers"] == {"W1": "A", "W2": "B", "W3": "C_no"}
        sm = (o1 / "sitemap.xml").read_text(encoding="utf-8")
        assert sm.count("<url>") == r1["sitemap_urls"]


def test_c_no_pages_excluded_from_sitemap():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        out = Path(td) / "o"
        r = generate(str(db), str(out), build_date="2026-08-10")
        sm = (out / "sitemap.xml").read_text(encoding="utf-8")
        assert "/w/W3/" not in sm          # C_no sayfası sitemap'te YOK
        assert r["pages"] > r["sitemap_urls"]
        for lang in ("tr", "en"):
            p = out / lang / "w" / "W3" / "index.html"
            assert p.exists()
            assert "noindex, follow" in p.read_text(encoding="utf-8")


def test_readonly_assertion():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        _assert_readonly(conn)
        conn.close()


def test_db_sha256_stable():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"; _seed_db(db)
        assert db_sha256(str(db)) == db_sha256(str(db))