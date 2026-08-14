"""
Gates (M4, M5) - MR-KEP Qualification Engine
OverrideResolver and GateRunner.
"""

from typing import Dict, Any, Tuple
from . import config

def run_gates(doc_id: str, doc_class: str, score: int, attributes: Dict[str, Any], profile_overrides: Dict[str, Any] = None) -> Tuple[str, str]:
    """
    Runs gates G0-G5 and hard overrides.
    Returns (gate, reason)
    """
    if profile_overrides is None:
        profile_overrides = {}
        
    def get_val(key, default=None):
        if key in profile_overrides and profile_overrides[key] is not None:
            return profile_overrides[key]
        return attributes.get(key, default)

    # G0 - Existence & Integrity
    if not doc_id:
        return config.GATE_REJECT, "G0 fail: document_id missing or blank"
        
    # G1 - Classifiability
    if doc_class == config.CLASS_UNKNOWN:
        return config.GATE_REJECT, "G1 fail: unknown document class"

    license_risk = get_val("license_risk", 1.0)
    auth_tier = get_val("authority_tier", config.TIER_T3)
    identity_use = get_val("identity_usefulness", 0.0)
    ocr_need = get_val("ocr_need", False)
    ocr_quality = get_val("ocr_quality", 0.0)
    has_text_layer = profile_overrides.get("has_text_layer", False)
    
    # Overrides / Pre-score Gates
    
    # G2 - License Risk
    if license_risk >= 1.0:
        return config.GATE_REJECT, "G2 override: license_risk == 1.0"
        
    # G3 - Authority Worthiness
    if auth_tier == config.TIER_T3 and identity_use < 0.2:
        return config.GATE_REJECT, "G3 override: T3 source with identity_usefulness < 0.2"
        
    # G4 - OCR Readiness Gate (blocking)
    ocr_blocked = False
    if ocr_need:
        if not (has_text_layer or ocr_quality > 0.0):
            ocr_blocked = True
            
    # G2 Archive Only check (license_risk >= 0.6)
    license_archive = license_risk >= 0.6
    
    # G5 - Score Thresholds
    base_gate = config.GATE_REJECT
    reason = f"G5: Score {score}"
    
    if score >= 80:
        base_gate = config.GATE_HIGH_PRIORITY
    elif score >= 60:
        base_gate = config.GATE_EXTRACT_NORMALLY
    elif score >= 45:
        base_gate = config.GATE_EXTRACT_LATER
    elif score >= 25:
        base_gate = config.GATE_ARCHIVE_ONLY
    else:
        base_gate = config.GATE_REJECT
        
    # Apply blocking rules that downgrade the base gate
    if base_gate in [config.GATE_HIGH_PRIORITY, config.GATE_EXTRACT_NORMALLY, config.GATE_EXTRACT_LATER]:
        if ocr_blocked:
            return config.GATE_ARCHIVE_ONLY, "G4 block: OCR needed but quality is 0 and no text layer"
        if license_archive:
            return config.GATE_ARCHIVE_ONLY, f"G2 limit: license_risk {license_risk} forces Archive Only"
            
    return base_gate, reason
