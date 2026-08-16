"""B3/B4: serve-time isim casing normalizasyonu — TDD testleri.

B1 teşhisi: production'da `name` KANONİK Title Case, `original_name` HAM
küçük ikiz; 147 satırda `name` de küçük harfle başlıyor. Bu modül,
`title_case_name` (title-case + MEŞRU brand istisnaları) ve
`DbReadService._prepare_whisky` entegrasyonunu test eder.

B4: production verisinden, resmi yazımı web-doğrulanmış marka/ürün istisnaları
(ImpEx, WhistlePig, anCnoc, GlenDronach, ...), possessive "'s" deseni ve
yaş-kısaltması ("18yo") sabitlenir.
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


@pytest.mark.parametrize("raw,expected", [
    # B4 — resmi yazımı doğrulanmış marka/ürün istisnaları (kelime-bazlı).
    ("the impex collection benrinnes 2008 16 year old",
     "The ImpEx Collection Benrinnes 2008 16 Year Old"),
    ("whistlepig 10 year old small batch bourbon",
     "WhistlePig 10 Year Old Small Batch Bourbon"),
    ("ancnoc 12", "anCnoc 12"),
    ("glendronach port wood", "GlenDronach Port Wood"),
    ("glenallachie 8 - from the valley of the rocks",
     "GlenAllachie 8 - From The Valley Of The Rocks"),
    ("kinglassie 8 year old double matured", "KinGlassie 8 Year Old Double Matured"),
    ("sirdavis sherry cask finished", "SirDavis Sherry Cask Finished"),
    ("santan spirits butcher jones arizona straight",
     "SanTan Spirits Butcher Jones Arizona Straight"),
    ("deleón reposado", "DeLeón Reposado"),
    ("milhòc première flamme single grain", "MilHòc Première Flamme Single Grain"),
    ("copperworks peatsmith single malt", "Copperworks PeatSmith Single Malt"),
    ("copperworks farmsmith single origin washington barley (2024 release)",
     "Copperworks FarmSmith Single Origin Washington Barley (2024 Release)"),
    ("copperworks maltsmith five malt mashbill", "Copperworks MaltSmith Five Malt Mashbill"),
    ("highglen", "HighGlen"),
    ("balvenie 12 doublewood", "Balvenie 12 DoubleWood"),
    ("caol ila smws 53.207", "Caol Ila SMWS 53.207"),            # akronim
    # Mc/Mac soyadlı markalar — iç büyük harf + possessive 's birlikte korunur.
    ("mcconnell's 5 year old sherry cask finish",
     "McConnell's 5 Year Old Sherry Cask Finish"),
    ("mccarthy's 6 year old oloroso cask finished single malt (2023 release)",
     "McCarthy's 6 Year Old Oloroso Cask Finished Single Malt (2023 Release)"),
    ("macarthur's blended scotch", "MacArthur's Blended Scotch"),
    ("macnair's peated", "MacNair's Peated"),
])
def test_title_case_name_brand_exceptions(raw, expected):
    assert title_case_name(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    # B4 — possessive "'s" deseni: sondaki 's küçük kalır (production'da ~200 isim).
    ("michter's barrel strength rye", "Michter's Barrel Strength Rye"),
    ("michter\u2019s 10yo single barrel bourbon", "Michter\u2019s 10yo Single Barrel Bourbon"),  # curly apostrof korunur
    ("dewar's 12 year old", "Dewar's 12 Year Old"),
    ("jack daniel's rested tennessee rye", "Jack Daniel's Rested Tennessee Rye"),
    ("ichiro's malt chichibu the first", "Ichiro's Malt Chichibu The First"),
    ("glenrothes whisky maker's cut", "Glenrothes Whisky Maker's Cut"),
    ("stranahan\u2019s single malt", "Stranahan\u2019s Single Malt"),
])
def test_title_case_name_possessive(raw, expected):
    assert title_case_name(raw) == expected


def test_title_case_name_age_abbreviation_yo_preserved():
    # B4 — rakam+"yo" yaş kısaltması korunur ("18yo" → "18yo", ASLA "18Yo").
    assert title_case_name("benriach 18yo albariza pedro ximenez peated") == \
        "BenRiach 18yo Albariza Pedro Ximenez Peated"
    assert title_case_name("laphroaig 27yo") == "Laphroaig 27yo"
    # karşıt: "12 year old" title-case olur (yaş kısaltması DEĞİL).
    assert title_case_name("glenfiddich 12 year old") == "Glenfiddich 12 Year Old"


def test_title_case_name_french_elision_dor():
    # apostrof-sonrası büyük harfli elision korunur (possessive DEĞİL).
    assert title_case_name("glenmorangie nectar d'or") == "Glenmorangie Nectar D'Or"


def test_title_case_name_idempotent_on_canonical():
    # İkinci geçiş değiştirmemeli (idempotency — B1: canonical name bozulmamalı).
    for raw in [
        "Aberlour A'Bunadh (Batch 33)",
        "BenRiach 18yo Albariza Pedro Ximenez Peated",
        "The Macallan 18 Sherry Oak",
        "The ImpEx Collection Benrinnes 2008 16 Year Old",
        "WhistlePig 10 Year Old Small Batch Bourbon",
        "anCnoc 12",
        "GlenDronach Port Wood",
        "MilHòc Première Flamme Single Grain",
        "Caol Ila SMWS 53.207",
        "McConnell's 5 Year Old Sherry Cask Finish",
        "Michter's Barrel Strength Rye",
        "Glenmorangie Nectar D'Or",
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
