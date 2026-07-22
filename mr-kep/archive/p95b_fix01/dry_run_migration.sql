-- ============================================================================
-- P95B-FIX-01 — DRY-RUN MIGRATION (NOT EXECUTED)
-- ============================================================================
-- Mode: READ-ONLY verification. Nothing below was run. No production mutation.
-- production.db SHA at analysis time: 8350fe9de2f1c73d9c4b6930bae607afe64696527910c2709b8b3a4a634c6a3a
--
-- Goal: bring production.flavor_evidence into parity with the canonical frozen
-- 7-axis contract (smoky, peaty, fruity, sweet, spicy, maritime, sherry @0-100).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FIX (REQUIRED): add the missing canonical axis `vector_maritime`
-- ----------------------------------------------------------------------------
-- Closes the only canonical-axis gap in flavor_evidence. maritime is produced by
-- the real d4 reducer, P96, and the editorial extractor, and is absent ONLY here.
ALTER TABLE flavor_evidence ADD COLUMN vector_maritime REAL;

-- IMPORTANT: No backfill is possible from existing data.
--   - vector_maritime was never stored (column did not exist).
--   - Per CANONICAL_SCHEMA.md, `rich` is NOT the maritime axis (rich maps to
--     sweet-side); vector_rich MUST NOT be used to derive vector_maritime.
-- Historical rows remain NULL until a re-extraction/promotion pass is authorized.

-- ----------------------------------------------------------------------------
-- FIX (OPTIONAL, COMMENTED — higher-risk, separate review):
--         normalize existing 0-1 columns to the canonical 0-100 scale
-- ----------------------------------------------------------------------------
-- Canonical contract mandates axis_scale='0-100' (0-1 inputs x100).
-- Current flavor_evidence.vector_* are on a 0-1 scale (verified min/max 0.0-1.0).
-- Uncomment ONLY after explicit approval + full backup.
--
-- UPDATE flavor_evidence
--    SET vector_smoky  = vector_smoky  * 100,
--        vector_peaty  = vector_peaty  * 100,
--        vector_sherry = vector_sherry * 100,
--        vector_fruity = vector_fruity * 100,
--        vector_spicy  = vector_spicy  * 100,
--        vector_sweet  = vector_sweet  * 100,
--        vector_rich   = vector_rich   * 100;   -- legacy retained (deprecated)

-- ----------------------------------------------------------------------------
-- DISPOSITION: vector_rich (legacy / evidence-only / unmappable)
-- ----------------------------------------------------------------------------
-- Keep vector_rich. It is in ambiguity_handler.unmappable (cannot map to a canonical
-- axis) and is non-canonical. Retain as provenance; mark deprecated; NEVER promote
-- as canonical; NEVER derive vector_maritime from it. No DROP in this migration.

-- ----------------------------------------------------------------------------
-- ROLLBACK (if FIX applied in a future authorized migration)
-- ----------------------------------------------------------------------------
-- SQLite pre-3.35 cannot DROP a column without a table rebuild; since maritime would
-- be NULL for all historical rows, dropping is safe. Recommend a pre-migration
-- backup: production.db.pre_p95b_fix01_*.bak.

-- ============================================================================
-- VERIFICATION QUERIES (read-only; safe to run for confirmation)
-- ============================================================================
-- SELECT name FROM pragma_table_info('flavor_evidence') WHERE name='vector_maritime';
-- SELECT COUNT(*) FROM flavor_evidence WHERE vector_maritime IS NOT NULL;  -- expect 0 pre-backfill
-- SELECT MIN(vector_smoky), MAX(vector_smoky) FROM flavor_evidence;        -- confirm 0-1 scale
-- SELECT COUNT(*) FROM flavor_profiles WHERE flavor_profile LIKE '%maritime%';  -- expect 1942
