-- ============================================================================
-- P95B Phase 9.9 — DRY-RUN MIGRATION (NOT EXECUTED)
-- ============================================================================
-- Mode: READ-ONLY verification. This script is provided for review only.
-- NO statement below was run. No production.db mutation occurred.
-- production.db SHA at time of analysis: 8350fe9de2f1c73d9c4b6930bae607afe64696527910c2709b8b3a4a634c6a3a
--
-- Goal: align production.flavor_evidence with the canonical 7-axis contract
--       (CANONICAL_SCHEMA.md: smoky, peaty, fruity, sweet, spicy, maritime, sherry @ 0-100)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FIX 1 (REQUIRED): add the missing canonical axis `vector_maritime`
-- ----------------------------------------------------------------------------
-- Closes GAP 1: maritime is a canonical axis, is produced by the editorial
-- extractor, and exists as a column in sibling staging tables, but is absent
-- from flavor_evidence -> maritime evidence is silently dropped on promotion.
ALTER TABLE flavor_evidence ADD COLUMN vector_maritime REAL;

-- IMPORTANT: No backfill is possible from existing data.
--   - vector_maritime was never stored (column did not exist).
--   - Per CANONICAL_SCHEMA.md, `rich` is NOT the maritime axis (rich maps to
--     sweet-side), so vector_rich MUST NOT be used to derive vector_maritime.
-- New rows populated by the (corrected) promotion path will carry real values;
-- historical rows remain NULL until a re-extraction pass is authorized.

-- ----------------------------------------------------------------------------
-- FIX 2 (OPTIONAL, COMMENTED — higher-risk, separate review):
--         normalize existing 0-1 columns to the canonical 0-100 scale
-- ----------------------------------------------------------------------------
-- CANONICAL_SCHEMA mandates axis_scale='0-100' (0-1 inputs x100).
-- Current flavor_evidence.vector_* are on a 0-1 scale.
-- Uncomment ONLY after explicit approval and a full backup.
--
-- UPDATE flavor_evidence
--    SET vector_smoky  = vector_smoky  * 100,
--        vector_peaty  = vector_peaty  * 100,
--        vector_sherry = vector_sherry * 100,
--        vector_fruity = vector_fruity * 100,
--        vector_spicy  = vector_spicy  * 100,
--        vector_sweet  = vector_sweet  * 100,
--        vector_rich   = vector_rich   * 100;   -- rich retained; see FIX 3

-- ----------------------------------------------------------------------------
-- FIX 3 (RECOMMENDED, NON-DESTRUCTIVE): deprecate, do NOT drop, vector_rich
-- ----------------------------------------------------------------------------
-- vector_rich is a SURPLUS / non-canonical column (CANONICAL_SCHEMA: rich is not
-- the maritime axis). It is orphaned (no current extractor produces it) but all
-- 791 rows carry a value, so it is retained to avoid data loss. Flag for
-- deprecation; do not delete in this migration.
-- (No SQL needed — documented for the promotion-layer cleanup ticket.)

-- ----------------------------------------------------------------------------
-- ROLLBACK (if FIX 1 applied in a future authorized migration)
-- ----------------------------------------------------------------------------
-- SQLite cannot DROP a column before 3.35 without table rebuild; if applied,
-- rollback via a temp-table rebuild excluding vector_maritime, or simply:
--   (no-op: maritime was NULL for all historical rows, so dropping is safe)
-- Recommend: keep a pre-migration backup (production.db.pre_p95b_*.bak).

-- ============================================================================
-- VERIFICATION QUERIES (read-only; safe to run for confirmation)
-- ============================================================================
-- SELECT name FROM pragma_table_info('flavor_evidence') WHERE name='vector_maritime';
-- SELECT COUNT(*) FROM flavor_evidence WHERE vector_maritime IS NOT NULL;  -- expect 0 pre-backfill
-- SELECT MIN(vector_smoky), MAX(vector_smoky) FROM flavor_evidence;        -- confirm 0-1 scale
