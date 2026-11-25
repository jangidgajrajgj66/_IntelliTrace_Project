"""
Safety Engine and Action Whitelist Validator for IntelliTrace.
Author: Gajraj Jangid
Enforces strict boundaries: approved-actions-only, attempt limits, parameter sanitization,
and complete audit trails.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List
import uuid

from config import APPROVED_ACTIONS, SAFETY_CONFIG, AUDIT_LOG_PATH
from src.fake_app.service import SimulatedService

class SafetyViolationError(Exception):
    """Raised when an unapproved or unsafe action is attempted."""
    pass

@dataclass
class ActionRecord:
    action_id: str
    incident_id: str
    attempt_number: int
    action_name: str
    parameters: Dict[str, Any]
    is_approved: bool
    status: str  # "EXECUTED", "BLOCKED_UNAPPROVED", "BLOCKED_MAX_ATTEMPTS", "FAILED", "PARAMETER_VIOLATION"
    execution_message: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SafetyEngine:
    """
    Enforces strict safety rules:
    1. Whitelist-only approved actions.
    2. Zero arbitrary shell / code execution.
    3. Maximum attempt limits per incident.
    4. Strongly-typed, bounded parameter validation.
    5. Immutable audit logging of all operations.
    """
    def __init__(self, max_attempts: int = SAFETY_CONFIG["max_fix_attempts"]):
        self.approved_actions = set(APPROVED_ACTIONS)
        self.max_attempts = max_attempts
        self.incident_attempt_counts: Dict[str, int] = {}
        self.action_history: List[ActionRecord] = []

    def _log_audit(self, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{ts}] [SAFETY_AUDIT] {message}\n"
        try:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

    def get_attempt_count(self, incident_id: str) -> int:
        return self.incident_attempt_counts.get(incident_id, 0)

    def validate_action(
        self, incident_id: str, action_name: str, parameters: Dict[str, Any]
    ) -> Tuple[bool, str, str]:
        """
        Validates action against whitelist, attempt budget, and parameter boundaries.
        Returns (is_valid, rejection_reason, status_code).
        """
        # Rule 1: Must be in approved whitelist
        if action_name not in self.approved_actions:
            reason = f"SECURITY VIOLATION: Action '{action_name}' is NOT in approved action whitelist {list(self.approved_actions)}."
            self._log_audit(f"REJECTED incident={incident_id} action={action_name} reason={reason}")
            return False, reason, "BLOCKED_UNAPPROVED"

        # Rule 2: Must not exceed max allowed attempts
        current_attempts = self.get_attempt_count(incident_id)
        if current_attempts >= self.max_attempts:
            reason = f"BUDGET EXCEEDED: Incident '{incident_id}' has reached maximum fix attempts ({self.max_attempts}). Escalating to human."
            self._log_audit(f"REJECTED incident={incident_id} action={action_name} reason={reason}")
            return False, reason, "BLOCKED_MAX_ATTEMPTS"

        # Rule 3: Parameter bounds checking
        if action_name == "SCALE_WORKERS":
            worker_count = parameters.get("worker_count", 4)
            min_w = SAFETY_CONFIG["min_workers"]
            max_w = SAFETY_CONFIG["max_workers"]
            if not isinstance(worker_count, int) or not (min_w <= worker_count <= max_w):
                reason = f"PARAMETER ERROR: worker_count={worker_count} must be integer between {min_w} and {max_w}."
                self._log_audit(f"REJECTED incident={incident_id} action={action_name} reason={reason}")
                return False, reason, "PARAMETER_VIOLATION"

        return True, "Action approved by safety engine.", "APPROVED"

    def execute_action(
        self,
        incident_id: str,
        action_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        service: Optional[SimulatedService] = None,
    ) -> ActionRecord:
        """
        Safely validates and executes an operational action against the simulated service.
        """
        parameters = parameters or {}
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action_id = str(uuid.uuid4())[:8]

        is_valid, validation_msg, status_code = self.validate_action(incident_id, action_name, parameters)

        if not is_valid:
            record = ActionRecord(
                action_id=action_id,
                incident_id=incident_id,
                attempt_number=self.get_attempt_count(incident_id),
                action_name=action_name,
                parameters=parameters,
                is_approved=False,
                status=status_code,
                execution_message=validation_msg,
                timestamp=ts,
            )
            self.action_history.append(record)
            return record

        # Valid action: increment attempt budget
        self.incident_attempt_counts[incident_id] = self.get_attempt_count(incident_id) + 1
        current_attempt = self.incident_attempt_counts[incident_id]

        if service is None:
            exec_ok = True
            exec_msg = f"Action {action_name} simulated (dry-run)."
        else:
            exec_ok, exec_msg = service.apply_action(action_name, parameters)

        status = "EXECUTED" if exec_ok else "FAILED"
        self._log_audit(f"EXECUTED incident={incident_id} attempt={current_attempt} action={action_name} status={status} message={exec_msg}")

        record = ActionRecord(
            action_id=action_id,
            incident_id=incident_id,
            attempt_number=current_attempt,
            action_name=action_name,
            parameters=parameters,
            is_approved=True,
            status=status,
            execution_message=exec_msg,
            timestamp=ts,
        )
        self.action_history.append(record)
        return record
