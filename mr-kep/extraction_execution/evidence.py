import hashlib
from datetime import datetime, timezone
import json

def generate_evidence_id(candidate_id: str, field_name: str, value: any) -> str:
    """Generate a deterministic EV- id based on SHA-256."""
    val_str = str(value) if value is not None else "null"
    raw = f"{candidate_id}:{field_name}:{val_str}"
    h = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f"EV-{h[:12]}"

def create_evidence_record(candidate_id: str, field_name: str, value: any,
                           authority_tier: str, evidence_type: str, 
                           source_key: str, source_url: str, quote: str,
                           confidence: float = 1.0) -> dict:
    """Creates an immutable P64 evidence record for a non-null field."""
    fact_id = generate_evidence_id(candidate_id, field_name, value)
    
    # Compute P64-compliant deterministic evidence_id
    raw_str = f"{candidate_id}{fact_id}{source_url or ''}{quote or ''}"
    ev_hash = hashlib.sha256(raw_str.encode('utf-8')).hexdigest()
    evidence_id = f"EV-{ev_hash[:16]}"
    
    return {
        "schema_version": "1.0.0",
        "evidence_id": evidence_id,
        "fact_id": fact_id,
        "field": field_name,
        "field_name": field_name,
        "value": value,
        "field_value": value,
        "confidence": confidence,
        "authority_tier": authority_tier,
        "sources": [
            {
                "source_key": source_key,
                "source_url": source_url,
                "quote": quote,
                "evidence_type": evidence_type,
                "won": True
            }
        ]
    }

def process_extraction_result(candidate_id: str, extraction_result: dict, 
                              authority_tier: str, evidence_type: str,
                              source_key: str, source_url: str) -> list:
    """
    Takes a draft extraction result and generates an evidence bundle.
    Only non-null fields get an evidence record.
    Expects extraction_result to be a dict of dicts:
    {
      "field_name": {
        "value": <val>,
        "quote": <str>,
        "confidence": <float>
      }
    }
    """
    evidence_bundle = []
    
    for field, data in extraction_result.items():
        if data and data.get("value") is not None:
            record = create_evidence_record(
                candidate_id=candidate_id,
                field_name=field,
                value=data["value"],
                authority_tier=authority_tier,
                evidence_type=evidence_type,
                source_key=source_key,
                source_url=source_url,
                quote=data.get("quote", ""),
                confidence=data.get("confidence", 1.0)
            )
            evidence_bundle.append(record)
            
    return evidence_bundle
