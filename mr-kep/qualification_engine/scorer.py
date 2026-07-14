"""
Scorer (M3) - MR-KEP Qualification Engine
Computes 0-100 deterministic score based on 10 weighted factors.
"""

from typing import Dict, Any
from . import config

def score(attributes: Dict[str, Any], profile_overrides: Dict[str, Any] = None) -> int:
    """
    Computes a deterministic score from 0-100.
    attributes comes from config.DOCUMENT_CLASSES
    profile_overrides can optionally override ocr_quality, license_risk, etc.
    """
    if profile_overrides is None:
        profile_overrides = {}
        
    def get_val(key, default=0.0):
        if key in profile_overrides and profile_overrides[key] is not None:
            return profile_overrides[key]
        return attributes.get(key, default)
        
    auth_tier = get_val("authority_tier", config.TIER_T3)
    auth_factor = config.AUTHORITY_FACTORS.get(auth_tier, 0.2)
    
    # Base factors
    density = get_val("metadata_density", 0.0)
    complexity = get_val("extraction_complexity", 1.0) # We store complexity directly
    complexity_inv = 1.0 - complexity
    
    hist_val = get_val("historical_value", 0.0)
    flavor_val = get_val("flavor_usefulness", 0.0)
    identity_val = get_val("identity_usefulness", 0.0)
    
    noise = get_val("expected_noise", 1.0)
    noise_inv = 1.0 - noise
    
    license_risk = get_val("license_risk", 1.0)
    license_inv = 1.0 - license_risk
    
    ocr_quality = get_val("ocr_quality", 0.0)
    
    ev_count = get_val("expected_evidence_count", 0)
    ev_factor = min(ev_count / 12.0, 1.0)
    
    w = config.SCORE_WEIGHTS
    
    total = (
        auth_factor * w["authority"] +
        density * w["metadata_density"] +
        complexity_inv * w["extraction_complexity"] +
        hist_val * w["historical_value"] +
        flavor_val * w["flavor_usefulness"] +
        identity_val * w["identity_usefulness"] +
        noise_inv * w["expected_noise"] +
        license_inv * w["license_risk"] +
        ocr_quality * w["ocr_quality"] +
        ev_factor * w["expected_evidence_count"]
    )
    
    return int(round(100.0 * total))
