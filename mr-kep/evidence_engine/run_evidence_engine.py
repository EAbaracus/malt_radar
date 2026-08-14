# =============================================================================
# MR-KEP P73 — Evidence Engine CLI / batch runner
# -----------------------------------------------------------------------------
# Read qualification records (qualification.schema.json) from a directory or a
# single JSON file, emit P64-compatible evidence candidates to a JSONL ledger.
# Read-only on Sprint 1 configs; writes only a staging ledger file (no
# production.db). Deterministic + idempotent.
# =============================================================================
import os
import sys
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E


def _load_qual_records(path: str):
    recs = []
    if os.path.isdir(path):
        for fp in sorted(glob.glob(os.path.join(path, "*.json"))):
            recs.extend(_load_qual_records(fp))
    elif os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            recs.extend(data)
        elif isinstance(data, dict):
            # single record OR {"qualification_records": [...]}
            if "units" in data and "source_key" in data:
                recs.append(data)
            elif "qualification_records" in data:
                recs.extend(data["qualification_records"])
    return recs


def main(argv):
    if len(argv) < 3:
        print("usage: python run_evidence_engine.py <qual_dir_or_file> <out_ledger.jsonl>")
        return 2
    in_path = argv[1]
    out_path = argv[2]
    recs = _load_qual_records(in_path)
    if not recs:
        print(f"[P73] no qualification records found at {in_path}")
        return 1
    cfg = E.load_authority_configs()
    ledger = E.run(recs, cfg)
    E.write_ledger_jsonl(ledger, out_path)
    print(f"[P73] consumed {len(recs)} qualification record(s) -> "
          f"{len(ledger)} evidence candidate(s) -> {out_path}")
    # quick schema self-check
    try:
        import jsonschema
        schema = json.load(open(E.EVIDENCE_SCHEMA_PATH, encoding="utf-8"))
        v = jsonschema.Draft7Validator(schema)
        bad = sum(1 for e in ledger if list(v.iter_errors(e)))
        print(f"[P73] schema validation: {len(ledger)-bad}/{len(ledger)} valid")
    except Exception:
        print("[P73] jsonschema not available; skipped schema self-check")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
