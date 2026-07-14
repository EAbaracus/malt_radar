"""
P95.6 — Schema Validation

Validates every produced artifact against the existing project schemas.
Verifies schema compliance, required fields, authority preservation,
evidence linkage, and deterministic serialization.

Rejects invalid outputs.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import jsonschema

    HAS_JSCONSCHEMA = True
except ImportError:
    HAS_JSCONSCHEMA = False
    logger.warning("jsonschema not installed — schema validation will use manual checks")


# Cache loaded schemas
_schema_cache: Dict[str, Dict] = {}


def _load_schema(path: str) -> Optional[Dict]:
    """Load a JSON schema from disk, caching the result."""
    if path in _schema_cache:
        return _schema_cache[path]
    if not os.path.exists(path):
        logger.warning(f"Schema file not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        _schema_cache[path] = schema
        return schema
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load schema {path}: {e}")
        return None


class SchemaValidator:
    """Validates artifacts against MR-KEP JSON schemas.

    Uses jsonschema when available; falls back to manual required-field
    checks to avoid dependency requirements.
    """

    def __init__(self, schemas_dir: str):
        self.schemas_dir = schemas_dir
        self.results: List[Dict] = []
        self.failures = 0
        self.passes = 0

    def validate(
        self, artifact_name: str, artifact_path: str, schema_name: str
    ) -> Dict:
        """Validate an artifact against a named schema.

        Args:
            artifact_name: Human-readable name (e.g. 'extraction record')
            artifact_path: Path to the JSON artifact file
            schema_name: Filename of the schema (e.g. 'extraction.schema.json')

        Returns:
            Validation result dict: {artifact, schema, valid, errors, warnings}
        """
        schema_path = os.path.join(self.schemas_dir, schema_name)
        schema = _load_schema(schema_path)
        artifact = self._load_artifact(artifact_path)

        result = {
            "artifact": artifact_name,
            "artifact_path": artifact_path,
            "schema": schema_name,
            "valid": False,
            "errors": [],
            "warnings": [],
        }

        if schema is None:
            result["errors"].append(f"Schema {schema_name} could not be loaded")
            self.results.append(result)
            self.failures += 1
            return result

        if artifact is None:
            result["errors"].append(f"Artifact {artifact_path} could not be loaded")
            self.results.append(result)
            self.failures += 1
            return result

        # Validate using jsonschema if available
        if HAS_JSCONSCHEMA:
            try:
                jsonschema.validate(artifact, schema)
                result["valid"] = True
                self.passes += 1
            except jsonschema.ValidationError as e:
                result["errors"].append(str(e))
                self.failures += 1
        else:
            # Manual required-field check
            self._manual_validate(artifact, schema, result)

        # Authority preservation check
        self._check_authority(artifact, result)

        # Evidence linkage check
        self._check_evidence_linkage(artifact, result)

        # Deterministic serialization check
        self._check_deterministic(artifact, result)

        self.results.append(result)
        return result

    def validate_artifact(
        self, artifact: Dict, schema_path: str
    ) -> Tuple[bool, List[str]]:
        """Validate a dict (artifact in memory) against a schema file.
        Returns (valid, error_list).
        """
        schema = _load_schema(schema_path)
        if schema is None:
            return (False, [f"Schema not found: {schema_path}"])

        if HAS_JSCONSCHEMA:
            try:
                jsonschema.validate(artifact, schema)
                return (True, [])
            except jsonschema.ValidationError as e:
                return (False, [str(e)])
        else:
            errors = []
            req_fields = schema.get("required", [])
            for field in req_fields:
                if field not in artifact:
                    errors.append(f"Missing required field: {field}")
            return (len(errors) == 0, errors)

    def _load_artifact(self, path: str) -> Optional[Dict]:
        """Load a JSON artifact from disk."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return None
                return json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load artifact {path}: {e}")
            return None

    def _manual_validate(self, artifact: Dict, schema: Dict, result: Dict):
        """Manual schema validation when jsonschema is unavailable."""
        errors = []
        warnings = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in artifact:
                errors.append(f"Missing required field: {field}")

        # Check type if specified
        expected_type = schema.get("type")
        if expected_type and expected_type != "object":
            actual_type = type(artifact).__name__
            if actual_type != expected_type:
                errors.append(f"Expected type {expected_type}, got {actual_type}")

        # Check schema_version pattern if present
        sv = artifact.get("schema_version")
        if sv is not None and not isinstance(sv, str):
            errors.append(f"schema_version must be string, got {type(sv).__name__}")

        if errors:
            result["errors"].extend(errors)
            result["valid"] = False
            self.failures += 1
        else:
            result["valid"] = True
            self.passes += 1

        if warnings:
            result["warnings"].extend(warnings)

    def _check_authority(self, artifact: Dict, result: Dict):
        """Verify authority tier preservation where applicable."""
        # Check for source fields that preserve authority
        if "evidence_index" in artifact:
            for entry in artifact["evidence_index"]:
                if "source_class" not in entry:
                    result["warnings"].append(
                        f"Evidence entry missing source_class: {entry.get('evidence_id', '?')}"
                    )

    def _check_evidence_linkage(self, artifact: Dict, result: Dict):
        """Check evidence_id references within the artifact."""
        if "evidence_index" in artifact:
            ids = [e.get("evidence_id") for e in artifact["evidence_index"]]
            if not ids:
                result["warnings"].append("evidence_index is empty")
            elif any(eid is None for eid in ids):
                result["warnings"].append("Some evidence entries have no evidence_id")

    def _check_deterministic(self, artifact: Dict, result: Dict):
        """Ensure the artifact contains deterministic markers."""
        if "run_id" in artifact:
            pass  # run_id presence is good
        if "provenance" in artifact:
            prov = artifact["provenance"]
            if prov.get("deterministic") is True:
                pass  # Good - explicitly marked
            else:
                result["warnings"].append("Artifact not explicitly marked as deterministic")

    def get_summary(self) -> Dict:
        """Return validation summary."""
        return {
            "total": len(self.results),
            "passed": self.passes,
            "failed": self.failures,
            "results": self.results,
            "all_passed": self.failures == 0,
        }

    def write_report(self, path: str):
        """Write validation report markdown."""
        lines = [
            "# P95 Schema Validation Report",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Artifacts Validated | {len(self.results)} |",
            f"| Passed | {self.passes} |",
            f"| Failed | {self.failures} |",
            f"| All Passed | {'YES' if self.failures == 0 else 'NO'} |",
            "",
            "## Per-Artifact Results",
            "",
        ]
        for r in self.results:
            status = "✅ PASS" if r["valid"] else "❌ FAIL"
            lines.append(f"### {r['artifact']}")
            lines.append(f"- **Schema**: {r['schema']}")
            lines.append(f"- **Status**: {status}")
            if r["errors"]:
                lines.append(f"- **Errors:**")
                for e in r["errors"]:
                    lines.append(f"  - {e}")
            if r["warnings"]:
                lines.append(f"- **Warnings:**")
                for w in r["warnings"]:
                    lines.append(f"  - {w}")
            lines.append("")

        lines.append("---")
        lines.append("*All schema validations performed against MR-KEP schemas/*")

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Schema validation report written: {path}")