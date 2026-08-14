"""
Tests for Qualification Engine (M10)
"""

import unittest
import os
import sys

# Adjust path to import qualification_engine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from qualification_engine import config, classifier, scorer, gates, strategy, emit, engine

class TestQualificationEngine(unittest.TestCase):

    def test_m2_classifier(self):
        # Book
        self.assertEqual(classifier.classify({"has_isbn": True}), config.CLASS_BOOK)
        # Official PDF
        self.assertEqual(classifier.classify({"mime_type": "application/pdf", "is_gov_domain": True}), config.CLASS_OFFICIAL_PDF)
        # Unknown
        self.assertEqual(classifier.classify({"mime_type": "text/html"}), config.CLASS_UNKNOWN)

    def test_m3_scorer_reproduces_p67_table(self):
        """
        Verify the scorer matches the worked class-score table in qualification_score_model.md exactly.
        """
        expected_scores = {
            config.CLASS_OFFICIAL_PDF: 79,
            config.CLASS_PRODUCT_SHEET: 77,
            config.CLASS_RESEARCH_PAPER: 70,
            config.CLASS_MAGAZINE: 66,
            config.CLASS_REVIEW_WEBSITE_EXPORT: 65,
            config.CLASS_DATABASE_DUMP: 65,
            config.CLASS_ARCHIVED_SNAPSHOT: 61,
            config.CLASS_MARKETING_BROCHURE: 59,
            config.CLASS_BOOK: 71,
            config.CLASS_AUCTION_CATALOGUE: 64,
            config.CLASS_BLOG_ARTICLE: 42,
            config.CLASS_SCANNED_DOCUMENT: 51
        }
        
        for doc_class, expected_score in expected_scores.items():
            attributes = config.DOCUMENT_CLASSES[doc_class]
            actual_score = scorer.score(attributes)
            self.assertEqual(actual_score, expected_score, f"Failed for {doc_class}: {actual_score} != {expected_score}")

    def test_m4_m5_gates(self):
        # High Priority Band (score=93) -> Official PDF
        attributes = config.DOCUMENT_CLASSES[config.CLASS_OFFICIAL_PDF]
        gate, reason = gates.run_gates("doc1", config.CLASS_OFFICIAL_PDF, 93, attributes)
        self.assertEqual(gate, config.GATE_HIGH_PRIORITY)
        
        # Override: License risk = 1.0 -> Reject
        gate, reason = gates.run_gates("doc1", config.CLASS_OFFICIAL_PDF, 93, attributes, {"license_risk": 1.0})
        self.assertEqual(gate, config.GATE_REJECT)
        
        # Scanned document (score=47, Extract Later normally, but ocr_quality=0 -> Archive Only)
        attributes_scan = config.DOCUMENT_CLASSES[config.CLASS_SCANNED_DOCUMENT]
        gate, reason = gates.run_gates("doc2", config.CLASS_SCANNED_DOCUMENT, 47, attributes_scan)
        self.assertEqual(gate, config.GATE_ARCHIVE_ONLY)
        self.assertIn("OCR needed", reason)

    def test_m6_strategy(self):
        # Book strategy
        attributes = config.DOCUMENT_CLASSES[config.CLASS_BOOK]
        pipeline = strategy.select_pipeline(config.CLASS_BOOK, attributes)
        self.assertIn("ocr_gate", pipeline)
        self.assertIn("extract(prose)", pipeline)
        
        expected_fields, confidence, cost = strategy.estimate_yield(config.CLASS_BOOK, attributes)
        self.assertIn("distillery_name", expected_fields)
        self.assertEqual(confidence, 0.56)  # T2 (0.7) * 0.80 density
        self.assertEqual(cost, "Medium")
        
    def test_m7_m8_engine(self):
        schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "schemas", "qualification.schema.json")
        
        units = [
            {
                "unit_id": "u1",
                "surface_signals": {"mime_type": "application/pdf", "is_gov_domain": True}
            },
            {
                "unit_id": "u2",
                "surface_signals": {"mime_type": "text/html"} # Unknown -> Reject
            }
        ]
        
        record = engine.run_batch("source_test", units, schema_path)
        
        self.assertEqual(record["summary"]["in_scope"], 1)
        self.assertEqual(record["summary"]["out_of_scope"], 1)
        self.assertEqual(record["summary"]["deferred"], 0)
        
        self.assertEqual(record["units"][0]["unit_id"], "u1")
        self.assertEqual(record["units"][0]["decision"], "in_scope")
        
        self.assertEqual(record["units"][1]["unit_id"], "u2")
        self.assertEqual(record["units"][1]["decision"], "out_of_scope")

if __name__ == "__main__":
    unittest.main()
