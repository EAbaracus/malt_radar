"""
RecordEmitter (M7) - MR-KEP Qualification Engine
"""

import json
import os
import jsonschema
from typing import Dict, Any, List
from datetime import datetime, timezone

def load_schema(schema_path: str) -> Dict[str, Any]:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def emit(
    source_key: str, 
    units: List[Dict[str, Any]], 
    schema_path: str = None
) -> Dict[str, Any]:
    """
    Assembles the qualification record and validates it.
    """
    
    in_scope_count = sum(1 for u in units if u["decision"] == "in_scope")
    out_of_scope_count = sum(1 for u in units if u["decision"] == "out_of_scope")
    deferred_count = sum(1 for u in units if u["decision"] == "deferred")
    
    record = {
        "schema_version": "1.0.0",
        "source_key": source_key,
        "qualified_at": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "engine": "P67-Qualification-Engine-v1",
            "deterministic": True
        },
        "units": units,
        "summary": {
            "in_scope": in_scope_count,
            "out_of_scope": out_of_scope_count,
            "deferred": deferred_count
        }
    }
    
    if schema_path and os.path.exists(schema_path):
        schema = load_schema(schema_path)
        jsonschema.validate(instance=record, schema=schema)
        
    return record
