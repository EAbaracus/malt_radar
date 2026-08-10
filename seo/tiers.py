"""seo/tiers.py — deterministik Tier bölümlemesi (spec §3).

Tek geçişli, tam bölümleme, örtüşme yok. Kural:
  A     = flavor_profile >=2 aktif eksen VE flavor_evidence >=1
  B     = flavor_profile var ama A değil
  C_idx = flavor_profile yok + distillery_id dolu
  C_no  = flavor_profile yok + distillery_id yok  (noindex, sitemap dışı)

Aktif eksen sayısı seo.axes.active_axes ile hesaplanır: ham flavor_profile
(JSON veya key=val) önce canonical→app MAX-map ile 8 app eksenine projekte
edilir (REVİZYON R1 — backend DbReadService._map_canonical_to_app_axes aynası),
sonra >0 olan eksenler sayılır.
"""
from seo.axes import active_axes as _active_axes

def classify(active_axes: int, has_distillery: bool, evidence_count: int) -> str:
    if active_axes >= 2 and evidence_count >= 1:
        return "A"
    if active_axes >= 1:
        return "B"
    return "C_idx" if has_distillery else "C_no"


def tier_map(conn) -> dict:
    """conn: salt-okunur sqlite bağlantısı. whisky_id -> tier sözlüğü."""
    profiles: dict[str, int] = {}
    for wid, fp in conn.execute(
        "SELECT whisky_id, flavor_profile FROM flavor_profiles "
        "WHERE flavor_profile IS NOT NULL AND flavor_profile != '' "
        "AND flavor_profile != '[]'"
    ):
        profiles[wid] = _active_axes(fp)
    tiers: dict[str, str] = {}
    for wid, has_dist in conn.execute(
        "SELECT whisky_id, (distillery_id IS NOT NULL AND distillery_id != '') FROM whiskies"
    ):
        ax = profiles.get(wid, 0)
        if ax >= 2:
            ev = conn.execute(
                "SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id = ?", (wid,)
            ).fetchone()[0]
            tiers[wid] = "A" if ev >= 1 else "B"
        elif ax >= 1:
            tiers[wid] = "B"
        else:
            tiers[wid] = "C_idx" if has_dist else "C_no"
    return tiers
