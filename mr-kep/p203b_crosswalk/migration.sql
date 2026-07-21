CREATE TABLE IF NOT EXISTS distillery_crosswalk (
  crosswalk_id   INTEGER PRIMARY KEY,
  entity_id      TEXT    NOT NULL,
  canonical_name TEXT    NOT NULL,
  external_name  TEXT    NOT NULL,
  source         TEXT    NOT NULL,
  confidence     REAL    NOT NULL,
  match_method   TEXT,
  created_at     TEXT,
  UNIQUE(entity_id, external_name, source)
);
CREATE INDEX IF NOT EXISTS idx_cw_external ON distillery_crosswalk(external_name);
CREATE INDEX IF NOT EXISTS idx_cw_entity ON distillery_crosswalk(entity_id);
CREATE INDEX IF NOT EXISTS idx_cw_source ON distillery_crosswalk(source);

CREATE TABLE IF NOT EXISTS distillery_crosswalk_review (
  review_id      INTEGER PRIMARY KEY,
  external_name  TEXT    NOT NULL,
  source         TEXT    NOT NULL,
  confidence     REAL    NOT NULL,
  match_method   TEXT,
  reason         TEXT,
  suggested_id   TEXT,
  created_at     TEXT,
  UNIQUE(external_name, source)
);
CREATE INDEX IF NOT EXISTS idx_cwr_external ON distillery_crosswalk_review(external_name);
