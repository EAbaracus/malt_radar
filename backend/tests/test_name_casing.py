"""B3: serve-time isim casing normalizasyonu — TDD testleri.

B1 teşhisi: production'da `name` KANONİK Title Case, `original_name` HAM
küçük ikiz; 147 satırda `name` de küçük harfle başlıyor. Bu modül,
`title_case_name` (title-case + MEŞRU brand istisnaları) ve
`DbReadService._prepare_whisky` entegrasyonunu test eder.
"""
import pytest

from app.services.name_casing import title_case_name


@pytest.mark.parametrize("raw,expected", [
    ("66 gilead crimson rye", "66 Gilead Crimson Rye"),          # sayı-başlı
    ("aberlour a'bunadh (batch 33)", "Aberlour A'Bunadh (Batch 33)"),  # apostrof + parantez
    ("BenRiach 18yo Albariza Pedro Ximenez Peated", "BenRiach 18yo Albariza Pedro Ximenez Peated"),  # MEŞRU brand korunur
    ("Glenfiddich 12 year old", "Glenfiddich 12 Year Old"),
    ("Laphroaig 10 cask strength", "Laphroaig 10 Cask Strength"),
    ("the macallan 18 sherry oak", "The Macallan 18 Sherry Oak"),
    ("8 seconds", "8 Seconds"),
    ("66 Gilead Crimson Rye", "66 Gilead Crimson Rye"),          # zaten doğru — idempotent
])
def test_title_case_name(raw, expected):
    assert title_case_name(raw) == expected


def test_title_case_name_idempotent_on_canonical():
    # İkinci geçiş değiştirmemeli (idempotency — B1: canonical name bozulmamalı).
    for raw in [
        "Aberlour A'Bunadh (Batch 33)",
        "BenRiach 18yo Albariza Pedro Ximenez Peated",
        "The Macallan 18 Sherry Oak",
    ]:
        assert title_case_name(title_case_name(raw)) == title_case_name(raw)


def test_whisky_mapper_uses_canonical_name():
    """_prepare_whisky çıktısında name KANONİK olmalı (original_name tercihi zararsız)."""
    from app.services.db_read_service import DbReadService
    svc = DbReadService()
    with svc._get_connection() as conn:
        cursor = conn.cursor()
        # B1 lowercase-name satırı (original_name NULL) — production'da ham
        # küçük biçimde durur; serve-time düzeltilmeli.
        cursor.execute(
            "SELECT w.whisky_id, w.name, w.original_name FROM whiskies w "
            "WHERE w.name LIKE 'aberlour%' AND w.original_name IS NULL LIMIT 1"
        )
        raw = cursor.fetchone()
    assert raw, "test verisi bekleniyor (lowercase-name + NULL original_name)"
    row = dict(raw)
    assert row["name"] != title_case_name(row["name"]), (
        "test verisi lowercase olmalı; production name zaten kanonikse test anlamsız"
    )
    prepared = svc._prepare_whisky(row)
    assert prepared["name"] == title_case_name(row["name"])
    assert prepared["name"] == "Aberlour A'Bunadh (Batch 33)"
