"""
PipelineSelector and YieldEstimator (M6) - MR-KEP Qualification Engine
"""

from typing import Dict, Any, List, Tuple
from . import config

def select_pipeline(doc_class: str, attributes: Dict[str, Any]) -> List[str]:
    """
    Select recommended pipeline stages based on class and attributes.
    """
    pipeline = ["detect_type", "qualify"]
    
    ocr_need = attributes.get("ocr_need", False)
    if ocr_need:
        pipeline.append("ocr_gate")
        
    extract_strategy = []
    
    # Base strategy based on class
    if doc_class in [config.CLASS_BOOK, config.CLASS_ARCHIVED_SNAPSHOT, config.CLASS_BLOG_ARTICLE]:
        extract_strategy.append("prose")
    elif doc_class in [config.CLASS_OFFICIAL_PDF, config.CLASS_PRODUCT_SHEET]:
        extract_strategy.append("structured")
    elif doc_class == config.CLASS_MARKETING_BROCHURE:
        extract_strategy.append("text")
    elif doc_class == config.CLASS_AUCTION_CATALOGUE:
        extract_strategy.append("table")
    elif doc_class in [config.CLASS_MAGAZINE, config.CLASS_RESEARCH_PAPER]:
        extract_strategy.append("prose")
    elif doc_class == config.CLASS_REVIEW_WEBSITE_EXPORT:
        extract_strategy.append("structured_parse")
    elif doc_class == config.CLASS_DATABASE_DUMP:
        extract_strategy.append("structured/tabular")
    elif doc_class == config.CLASS_SCANNED_DOCUMENT:
        # P67 says "depends on OCR output", we'll just say extract
        pass

    table_prob = attributes.get("table_likelihood", 0.0)
    if table_prob >= 0.6 and "table" not in extract_strategy and "structured/tabular" not in extract_strategy and "structured" not in extract_strategy:
        extract_strategy.append("table")
        
    image_prob = attributes.get("image_usefulness", 0.0)
    if image_prob >= 0.6 and "image_caption" not in extract_strategy:
        extract_strategy.append("image_caption")
        
    if len(extract_strategy) > 0:
        pipeline.append(f"extract({'+'.join(extract_strategy)})")
    else:
        pipeline.append("extract")
        
    pipeline.append("normalize")
    pipeline.append("evidence_ledger")
    
    # Specific validation targets based on class (e.g. Wayback source, T3)
    if doc_class == config.CLASS_ARCHIVED_SNAPSHOT:
        pipeline.append("validate (Wayback source)")
    elif doc_class == config.CLASS_BLOG_ARTICLE:
        pipeline.append("validate (T3)")
    else:
        pipeline.append("validate")
        
    return pipeline

def estimate_yield(doc_class: str, attributes: Dict[str, Any]) -> Tuple[List[str], float, str]:
    """
    Returns (expected_fields, confidence_before_extraction, estimated_cost)
    """
    expected_fields = config.EXPECTED_FIELDS.get(doc_class, [])
    
    auth_tier = attributes.get("authority_tier", config.TIER_T3)
    auth_factor = config.AUTHORITY_FACTORS.get(auth_tier, 0.2)
    
    if doc_class == config.CLASS_DATABASE_DUMP:
        auth_factor = 0.9  # P65 special case for T2 structured
        
    density = attributes.get("metadata_density", 0.0)
    confidence = auth_factor * density
    
    # Cost estimation
    cost_units = 0
    if attributes.get("ocr_need", False):
        cost_units += 1
    if attributes.get("table_likelihood", 0.0) >= 0.6:
        cost_units += 1
    if attributes.get("extraction_complexity", 0.0) >= 0.6:
        cost_units += 1
        
    if cost_units == 0:
        cost = "Low"
    elif cost_units == 1:
        cost = "Medium"
    else:
        cost = "High"
        
    return expected_fields, round(confidence, 2), cost
