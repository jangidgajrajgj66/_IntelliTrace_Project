"""
IntelliTrace Workflow Loop Orchestrator powered by LangGraph.
Author: Gajraj Jangid
Coordinates the 5 operational stations:
1. Detect -> 2. Investigate (LLM) -> 3. Safety -> 4. Fix -> 5. Verify -> 6. Escalate / Resolve.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
import time
import uuid
from typing import Dict, Any, Optional, List

from config import SAFETY_CONFIG
from src.utils.logger import get_logger
from src.fake_app.service import SimulatedService
from src.fake_app.scenarios import SCENARIOS
from src.monitor.detector import IncidentDetector, Alert
from src.investigator.cause_finder import RootCauseFinder, InvestigationReport
from src.investigator.llm_investigator import LLMInvestigator, LLMInvestigationResult
from src.investigator.explainer import Explainer
from src.safety.safety_engine import SafetyEngine, ActionRecord
from src.storage.repository import IncidentRepository
from src.workflow.graph import build_incident_graph, IncidentWorkflowState

logger = get_logger("workflow.loop")

@dataclass
class IncidentLifecycleResult:
    incident_id: str
    scenario_id: str
    title: str
    status: str  # "RESOLVED", "ESCALATED", "HEALTHY"
    detected_at: str
    resolved_at: Optional[str]
    root_cause: str
    severity: str
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    before_metrics: Dict[str, Any] = field(default_factory=dict)
    after_metrics: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    human_handover_notes: Optional[str] = None
    timeline: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AutonomousInvestigator:
    """
    IntelliTrace Autonomous SRE Engine powered by LangGraph.
    Monitors services, triggers LLM-guided root cause investigation, applies safe
    remediations via strict safety policies, and escalates safely.
    """
    def __init__(
        self,
        service: Optional[SimulatedService] = None,
        detector: Optional[IncidentDetector] = None,
        cause_finder: Optional[RootCauseFinder] = None,
        explainer: Optional[Explainer] = None,
        safety_engine: Optional[SafetyEngine] = None,
        repository: Optional[IncidentRepository] = None,
    ):
        self.service = service or SimulatedService()
        self.detector = detector or IncidentDetector()
        self.cause_finder = cause_finder or RootCauseFinder()
        self.explainer = explainer or Explainer()
        self.safety_engine = safety_engine or SafetyEngine()
        self.repository = repository or IncidentRepository()
        self.graph = build_incident_graph()

    def run_scenario(self, scenario_id: str) -> IncidentLifecycleResult:
        """
        Executes an end-to-end incident lifecycle using the LangGraph StateGraph.
        """
        start_ts = time.time()
        # Step 0: Fault Injection
        if scenario_id in SCENARIOS:
            self.service.inject_fault(scenario_id)
        else:
            raise ValueError(f"Unknown scenario_id: {scenario_id}")

        # Tick service to generate anomalous metrics
        for _ in range(2):
            self.service.tick()

        incident_id = f"INC-{int(time.time())}-{str(uuid.uuid4())[:4].upper()}"
        scenario_meta = SCENARIOS[scenario_id]
        before_metrics = self.service.get_metrics_df().iloc[-1].to_dict()

        # Initialize LangGraph State
        initial_state: IncidentWorkflowState = {
            "incident_id": incident_id,
            "scenario_id": scenario_id,
            "target_type": "simulated",
            "service_ref": self.service,
            "safety_ref": self.safety_engine,
            "metrics_snapshot": before_metrics,
            "alert_data": None,
            "is_healthy": True,
            "investigation_data": None,
            "current_action": None,
            "actions_taken": [],
            "attempt_count": 0,
            "max_attempts": SAFETY_CONFIG["max_fix_attempts"],
            "verification_passed": False,
            "status": "HEALTHY",
            "handover_notes": None,
            "timeline": [],
        }

        # Execute LangGraph Workflow
        logger.info(f"Invoking LangGraph incident state machine for {incident_id} ({scenario_id})")
        final_state = self.graph.invoke(initial_state)

        # Extract Results
        status = final_state.get("status", "HEALTHY")
        if final_state.get("verification_passed", False):
            status = "RESOLVED"
        elif status not in ["RESOLVED", "HEALTHY"]:
            status = "ESCALATED"

        inv_data = final_state.get("investigation_data") or {}
        root_cause = inv_data.get("root_cause", "None")
        explanation = inv_data.get("explanation_plain_text", "All metrics within nominal bounds.")
        handover = final_state.get("handover_notes")
        after_metrics = final_state.get("metrics_snapshot", {})
        actions_taken = final_state.get("actions_taken", [])
        timeline = final_state.get("timeline", [])

        result = IncidentLifecycleResult(
            incident_id=incident_id,
            scenario_id=scenario_id,
            title=scenario_meta.name,
            status=status,
            detected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            resolved_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "RESOLVED" else None,
            root_cause=root_cause,
            severity="CRITICAL" if status != "HEALTHY" else "OK",
            actions_taken=actions_taken,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            explanation=explanation,
            human_handover_notes=handover,
            timeline=timeline,
        )

        # Persist to database and sync to JSON repository
        self.repository.record_incident({
            "id": incident_id,
            "scenario_id": scenario_id,
            "title": scenario_meta.name,
            "status": status,
            "root_cause": root_cause,
            "severity": result.severity,
            "detection_timestamp": result.detected_at,
            "resolution_timestamp": result.resolved_at,
            "duration_seconds": round(time.time() - start_ts, 3),
            "before_metrics": before_metrics,
            "after_metrics": after_metrics,
            "explanation": explanation + (f"\n\n{handover}" if handover else ""),
        })

        for act in actions_taken:
            self.repository.record_action(act)

        return result


IntelliTraceEngine = AutonomousInvestigator
