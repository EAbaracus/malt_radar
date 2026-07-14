import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IncrementalExtractor:
    """
    P91.1 Incremental Extractor
    Wraps standard extraction logic to only output evidence deltas, 
    preventing full dataset rebuilds when crawling new information.
    """
    
    def __init__(self, existing_evidence_path: Optional[str] = None):
        self.existing_evidence_path = existing_evidence_path
        self.existing_evidence = self._load_existing_evidence()
        
    def _load_existing_evidence(self) -> Dict[str, Dict[str, Any]]:
        """Loads existing evidence by entity_id + field_name to detect deltas."""
        evidence_map = {}
        if not self.existing_evidence_path:
            return evidence_map
            
        try:
            with open(self.existing_evidence_path, 'r', encoding='utf-8') as f:
                for line in f:
                    record = json.loads(line)
                    # Unique key for an evidence record
                    key = f"{record.get('candidate_id')}_{record.get('field_name')}_{record.get('source_url', 'unknown')}"
                    evidence_map[key] = record
        except FileNotFoundError:
            logger.warning(f"Existing evidence file {self.existing_evidence_path} not found. Starting fresh.")
            
        return evidence_map
        
    def extract_delta(self, entity_id: str, source_url: str, new_extractions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw new extractions from the base extractor and filters out 
        anything that already exists exactly in the historical evidence.
        """
        delta = {}
        
        for field_name, extraction_data in new_extractions.items():
            key = f"{entity_id}_{field_name}_{source_url}"
            
            existing = self.existing_evidence.get(key)
            if existing:
                # Compare the extracted value and confidence
                # If they match, this is not a delta, skip it
                if (str(existing.get('field_value')) == str(extraction_data.get('value')) and
                    existing.get('confidence') == extraction_data.get('confidence')):
                    continue
                    
            # If not skipped, it's new or updated evidence
            delta[field_name] = extraction_data
            
        return delta
