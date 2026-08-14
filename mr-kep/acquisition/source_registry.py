import json
import os

class SourceRegistry:
    def __init__(self, registry_file="registry.json"):
        self.registry_file = registry_file
        self.sources = {
            "whiskybase": {
                "source_id": "whiskybase",
                "authority_tier": "T1_authoritative",
                "source_type": "database",
                "crawl_frequency": "weekly",
                "robots_policy": "respect",
                "rate_limit": "2/sec",
                "parser": "whiskybase_html_parser",
                "evidence_confidence": 0.95,
                "incremental_support": True,
                "authentication_requirements": "none",
                "estimated_token_cost": 400
            },
            "masterofmalt": {
                "source_id": "masterofmalt",
                "authority_tier": "T2_retailer",
                "source_type": "retailer",
                "crawl_frequency": "daily",
                "robots_policy": "respect",
                "rate_limit": "1/sec",
                "parser": "mom_html_parser",
                "evidence_confidence": 0.85,
                "incremental_support": True,
                "authentication_requirements": "none",
                "estimated_token_cost": 600
            },
            "reddit_scotch": {
                "source_id": "reddit_scotch",
                "authority_tier": "T3_community",
                "source_type": "forum",
                "crawl_frequency": "hourly",
                "robots_policy": "respect",
                "rate_limit": "30/min",
                "parser": "reddit_api_parser",
                "evidence_confidence": 0.50,
                "incremental_support": True,
                "authentication_requirements": "oauth2",
                "estimated_token_cost": 1200
            },
            "meleklerinpayi": {
                "source_id": "meleklerinpayi",
                "authority_tier": "T2_expert",
                "source_type": "editorial_blog",
                "language": "tr",
                "license": "copyright-attribution-required",
                "crawl_frequency": "weekly",
                "robots_policy": "respect",
                "rate_limit": "20/min",
                "parser": "meleklerinpayi_adapter",
                "evidence_confidence": 0.85,
                "incremental_support": True,
                "authentication_requirements": "none",
                "estimated_token_cost": 300
            }
        }
        self.save()
        
    def save(self):
        with open(self.registry_file, "w") as f:
            json.dump(self.sources, f, indent=2)
