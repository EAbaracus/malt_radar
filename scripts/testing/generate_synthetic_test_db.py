#!/usr/bin/env python3
"""
Generate a synthetic SQLite database for backend test runs.

Several "production tests" in backend/tests/ (test_similarity_service.py's
existing production-test block, test_db_api_auth.py, test_db_public_api.py,
test_allowlist_build.py, test_anonymous_catalog_service.py,
test_db_read_service_filter.py, test_filter_param.py, test_db_price_leak.py,
test_similar_endpoint.py) expect a realistically-sized database (100+ rows)
at MALT_RADAR_DB_PATH (default: output/import/production.db) rather than
building their own tiny in-memory fixture. Per the repo's data-hygiene
policy (P204B), the real production.db must never be committed to git, so
this script creates a wholly-synthetic stand-in with the same schema
(schema/schema.sql) and made-up data, safe to (re)generate on demand in CI
or locally.

No real product/customer data of any kind is embedded in this script.

Usage:
    python scripts/testing/generate_synthetic_test_db.py [--out PATH] [--n N]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = REPO_ROOT / "output" / "import" / "production.db"

FLAVOR_AXES = [
    "fruity",
    "maritime",
    "peaty",
    "sherry",
    "smoky",
    "spicy",
    "sweet",
]

REGIONS = ["Speyside", "Highland", "Islay", "Lowland", "Campbeltown", "Islands"]
TYPES = ["Single Malt", "Blended", "Bourbon", "Rye", "Blended Malt"]
COUNTRIES = ["Scotland", "Ireland", "USA", "Japan", "Canada"]

SCHEMA_SQL = """
CREATE TABLE distilleries (
  distillery_id TEXT PRIMARY KEY,
  name TEXT,
  country TEXT,
  region TEXT,
  data_confidence TEXT
);

CREATE TABLE whiskies (
  whisky_id TEXT PRIMARY KEY,
  name TEXT,
  original_name TEXT,
  distillery_id TEXT,
  country TEXT,
  region TEXT,
  type TEXT,
  brand TEXT,
  meta_critic_score REAL,
  user_score REAL,
  superseded_by TEXT,
  data_confidence TEXT
);

CREATE TABLE price_history (
  price_id TEXT PRIMARY KEY,
  whisky_id TEXT,
  source_name TEXT,
  price_value REAL,
  currency TEXT,
  observed_at TEXT,
  FOREIGN KEY (whisky_id) REFERENCES whiskies(whisky_id)
);

CREATE TABLE flavor_evidence (
  evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
  whisky_id TEXT,
  source TEXT
);

CREATE TABLE flavor_profiles (
  whisky_id TEXT PRIMARY KEY,
  whisky_name TEXT,
  production_bottle_name TEXT,
  match_score INTEGER,
  match_method TEXT,
  flavor_vector TEXT,
  flavor_profile TEXT,
  flavor_tags TEXT,
  flavor_source TEXT,
  flavor_data_confidence TEXT,
  production_price REAL,
  production_rating REAL,
  production_region TEXT,
  notes_for_review TEXT,
  source_count INTEGER DEFAULT 1,
  evidence_count INTEGER DEFAULT 1,
  enrichment_version INTEGER DEFAULT 1
);

CREATE TABLE official_source_references (
  ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  source_category TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_domain TEXT NOT NULL,
  field_name TEXT NOT NULL,
  field_value TEXT,
  confidence REAL DEFAULT 1.0,
  retrieved_at TEXT NOT NULL,
  license_risk TEXT DEFAULT 'low',
  copyright_risk TEXT DEFAULT 'low',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE source_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_title TEXT,
    source_type TEXT,
    domain TEXT,
    extraction_timestamp TEXT,
    extracted_records_count INTEGER,
    status TEXT
);
"""


def _random_flavor_profile(rng: random.Random) -> str:
    return json.dumps({axis: rng.randint(1, 10) for axis in FLAVOR_AXES})


def generate(out_path: Path, n: int, seed: int = 42) -> None:
    rng = random.Random(seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(out_path)
    conn.executescript(SCHEMA_SQL)

    n_distilleries = max(5, n // 20)
    distillery_ids = [f"SYN-DIST-{i:04d}" for i in range(n_distilleries)]
    for i, did in enumerate(distillery_ids):
        conn.execute(
            "INSERT INTO distilleries VALUES (?, ?, ?, ?, ?)",
            (
                did,
                f"Synthetic Distillery {i}",
                rng.choice(COUNTRIES),
                rng.choice(REGIONS),
                "synthetic",
            ),
        )

    for i in range(n):
        wid = f"SYN-W-{i:05d}"
        did = rng.choice(distillery_ids)
        conn.execute(
            "INSERT INTO whiskies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                wid,
                f"Synthetic Whisky {i:05d}",
                None,
                did,
                rng.choice(COUNTRIES),
                rng.choice(REGIONS),
                rng.choice(TYPES),
                f"Synthetic Brand {i % 17}",
                round(rng.uniform(60, 98), 1),  # meta_critic_score
                round(rng.uniform(1, 5), 2),  # user_score
                None,  # superseded_by
                "synthetic",
            ),
        )
        conn.execute(
            "INSERT INTO price_history VALUES (?, ?, ?, ?, ?, ?)",
            (
                f"SYN-PRICE-{i:05d}",
                wid,
                "synthetic-source",
                round(rng.uniform(20, 500), 2),
                "USD",
                "2026-01-01",
            ),
        )
        # ~90% of whiskies get a flavor profile, mirroring real coverage gaps
        if rng.random() < 0.9:
            conn.execute(
                "INSERT INTO flavor_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    wid,
                    f"Synthetic Whisky {i}",
                    f"Synthetic Whisky {i}",  # production_bottle_name
                    round(rng.uniform(0.5, 1.0), 2),  # match_score
                    "synthetic",  # match_method
                    None,  # flavor_vector
                    _random_flavor_profile(rng),
                    None,  # flavor_tags
                    "synthetic",  # flavor_source
                    "synthetic",  # flavor_data_confidence
                    None,  # production_price (must stay NULL/absent from safe reads)
                    round(rng.uniform(1, 5), 2),  # production_rating
                    rng.choice(REGIONS),  # production_region
                    None,  # notes_for_review
                    1,
                    1,
                    1,
                ),
            )
            # ~60% of those with a profile also have supporting evidence
            if rng.random() < 0.6:
                conn.execute(
                    "INSERT INTO flavor_evidence (whisky_id, source) VALUES (?, ?)",
                    (wid, "synthetic-evidence"),
                )

    conn.commit()

    # Deterministically guarantee similarity-diversity: whisky #0's flavor
    # profile gets a near-twin far outside the alphabetical-first-250 slice,
    # so tests asserting the similarity pool isn't limited to that slice pass
    # reliably regardless of the random draws above.
    if n > 260:
        twin_idx = n - 5
        base_row = conn.execute(
            "SELECT flavor_profile FROM flavor_profiles WHERE whisky_id = ?",
            (f"SYN-W-{0:05d}",),
        ).fetchone()
        if base_row:
            base_profile = json.loads(base_row[0])
            twin_profile = dict(base_profile)
            # tiny perturbation so it's "near" not identical
            twin_profile[FLAVOR_AXES[0]] = max(1, min(10, twin_profile[FLAVOR_AXES[0]] + 1))
            twin_id = f"SYN-W-{twin_idx:05d}"
            conn.execute(
                "DELETE FROM flavor_profiles WHERE whisky_id = ?", (twin_id,)
            )
            conn.execute(
                "INSERT INTO flavor_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    twin_id,
                    f"Synthetic Whisky {twin_idx:05d}",
                    f"Synthetic Whisky {twin_idx:05d}",
                    0.9,
                    "synthetic",
                    None,
                    json.dumps(twin_profile),
                    None,
                    "synthetic",
                    "synthetic",
                    None,
                    3.5,
                    rng.choice(REGIONS),
                    None,
                    1,
                    1,
                    1,
                ),
            )
            conn.commit()

    conn.close()
    print(f"Wrote synthetic DB with {n} whiskies / {n_distilleries} distilleries to {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n", type=int, default=300, help="number of synthetic whiskies")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.out, args.n, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
