"""
Classifier (M2) - MR-KEP Qualification Engine
Assigns exactly one of the 12 classes based on surface signals.
"""

from typing import Dict, Any
from urllib.parse import urlparse
from . import config

def classify(surface_signals: Dict[str, Any]) -> str:
    """
    Classify the document into exactly one of the 12 classes based on surface signals.
    Tie-breaking: Returns the lowest priority class (fail-safe toward caution) if multiple match, 
    but rules should be distinct.
    If no match, returns CLASS_UNKNOWN.
    
    Signals expected:
    - url: str
    - mime_type: str
    - filename: str
    - has_isbn: bool
    - has_issn: bool
    - is_gov_domain: bool
    - is_producer_domain: bool
    - is_brand_domain: bool
    - is_auction_domain: bool
    - is_blog_domain: bool
    - has_doi: bool
    - is_structured_export: bool
    """
    url = surface_signals.get("url", "").lower()
    mime = surface_signals.get("mime_type", "").lower()
    filename = surface_signals.get("filename", "").lower()
    
    # Check Scanned Document first
    if mime.startswith("image/") or "scan" in filename:
        return config.CLASS_SCANNED_DOCUMENT
        
    # Database Dump
    if any(ext in filename for ext in [".csv", ".sql", ".json"]):
        return config.CLASS_DATABASE_DUMP
        
    # Archived Snapshot
    if urlparse(url).netloc == "web.archive.org":
        return config.CLASS_ARCHIVED_SNAPSHOT
        
    # Review Website Export
    if surface_signals.get("is_structured_export"):
        return config.CLASS_REVIEW_WEBSITE_EXPORT
        
    # Book
    if surface_signals.get("has_isbn"):
        return config.CLASS_BOOK
        
    # Magazine
    if surface_signals.get("has_issn"):
        return config.CLASS_MAGAZINE
        
    # Research Paper
    if surface_signals.get("has_doi"):
        return config.CLASS_RESEARCH_PAPER
        
    # PDF based logic
    is_pdf = mime == "application/pdf" or filename.endswith(".pdf")
    
    if is_pdf:
        if surface_signals.get("is_gov_domain"):
            return config.CLASS_OFFICIAL_PDF
        if surface_signals.get("is_producer_domain"):
            return config.CLASS_PRODUCT_SHEET
        if surface_signals.get("is_brand_domain"):
            return config.CLASS_MARKETING_BROCHURE
        if surface_signals.get("is_auction_domain"):
            return config.CLASS_AUCTION_CATALOGUE
            
    # Blog Article
    if surface_signals.get("is_blog_domain") or "rss" in url:
        return config.CLASS_BLOG_ARTICLE
        
    return config.CLASS_UNKNOWN
