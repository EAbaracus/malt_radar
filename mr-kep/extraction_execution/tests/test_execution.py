import unittest
import os
import sys
import shutil

# Fix import: resolve to the extraction_execution directory unambiguously
_EXEC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _EXEC_DIR not in sys.path:
    sys.path.insert(0, _EXEC_DIR)
# Clear any cached 'engine' module that might point elsewhere
if 'engine' in sys.modules:
    del sys.modules['engine']
import engine as exec_engine
import checkpoints

class TestExecutionEngine(unittest.TestCase):
    def setUp(self):
        self.run_id = "test_run_001"
        checkpoints.clear_run(self.run_id)

    def tearDown(self):
        checkpoints.clear_run(self.run_id)

    def test_happy_path(self):
        e = exec_engine.ExecutionEngine(self.run_id)

        # Setup QUEUED requirements
        e.context = {
            "qualification_record": {
                "priority_gate": "Extract Normally",
                "candidate_id": "GSD-CAND-TEST"
            },
            "extraction_request": {"url": "http://test"},
            "extraction_result": {"smoky": 5.0, "sweet": 8.0, "null_field": None},
            "validation_report": {"gate": "PASS"}
        }

        final_state = e.run_to_completion()
        self.assertEqual(final_state, exec_engine.State.COMPLETED)

        # Verify Evidence bundle size (should only be 2 because null_field is None)
        ev_bundle = e.context.get("evidence_bundle")
        self.assertIsNotNone(ev_bundle)
        self.assertEqual(len(ev_bundle), 2)

        # Check generated evidence IDs
        self.assertTrue(ev_bundle[0]["fact_id"].startswith("EV-"))

    def test_checkpoint_resume(self):
        e1 = exec_engine.ExecutionEngine(self.run_id)

        e1.context = {
            "qualification_record": {
                "priority_gate": "Extract Normally",
                "candidate_id": "GSD-CAND-TEST"
            },
            "extraction_request": {"url": "http://test"}
        }

        # Step through to WAITING state
        e1.step() # to QUALIFIED
        e1.step() # to WAITING
        self.assertEqual(e1.state, exec_engine.State.WAITING)

        # Create a new engine and resume
        e2 = exec_engine.ExecutionEngine(self.run_id)
        e2.resume()

        # Should resume at WAITING with same context
        self.assertEqual(e2.state, exec_engine.State.WAITING)
        self.assertIn("extraction_request", e2.context)

    def test_transient_error_retry(self):
        e = exec_engine.ExecutionEngine(self.run_id)
        e.context = {
            "qualification_record": {
                "priority_gate": "Extract Normally",
                "candidate_id": "GSD-CAND-TEST"
            },
            "extraction_request": {"url": "http://test"},
            "simulate_transient_error": True,
            "extraction_result": {"smoky": 5.0},
            "validation_report": {"gate": "PASS"}
        }

        e.step() # QUEUED -> QUALIFIED
        e.step() # QUALIFIED -> WAITING
        e.step() # WAITING -> EXTRACTING
        e.step() # EXTRACTING (simulates error, clears flag, goes to RETRY_PENDING)
        self.assertEqual(e.state, exec_engine.State.RETRY_PENDING)

        e.step() # WAITING (retry 1)
        self.assertEqual(e.state, exec_engine.State.WAITING)

        final_state = e.run_to_completion()
        self.assertEqual(final_state, exec_engine.State.COMPLETED)

    def test_rollback(self):
        e = exec_engine.ExecutionEngine(self.run_id)
        e.context = {
            "qualification_record": {
                "priority_gate": "Extract Normally",
                "candidate_id": "GSD-CAND-TEST"
            },
            "extraction_request": {"url": "http://test"},
            "extraction_result": {"smoky": 5.0},
        }

        e.step() # QUEUED -> QUALIFIED
        e.step() # QUALIFIED -> WAITING (Checkpoint saved)
        e.step() # WAITING -> EXTRACTING

        e.rollback()
        self.assertEqual(e.state, exec_engine.State.WAITING)

if __name__ == '__main__':
    unittest.main()