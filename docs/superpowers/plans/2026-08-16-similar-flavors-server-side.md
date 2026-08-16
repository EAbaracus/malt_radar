# Similar Flavors Server-Side Endpoint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Benzer lezzetler hesabını tam aktif katalog üzerinde server-side yaparak A/B harfli alfabetik önyargıyı kaldırmak (spec: `docs/superpowers/specs/2026-08-16-similar-flavors-server-side-design.md`).

**Architecture:** Yeni `GET /api/db/public/whiskies/{id}/similar` endpoint'i, `SimilarityService` ile production.db'den (read-only adapter) tam katalog (4.409 profil) çeker; her profili önce `DbReadService._normalize_flavor_profile` (canonical→app eksen) sonra Dart `flavor_profile_normalizer.dart`'ın birebir portu ile normalize eder; Euclidean sum-of-squares ile sıralar; top-N döner. Flutter repo endpoint'i çağırır, eski backend'de bounded-fetch'e düşer.

**Tech Stack:** FastAPI (backend), sqlite3 read-only (ProductionReadAdapter), pytest (TestClient), Flutter/Dart (Riverpod), package:http MockClient.

## Global Constraints

1. **Read-only zorunlu:** production.db'e ASLA yazma. Bağlantı yalnızca `ProductionReadAdapter.raw_connection()` (mode=ro + query_only). SQL `SELECT` yalnızca belirtilen kolonlar — `fp.*`/`w.*` yok, fiyat redaksiyonu bypass edilmez.
2. **Aktif + katalog parity:** `WHERE w.superseded_by IS NULL` + SMWS hariç (`LOWER(w.name) NOT LIKE '%smws%' AND LOWER(COALESCE(w.brand,'')) NOT LIKE '%smws%'`) — `db_read_service.py:238` katalog sorgusuyla aynı filtre.
3. **Allowlist (G1):** Hedef `whisky_id` allowlist'te değilse → 404. SONUÇLAR tam havuzdur (istisna yalnızca sonuçlar için).
4. **Normalize parity (G4):** `json.loads(DbReadService._normalize_flavor_profile(raw) or "{}")` → sonra Dart `normalizeFlavorProfileMap` portu (7 eksen, `_scale` ≤1→×10, component fallback) — client'ın bugün gördüğü veriyle birebir aynı girdi.
5. **Response shaping (G5):** Alanlar: `whisky_id, name, original_name, distillery_name, region, type, country, meta_critic_score, user_score, distance, similarity`. Fiyat/evidence/ham flavor_profile YOK.
6. **Test runner:** Backend → repo kökünde `backend/.venv/Scripts/python.exe -m pytest backend/tests/<file> -v`. Flutter → `C:/Users/eltun/flutter/bin/flutter.bat test --no-pub`.
7. **DB yolu:** Worktree'de backend testleri için `MALT_RADAR_DB_PATH=C:/Users/eltun/Documents/malt radar CLEAN/output/import/production.db` export et (read-only, güvenli).
8. **Commit:** Her task kendi commit'ini yapar; commit/push yalnızca insan GO'su ile (AGENTS.md kural 15).

---

### Task 1: SimilarityService (backend) — normalize port + tam havuz skorlama

**Files:**
- Create: `backend/app/services/similarity_service.py`
- Test: `backend/tests/test_similarity_service.py`

**Interfaces:**
- Consumes: `ProductionReadAdapter` (import `from app.db.production_read_adapter import ProductionReadAdapter`), `DbReadService._normalize_flavor_profile(raw: str) -> Optional[str]`, `resolve_db_path`.
- Produces: `SimilarityService.get_similar(whisky_id: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]` — `None` = hedef whiskies tablosunda yok; `[]` = profil yok/eşleşme yok; aksi halde sıralı (distance artan) shaped dict listesi.

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_similarity_service.py` (gerçek production.db, mevcut test deseni):

```python
"""SimilarityService — full-pool similarity. Read-only against production.db."""
import json
import pytest
from app.services.similarity_service import SimilarityService


@pytest.fixture
def service():
    return SimilarityService()


def test_unknown_target_returns_none(service):
    assert service.get_similar("DOES-NOT-EXIST-999", limit=5) is None


def test_self_excluded_and_ordered(service):
    # İlk allowlist profilli adayı hedef al (kendini uyarlayan seçim).
    ids = service._candidate_profiles()
    assert len(ids) > 100, "full-pool bekleniyor, bounded havuz değil"
    target = next(iter(ids))
    result = service.get_similar(target, limit=5)
    assert result, "en az 1 benzer olmalı"
    assert len(result) <= 5
    assert all(r["whisky_id"] != target for r in result)
    distances = [r["distance"] for r in result]
    assert distances == sorted(distances)
    assert all(0.0 <= r["similarity"] <= 1.0 for r in result)


def test_full_pool_not_alphabetical_first_250(service):
    """Bug regresyonu: sonuçlar alfabetik ilk 250 (A/B) ile sınırlı OLMAMALI."""
    rows = service._all_active_whiskies()
    name_ordered = sorted(rows, key=lambda r: (r.get("name") or "").lower())
    first250 = {r["whisky_id"] for r in name_ordered[:250]}
    target = next(iter(service._candidate_profiles()))
    result = service.get_similar(target, limit=5)
    assert any(r["whisky_id"] not in first250 for r in result), \
        "benzerlik yalnızca alfabetik ilk 250 havuzundan geldi (bug)"


def test_no_profile_target_returns_empty(service):
    # Profilsiz bir aktif viski bul: flavor_profiles'ta olmayan, superseded olmayan.
    rows = service._all_active_whiskies()
    no_profile = [r for r in rows if not r.get("flavor_profile")]
    if no_profile:
        assert service.get_similar(no_profile[0]["whisky_id"], limit=5) == []
```

- [ ] **Step 2: Testin fail olduğunu doğrula**

Run: `MALT_RADAR_DB_PATH="C:/Users/eltun/Documents/malt radar CLEAN/output/import/production.db" backend/.venv/Scripts/python.exe -m pytest backend/tests/test_similarity_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.similarity_service`.

- [ ] **Step 3: Minimal implementasyon** — `backend/app/services/similarity_service.py`:

```python
"""SimilarityService — tam katalog benzerlik (read-only).

Spec: docs/superpowers/specs/2026-08-16-similar-flavors-server-side-design.md
Normalize parity (G4): raw JSON -> DbReadService._normalize_flavor_profile
(canonical->app axes) -> Dart flavor_profile_normalizer.dart portu.
"""
import json
from typing import Any, Dict, List, Optional

from app.db.production_read_adapter import ProductionReadAdapter
from app.services.db_read_service import DbReadService

MALT_RADAR_AXES = ["fruity", "sweet", "spicy", "smoky_peaty",
                   "oak_cask", "malty_cereal", "floral_herbal"]


def _num_value(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return 0.0
    return 0.0


def _scale(v: float) -> float:
    if v <= 0:
        return 0.0
    if v <= 1:
        return v * 10
    return v


def _has_whiskey_mapper_components(profile: Dict[str, Any]) -> bool:
    return all(f"component_{i}" in profile for i in (1, 2, 3))


def _dart_normalize(profile: Dict[str, Any]) -> Dict[str, float]:
    """flavor_profile_normalizer.dart normalizeFlavorProfileMap portu."""
    axis_profile: Dict[str, float] = {}
    has_axis_value = False
    for axis in MALT_RADAR_AXES:
        value = _num_value(profile.get(axis))
        axis_profile[axis] = value
        has_axis_value = has_axis_value or value > 0
    if has_axis_value:
        return axis_profile
    if _has_whiskey_mapper_components(profile):
        c1 = _num_value(profile.get("component_1"))
        c2 = _num_value(profile.get("component_2"))
        c3 = _num_value(profile.get("component_3"))
        return {
            "fruity": _scale(c1),
            "sweet": _scale((c1 + c2) / 2),
            "spicy": _scale(c2),
            "smoky_peaty": _scale(c3),
            "oak_cask": _scale((c2 + c3) / 2),
            "malty_cereal": _scale((c1 + c3) / 2),
            "floral_herbal": _scale(c1 * 0.5),
        }
    return axis_profile


class SimilarityService:
    def __init__(self, adapter: Optional[ProductionReadAdapter] = None):
        self._adapter = adapter or ProductionReadAdapter()

    def _all_active_whiskies(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT w.whisky_id, w.name, w.original_name, w.distillery_id,
                   d.name AS distillery_name, w.region, w.type, w.country,
                   w.meta_critic_score, w.user_score, fp.flavor_profile
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
            LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
            WHERE w.superseded_by IS NULL
              AND LOWER(w.name) NOT LIKE '%smws%'
              AND LOWER(COALESCE(w.brand, '')) NOT LIKE '%smws%'
        """
        with self._adapter.raw_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return rows

    def _candidate_profiles(self) -> Dict[str, Dict[str, float]]:
        profiles = {}
        for row in self._all_active_whiskies():
            raw = row.get("flavor_profile")
            if not raw:
                continue
            try:
                app_axes = json.loads(
                    DbReadService._normalize_flavor_profile(raw) or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(app_axes, dict):
                continue
            norm = _dart_normalize(app_axes)
            if any(v > 0 for v in norm.values()):
                profiles[row["whisky_id"]] = norm
        return profiles

    def get_similar(self, whisky_id: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        rows = self._all_active_whiskies()
        target_row = next((r for r in rows if r["whisky_id"] == whisky_id), None)
        if target_row is None:
            return None
        raw = target_row.get("flavor_profile")
        if not raw:
            return []
        try:
            target_norm = _dart_normalize(json.loads(
                DbReadService._normalize_flavor_profile(raw) or "{}"))
        except (json.JSONDecodeError, TypeError):
            return []
        if not any(v > 0 for v in target_norm.values()):
            return []
        scored = []
        for row in rows:
            wid = row["whisky_id"]
            if wid == whisky_id:
                continue
            raw_other = row.get("flavor_profile")
            if not raw_other:
                continue
            try:
                other_norm = _dart_normalize(json.loads(
                    DbReadService._normalize_flavor_profile(raw_other) or "{}"))
            except (json.JSONDecodeError, TypeError):
                continue
            if not any(v > 0 for v in other_norm.values()):
                continue
            dist = sum((target_norm[k] - other_norm[k]) ** 2
                       for k in target_norm if k in other_norm)
            item = {k: row[k] for k in (
                "whisky_id", "name", "original_name", "distillery_name",
                "region", "type", "country", "meta_critic_score", "user_score")}
            item["distance"] = round(dist, 6)
            item["similarity"] = round(1.0 / (1.0 + (dist ** 0.5)), 6)
            scored.append(item)
        scored.sort(key=lambda r: r["distance"])
        return scored[:limit]
```

- [ ] **Step 4: Testleri çalıştır — PASS beklenir**

Run: `MALT_RADAR_DB_PATH="C:/Users/eltun/Documents/malt radar CLEAN/output/import/production.db" backend/.venv/Scripts/python.exe -m pytest backend/tests/test_similarity_service.py -v`
Expected: 4 passed. `test_full_pool_not_alphabetical_first_250` kanıttır: en az 1 sonuç alfabetik ilk 250 dışından.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/similarity_service.py backend/tests/test_similarity_service.py
git commit -m "feat(backend): full-pool SimilarityService with Dart-parity normalization"
```

---

### Task 2: `/api/db/public/whiskies/{id}/similar` endpoint

**Files:**
- Modify: `backend/app/services/anonymous_catalog_service.py` (delegate metodu)
- Modify: `backend/app/routers/db_public_api.py` (route)
- Test: `backend/tests/test_similar_endpoint.py`

**Interfaces:**
- Consumes: `SimilarityService.get_similar(whisky_id, limit) -> Optional[List[dict]]` (Task 1).
- Produces: `AnonymousCatalogService.get_similar_whiskies(whisky_id, limit) -> Optional[Dict[str, Any]]` (None = allowlist dışı veya DB'de yok); `GET /api/db/public/whiskies/{whisky_id}/similar?limit=N` → 200 `{"whisky_id": ..., "similar": [...]}` | 404 | 503.

- [ ] **Step 1: Failing test yaz** — `backend/tests/test_similar_endpoint.py`:

```python
"""End-to-end: /api/db/public/whiskies/{id}/similar."""
import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ALLOWLIST = json.load(open("artifacts/anonymous_allowlist.json", encoding="utf-8"))["ids"]


def _pick_target():
    """Allowlist'ten profilli bir hedef seç (kendini uyarlayan)."""
    for wid in ALLOWLIST:
        r = client.get(f"/api/db/public/whiskies/{wid}/flavor-profile")
        if r.status_code == 200:
            return wid
    raise AssertionError("allowlist'te profilli hedef yok")


def test_similar_200_shaped_and_limited():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert body["whisky_id"] == target
    assert len(body["similar"]) <= 5
    for item in body["similar"]:
        assert item["whisky_id"] != target
        assert "distance" in item and "similarity" in item
        # G5: fiyat/evidence sızıntısı yok
        assert "production_price" not in item and "price_value" not in item
        assert "flavor_profile" not in item


def test_similar_anon_no_auth():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar")
    assert res.status_code == 200


def test_similar_non_allowlist_target_404():
    os.environ["DB_API_ENABLED"] = "true"
    res = client.get("/api/db/public/whiskies/NOT-IN-ALLOWLIST-1/similar")
    assert res.status_code == 404


def test_similar_regression_full_pool():
    """Sonuçlar alfabetik ilk 250 ile sınırlı değil (bug regresyonu)."""
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    res = client.get(f"/api/db/public/whiskies/{target}/similar?limit=5")
    similar_ids = {i["whisky_id"] for i in res.json()["similar"]}
    first250 = set()
    for p in range(5):  # eski bug mekanizması: name-ordered sayfa 0-4
        page = client.get(f"/api/db/public/whiskies?limit=50&offset={p*50}").json()
        first250 |= {i["whisky_id"] for i in page["items"]}
    assert similar_ids - first250, "benzerlik yalnızca alfabetik ilk 250 havuzu (bug)"


def test_similar_limit_bounds():
    os.environ["DB_API_ENABLED"] = "true"
    target = _pick_target()
    assert client.get(f"/api/db/public/whiskies/{target}/similar?limit=0").status_code == 422
    assert client.get(f"/api/db/public/whiskies/{target}/similar?limit=21").status_code == 422
```

- [ ] **Step 2: Testin fail olduğunu doğrula**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_similar_endpoint.py -v`
Expected: FAIL — `AttributeError: 'AnonymousCatalogService' object has no attribute 'get_similar_whiskies'` (veya 404 route yok).

- [ ] **Step 3: Delegate + route implementasyonu**

`backend/app/services/anonymous_catalog_service.py` — sınıfın sonuna ekle:

```python
    def get_similar_whiskies(self, whisky_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """G1: hedef allowlist'e tabi; SONUÇLAR tam havuz (bilinçli istisna)."""
        if whisky_id not in self._allowlist_set:
            return None
        from app.services.similarity_service import SimilarityService
        similar = SimilarityService(self._adapter).get_similar(whisky_id, limit)
        if similar is None:
            return None
        return {"similar": similar}
```

`backend/app/routers/db_public_api.py` — `get_flavor_profile` route'unun altına ekle:

```python
@router.get("/whiskies/{whisky_id}/similar")
@limiter.limit("120/minute")
def get_similar_whiskies(
    request: Request,
    whisky_id: str,
    limit: int = Query(5, ge=1, le=20),
    service: AnonymousCatalogService = Depends(get_public_service),
):
    try:
        result = service.get_similar_whiskies(whisky_id, limit)
        if result is None:
            raise HTTPException(status_code=404, detail="Whisky not found in public catalog")
        return {"whisky_id": whisky_id, **result}
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
```

- [ ] **Step 4: Testleri çalıştır — PASS beklenir**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_similar_endpoint.py -v`
Expected: 5 passed.

- [ ] **Step 5: Komşu regresyon — public API suite**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_db_public_api.py backend/tests/test_anonymous_catalog_service.py -v`
Expected: PASS (allowlist davranışı bozulmadı).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/anonymous_catalog_service.py backend/app/routers/db_public_api.py backend/tests/test_similar_endpoint.py
git commit -m "feat(backend): public /whiskies/{id}/similar endpoint (full-pool, G1)"
```

---

### Task 3: Flutter client metodu + repo bağlantısı (fallback'li)

**Files:**
- Modify: `frontend/lib/core/api/db_whisky_api_client.dart` (yeni metot)
- Modify: `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart:184-236` (rewrite + fallback)
- Test: `frontend/test/similar_flavor_backend_test.dart`

**Interfaces:**
- Consumes: `DbWhiskyMapper.toLegacyMap(map)` (mevcut DTO).
- Produces: `DbWhiskyApiClient.getSimilarWhiskies(String whiskyId, {int limit = 5}) -> Future<List<Map<String, dynamic>>?>` (200 → item listesi; 404 → null; diğer → throw); `DbWhiskyRepositoryImpl.getSimilarWhiskies(backendId, {limit})` endpoint öncelikli, 404/hatada bounded-fetch fallback.

- [ ] **Step 1: Failing test yaz** — `frontend/test/similar_flavor_backend_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:malt_radar/core/api/db_whisky_api_client.dart';
import 'package:malt_radar/core/database/database.dart';
import 'package:malt_radar/features/whisky/data/repositories/db_whisky_repository_impl.dart';
import 'package:drift/native.dart';

const _similarJson = {
  'whisky_id': 'W000001',
  'similar': [
    {
      'whisky_id': 'W000002',
      'name': 'Ardbeg 10',
      'distillery_name': 'Ardbeg',
      'region': 'Islay',
      'type': 'Malt',
      'meta_critic_score': 8.4,
      'distance': 0.5,
      'similarity': 0.586,
    },
    {
      'whisky_id': 'W000003',
      'name': 'Laphroaig 10',
      'distillery_name': 'Laphroaig',
      'region': 'Islay',
      'type': 'Malt',
      'distance': 1.2,
      'similarity': 0.477,
    },
  ],
};

void main() {
  test('client getSimilarWhiskies parses public /similar response', () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async {
        expect(req.url.path, '/api/db/public/whiskies/W000001/similar');
        return http.Response('''{"whisky_id":"W000001","similar":[
          {"whisky_id":"W000002","name":"Ardbeg 10","distillery_name":"Ardbeg",
           "region":"Islay","type":"Malt","meta_critic_score":8.4,
           "distance":0.5,"similarity":0.586}]}''', 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }),
    );
    final result = await client.getSimilarWhiskies('W000001', limit: 5);
    expect(result, isNotNull);
    expect(result!.length, 1);
    expect(result.first['whisky_id'], 'W000002');
  });

  test('client returns null on 404 (target not found)', () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async => http.Response('not found', 404)),
    );
    expect(await client.getSimilarWhiskies('W000001'), isNull);
  });

  test('repo uses endpoint result and maps similarity to styleSimilarity',
      () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async => http.Response(
          jsonEncode(_similarJson), 200,
          headers: {'content-type': 'application/json; charset=utf-8'})),
    );
    final repo = DbWhiskyRepositoryImpl(AppDatabase.forTesting(NativeDatabase.memory()), client);
    final result = await repo.getSimilarWhiskies('W000001', limit: 5);
    expect(result.length, 2);
    expect(result.first.externalId, 'W000002');
    expect(result.first.styleSimilarity, isNotNull);
    expect(result.first.globalScore, 8.4); // meta_critic_score fallback
    await repo.clearCache();
  });

  test('repo falls back to bounded fetch when endpoint 404s', () async {
    final client = DbWhiskyApiClient(
      client: MockClient((req) async {
        if (req.url.path.endsWith('/similar')) {
          return http.Response('not found', 404);
        }
        if (req.url.path.contains('/whiskies')) {
          return http.Response(
              '{"items":[{"whisky_id":"W000009","name":"Glenfiddich 12",'
              '"flavor_profile":"{\\"fruity\\":3.0,\\"sweet\\":4.0,'
              '\\"spicy\\":1.0,\\"smoky_peaty\\":0.0,\\"oak_cask\\":2.0,'
              '\\"malty_cereal\\":5.0,\\"floral_herbal\\":2.0}"}],'
              '"total_count":1,"limit":50,"offset":0}', 200,
              headers: {'content-type': 'application/json; charset=utf-8'});
        }
        return http.Response('{"similar":[]}', 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }),
    );
    final repo = DbWhiskyRepositoryImpl(AppDatabase.forTesting(NativeDatabase.memory()), client);
    // 404 -> fallback; fallback havuzunda profil yoksa sonuç boş olabilir —
    // kritik nokta: THROW etmemesi ve boş liste dönmesi.
    final result = await repo.getSimilarWhiskies('W000001', limit: 5);
    expect(result, isA<List>());
    await repo.clearCache();
  });
}
```

Not: test dosyasına `import 'dart:convert';` ekle (jsonEncode için).

- [ ] **Step 2: Testin fail olduğunu doğrula**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/similar_flavor_backend_test.dart --no-pub`
Expected: FAIL — `NoSuchMethodError: getSimilarWhiskies` (client'ta metot yok).

- [ ] **Step 3: Client metodu** — `frontend/lib/core/api/db_whisky_api_client.dart` (`search` metodunun altına):

```dart
  /// Full-pool similar whiskies (public namespace — route yalnızca
  /// /api/db/public altında tanımlı, G1 spec). 404 -> null (hedef yok);
  /// diğer status -> throw (repo fallback'e düşer).
  Future<List<Map<String, dynamic>>?> getSimilarWhiskies(
      String whiskyId, {int limit = 5}) async {
    await _ensureToken();
    final uri = Uri.parse(
        '${AppConfig.baseUrl}/api/db/public/whiskies/${Uri.encodeComponent(whiskyId)}/similar?limit=$limit');
    final response = await _client.get(uri, headers: _headers());
    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return (data['similar'] as List?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          [];
    } else if (response.statusCode == 404) {
      return null;
    }
    throw Exception('API db similar failed: ${response.statusCode}');
  }
```

- [ ] **Step 4: Repo rewrite** — `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart:184-236`, `getSimilarWhiskies` gövdesini değiştir:

```dart
  @override
  Future<List<Whisky>> getSimilarWhiskies(String backendId, {int limit = 5}) async {
    // Öncelik: server-side full-pool endpoint (spec G1/G6). Eski backend'de
    // 404/network hatası olursa bounded-fetch fallback (eski davranış).
    try {
      final maps = await _dbClient.getSimilarWhiskies(backendId, limit: limit);
      if (maps == null) return []; // hedef yok -> "no similar flavors"
      return maps
          .map((m) {
            final legacy = DbWhiskyMapper.toLegacyMap(m);
            final sim = m['similarity'];
            if (sim is num) legacy['style_similarity'] = sim.toString();
            return Whisky.fromMap(legacy);
          })
          .toList();
    } catch (_) {
      return _boundedSimilarFallback(backendId, limit: limit);
    }
  }

  /// Eski backend uyumluluğu: 5-page (250 satır) alfabetik bounded fetch.
  /// Yeni backend'de yalnızca endpoint hatasında tetiklenir.
  Future<List<Whisky>> _boundedSimilarFallback(String backendId,
      {int limit = 5}) async {
    try {
      final target = await getWhiskyByBackendId(backendId);
      if (target?.flavorProfile == null) return [];

      Map<String, double> targetProfile;
      try {
        targetProfile = normalizeFlavorProfileJson(target!.flavorProfile!);
      } catch (_) {
        return [];
      }
      if (targetProfile.isEmpty) return [];

      final all = <Whisky>[];
      for (var p = 0; p < 5; p++) {
        final page = await getWhiskiesPage(offset: p * 50, limit: 50);
        if (page.isEmpty) break;
        all.addAll(page);
      }
      if (all.isEmpty) return [];

      final scored = <Map<String, dynamic>>[];
      for (final other in all) {
        if (other.externalId == backendId) continue;
        if (other.flavorProfile == null) continue;
        Map<String, double> otherProfile;
        try {
          otherProfile = normalizeFlavorProfileJson(other.flavorProfile!);
        } catch (_) {
          continue;
        }
        double sumSquares = 0.0;
        bool hasData = false;
        for (final entry in targetProfile.entries) {
          final v = otherProfile[entry.key] ?? 0.0;
          final diff = entry.value - v;
          sumSquares += diff * diff;
          hasData = true;
        }
        if (hasData) scored.add({'whisky': other, 'distance': sumSquares});
      }

      scored.sort(
          (a, b) => (a['distance'] as double).compareTo(b['distance'] as double));
      return scored.take(limit).map((e) => e['whisky'] as Whisky).toList();
    } catch (_) {
      return [];
    }
  }
```

- [ ] **Step 5: Testleri çalıştır — PASS beklenir**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/similar_flavor_backend_test.dart --no-pub`
Expected: 4 passed.

- [ ] **Step 6: Komşu regresyon — mevcut Flutter testleri**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/similar_flavor_test.dart test/widget_test.dart --no-pub`
Expected: PASS (lokal mod + widget override bozulmadı).

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/core/api/db_whisky_api_client.dart frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart frontend/test/similar_flavor_backend_test.dart
git commit -m "feat(frontend): similar-flavors via server-side endpoint with bounded-fetch fallback"
```

---

### Task 4: Uçtan uca doğrulama + closure

**Files:**
- Create: `docs/superpowers/specs/incident-2026-08-14/` altına DEĞİL — `docs/superpowers/specs/2026-08-16-similar-flavors-verification.md` (closure kanıtı)

- [ ] **Step 1: Backend tam suite**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_similarity_service.py backend/tests/test_similar_endpoint.py backend/tests/test_db_public_api.py backend/tests/test_anonymous_catalog_service.py -v`
Expected: ALL PASS.

- [ ] **Step 2: Flutter tam suite (ilgili dosyalar)**

Run: `cd frontend && C:/Users/eltun/flutter/bin/flutter.bat test test/similar_flavor_backend_test.dart test/similar_flavor_test.dart test/widget_test.dart --no-pub`
Expected: ALL PASS. Ardından `C:/Users/eltun/flutter/bin/flutter.bat analyze --no-pub` → `No issues found!`.

- [ ] **Step 3: Canlı backend'de manuel kanıt (3 hedef profili)**

Backend çalışıyorsa (uvicorn), hedef seç: allowlist'ten profilli 3 farklı tip (peated Islay / sherry / bourbon). Her biri için:

```bash
curl -s "http://localhost:8000/api/db/public/whiskies/<id>/similar?limit=5" | python -m json.tool
```

Kabul kriterleri:
- Sonuçlarda alfabetik A/B önyargısı yok (en az 1 sonuç ilk-250 dışı — Task 2 testi bunu zaten kanıtlar).
- Sonuçlar mantıklı: peated hedef → smoky_peaty komşuları; sherry hedef → oaky/sweet komşuları.
- `production_price`/`flavor_profile` alanı yok (G5).
- `similarity` değerleri 0-1 arası, distance artan sırada.

- [ ] **Step 4: Read-only kanıtı — production.db SHA256 değişmedi**

```bash
sha256sum "output/import/production.db"
```
Expected: `cbffd16b29433c983bb113b2e9a9f186dd94c1ff9dc6f5f1b13d97f084386177` (AGENTS.md baseline) — endpoint yalnızca okur.

- [ ] **Step 5: Closure kanıtı yaz** — `docs/superpowers/specs/2026-08-16-similar-flavors-verification.md`:

İçerik (şablon):
- Phase ID: `similar-flavors-server-side` · Spec ref: `2026-08-16-similar-flavors-server-side-design.md`
- Backend test sonuçları (task bazlı PASS sayıları)
- Flutter test sonuçları + analyze çıktısı
- Canlı curl örnekleri (3 hedef)
- production.db SHA256 (önce/sonra aynı — read-only kanıtı)
- G1 istisnası kaydı (tam havuz sonuç, bilinçli kapsam genişletmesi)

- [ ] **Step 6: Commit (closure)**

```bash
git add docs/superpowers/specs/2026-08-16-similar-flavors-verification.md
git commit -m "docs(closure): similar-flavors server-side verification (read-only kanıtı)"
```

- [ ] **Step 7: Deploy + canlı doğrulama (yalnızca insan GO'suyla)**

Backend canlıya deploy (kullanıcı GO'su gerektirir — mevcut deploy akışı). Deploy sonrası Flutter build'inde `?cb=` cache-bust doğrula (mevcut Caddy kuralı: index/JS no-cache, assets 1y). Son kullanıcı görünür kanıt: detail ekranında "Benzer Lezzetler" A/B dışı gerçek komşular gösteriyor.

---

## Self-Review (plan yazarı tarafından yapıldı)

1. **Spec coverage:** G1 (allowlist hedef/404 + tam havuz sonuç) → Task 2 testleri + Task 1 testi; G2 (read-only) → Task 4 Step 4 SHA kanıtı; G3 (Euclidean) → Task 1 `get_similar`; G4 (normalize parity) → Task 1 `_dart_normalize` + `_normalize_flavor_profile` zinciri; G5 (shaping) → Task 2 Step 1 test assert'leri; G6 (fallback) → Task 3 Step 4 `_boundedSimilarFallback`; G7 (kapsam dışı) → plana alınmadı (bilinçli). Spec madde 4.1-4.7 → Task 1 davranış kuralları. Spec test listesi 1-8 → Task 1-3 testleri.
2. **Placeholder scan:** Tüm adımlar gerçek kod + komut içeriyor; TBD/TODO yok.
3. **Type consistency:** `SimilarityService.get_similar -> Optional[List[dict]]` Task 1→2 tutarlı; `AnonymousCatalogService.get_similar_whiskies -> Optional[Dict]` Task 2→route tutarlı; `DbWhiskyApiClient.getSimilarWhiskies -> Future<List<Map<String,dynamic>>?>` Task 3 client→repo tutarlı; `style_similarity` repo map'i `Whisky.styleSimilarity` (`whisky.dart:227`) ile eşleşiyor; `meta_critic_score` → `globalScore` DTO fallback zinciri (`db_whisky_dto.dart:29`) ile eşleşiyor.
4. **Bilinen risk:** Task 1 `test_no_profile_target_returns_empty` veriye bağımlı — production'da profilsiz aktif viski yoksa `no_profile` boş olur ve assert atlanır (`if no_profile:` guard'ı). Kabul edilebilir (invariant korunur).
