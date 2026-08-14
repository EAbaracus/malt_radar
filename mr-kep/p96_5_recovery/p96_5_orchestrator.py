import json
from db_connector import DBConnector
from noise_filter import NoiseFilter
from ner_resolver import NERResolver

class P96_5_Orchestrator:
    def __init__(self, db_path):
        self.db = DBConnector(db_path)
        print("Loading DB Lexicon...")
        self.lexicon = self.db.load_lexicon()
        print(f"Loaded {len(self.lexicon)} canonical names.")
        self.filter = NoiseFilter()
        self.resolver = NERResolver(self.lexicon)
        
    def process(self, consensus_data):
        repaired = []
        unresolved = []
        false_positives = []
        
        stats = {
            "total_raw": len(consensus_data),
            "false_positives_caught": 0,
            "resolved_entities": 0,
            "unresolved_queued": 0
        }
        
        for entity in consensus_data:
            key = entity.get("entity_key", "")
            
            # 1. Noise Filter (Headers, OCR, generic words)
            if self.filter.is_noise(key):
                false_positives.append({"entity_key": key, "reason": "Noise Filter Triggered"})
                stats["false_positives_caught"] += 1
                continue
                
            # 2. NER Resolution against DB
            w_id, match_type = self.resolver.resolve(key)
            if w_id:
                # Successfully mapped a whisky entity
                entity["whisky_id"] = w_id
                entity["match_type"] = match_type
                repaired.append(entity)
                stats["resolved_entities"] += 1
            else:
                # Valid string, but no matching DB whisky found
                unresolved.append({"entity_key": key, "reason": "Not found in production.db"})
                stats["unresolved_queued"] += 1
                
        return repaired, unresolved, false_positives, stats
