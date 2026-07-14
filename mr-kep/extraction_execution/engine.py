import logging
from enum import Enum
from extraction_execution import checkpoints
from extraction_execution import evidence

logger = logging.getLogger(__name__)

class State(Enum):
    QUEUED = "Queued"
    QUALIFIED = "Qualified"
    WAITING = "Waiting"
    EXTRACTING = "Extracting"
    EVIDENCE_RECORDING = "Evidence Recording"
    VALIDATION = "Validation"
    CERTIFICATION_READY = "Certification Ready"
    COMPLETED = "Completed"
    REJECTED = "Rejected"
    FAILED = "Failed"
    RETRY_PENDING = "Retry Pending"
    ROLLED_BACK = "Rolled Back"

class ExecutionEngine:
    """Deterministic P68 Execution Engine."""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.state = State.QUEUED
        self.context = {}
        self.retries = 0
        self.max_retries = 3

    def _save_checkpoint(self):
        checkpoints.save_checkpoint(self.run_id, self.state.value, self.context)

    def _load_checkpoint(self, state: State) -> bool:
        data = checkpoints.load_checkpoint(self.run_id, state.value)
        if data:
            if not checkpoints.verify_checksum(data):
                raise ValueError("Checkpoint checksum failed verification!")
            self.context = data
            return True
        return False

    def resume(self):
        """HERMES resume rule: load last verified checkpoint."""
        for state in reversed(list(State)):
            if self._load_checkpoint(state):
                self.state = state
                return
        self.state = State.QUEUED

    def rollback(self):
        """Rollback to pre-Extracting (WAITING) state."""
        self.state = State.ROLLED_BACK
        if self._load_checkpoint(State.WAITING):
            self.state = State.WAITING
        else:
            self.state = State.FAILED

    def step(self) -> State:
        """Run a single state transition deterministically."""
        
        if self.state == State.QUEUED:
            # Transition to Qualified
            if self.context.get("qualification_record"):
                self.state = State.QUALIFIED
            else:
                self.state = State.REJECTED
                
        elif self.state == State.QUALIFIED:
            gate = self.context["qualification_record"].get("priority_gate")
            if gate in ["High Priority", "Extract Normally", "Extract Later"]:
                self.state = State.WAITING
            else:
                self.state = State.REJECTED
                
        elif self.state == State.WAITING:
            if self.context.get("extraction_request"):
                self.state = State.EXTRACTING
            else:
                self.state = State.FAILED
                
        elif self.state == State.EXTRACTING:
            if self.context.get("simulate_transient_error"):
                self.context["simulate_transient_error"] = False # clear it
                self.state = State.RETRY_PENDING
            elif self.context.get("extraction_result"):
                self.state = State.EVIDENCE_RECORDING
            else:
                self.state = State.FAILED
                
        elif self.state == State.EVIDENCE_RECORDING:
            try:
                candidate_id = self.context["qualification_record"]["candidate_id"]
                result = self.context["extraction_result"]
                # Read source info from extraction request
                req = self.context.get("extraction_request", {})
                auth_tier = req.get("authority_tier", "T3_community")
                ev_type = req.get("evidence_type", "inferred")
                src_key = req.get("source_key", "unknown")
                src_url = req.get("url", "")
                
                ev_bundle = evidence.process_extraction_result(
                    candidate_id, result, auth_tier, ev_type, src_key, src_url
                )
                self.context["evidence_bundle"] = ev_bundle
                self.state = State.VALIDATION
            except Exception as e:
                logger.error(f"Ledger error: {e}")
                self.rollback()
                return self.state
                
        elif self.state == State.VALIDATION:
            report = self.context.get("validation_report", {})
            gate = report.get("gate")
            if gate in ["PASS", "PARTIAL"]:
                self.state = State.CERTIFICATION_READY
            elif gate == "FAIL":
                if report.get("recoverable"):
                    self.state = State.RETRY_PENDING
                else:
                    self.state = State.FAILED
            else:
                self.state = State.FAILED
                
        elif self.state == State.CERTIFICATION_READY:
            self.context["certification_bundle"] = {
                "evidence": self.context["evidence_bundle"],
                "report": self.context["validation_report"]
            }
            self.state = State.COMPLETED
            
        elif self.state == State.RETRY_PENDING:
            if self.retries < self.max_retries:
                self.retries += 1
                self.state = State.WAITING
            else:
                self.state = State.FAILED

        # Save checkpoint after every successful transition if it's a checkpoint state
        checkpoint_states = [State.QUALIFIED, State.WAITING, State.EXTRACTING, 
                             State.EVIDENCE_RECORDING, State.VALIDATION, State.CERTIFICATION_READY]
        if self.state in checkpoint_states:
            self._save_checkpoint()
            
        return self.state

    def run_to_completion(self):
        terminal_states = {State.COMPLETED, State.REJECTED, State.FAILED, State.ROLLED_BACK}
        while self.state not in terminal_states:
            prev = self.state
            self.step()
            if self.state == prev: # prevent infinite loops if stuck
                break
        return self.state
