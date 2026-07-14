"""
Batch driver (M8, M9) - MR-KEP Qualification Engine
"""

from typing import Dict, Any, List
from . import config
from . import classifier
from . import scorer
from . import gates
from . import strategy
from . import emit
import hashlib

def run_batch(source_key: str, input_units: List[Dict[str, Any]], schema_path: str = None) -> Dict[str, Any]:
    """
    input_units: list of dicts with:
      - unit_id (or we compute it if missing?) The spec says:
        "document_id (deterministic hash of source_url|title|header-sha, P67 G0)"
        We expect the unit dict to provide these surface signals.
      - surface_signals
      - profile_overrides
    """
    
    # Sort deterministically by a provided key if possible, else just process in order.
    # The spec: "units processed in unit_id lexicographic order"
    
    # First, let's prepare the units with unit_ids
    prepared_units = []
    for u in input_units:
        surface = u.get("surface_signals", {})
        unit_id = u.get("unit_id")
        
        # If no unit_id, try to generate one per G0 rules if possible, but the input SHOULD have it.
        if not unit_id:
            raw_str = f"{surface.get('url','')}|{surface.get('title','')}|{surface.get('header_sha','')}"
            if raw_str != "||":
                unit_id = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()
                
        u["_unit_id_val"] = unit_id or ""
        prepared_units.append(u)
        
    prepared_units.sort(key=lambda x: x["_unit_id_val"])
    
    out_units = []
    
    for u in prepared_units:
        unit_id = u["_unit_id_val"]
        surface = u.get("surface_signals", {})
        overrides = u.get("profile_overrides", {})
        
        # M2: Classify
        doc_class = classifier.classify(surface)
        
        # M3: Score
        attributes = config.DOCUMENT_CLASSES.get(doc_class, {})
        if not attributes:
            # If doc_class is unknown, attributes is empty. Gate G1 will catch this.
            score = 0
        else:
            score = scorer.score(attributes, overrides)
            
        # M4, M5: Gates
        gate_result, reason = gates.run_gates(unit_id, doc_class, score, attributes, overrides)
        
        decision = config.GATE_TO_DECISION.get(gate_result, config.DECISION_OUT_OF_SCOPE)
        
        whisky_hint = surface.get("whisky_hint")
        
        unit_record = {
            "unit_id": unit_id,
            "decision": decision,
            "reason": reason
        }
        
        if whisky_hint:
            unit_record["whisky_hint"] = whisky_hint
            
        # If in_scope, we might want to attach recommended_pipeline, expected_fields etc.
        # But wait, schemas/qualification.schema.json units[] array only allows:
        # unit_id, decision, reason, whisky_hint
        # The extra info (pipeline, etc) is probably fed downstream but not part of the strict output schema's array elements per the provided JSON schema.
        # Let's check schemas/qualification.schema.json:
        # properties: unit_id, decision, reason, whisky_hint. additionalProperties: false.
        # So we MUST NOT add extra fields to the unit record.
        
        out_units.append(unit_record)
        
    record = emit.emit(source_key, out_units, schema_path)
    return record
