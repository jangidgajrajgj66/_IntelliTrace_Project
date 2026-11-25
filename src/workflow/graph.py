"""
LangGraph StateGraph Workflow Orchestrator for IntelliTrace.
Author: Gajraj Jangid
Implements the 5-station agent loop (Detect -> Investigate -> Safety -> Remediate -> Verify -> Escalate)
as an explicit, stateful, auditable LangGraph graph.
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END

from config import SAFETY_CONFIG, THRESHOLDS
from src.utils.logger import get_logger
from src.monitor.detector import IncidentDetector, Alert
from src.investigator.llm_investigator import LLMInvestigator, LLMInvestigationResult
from src.safety.safety_engine import SafetyEngine, ActionRecord
from src.fake_app.service import SimulatedService
from src.fake_app.scenarios import SCENARIOS
from src.storage.repository import IncidentRepository

logger = get_logger("workflow.graph")

class IncidentWorkflowState(TypedDict, total=False):
    """LangGraph state schema representing the full lifecycle of an incident."""
    incident_id: str
    scenario_id: str
    target_type: str  # "simulated" or "real_app"
    service_ref: Any
    safety_ref: Any
    metrics_snapshot: Dict[str, Any]
    alert_data: Optional[Dict[str, Any]]
    is_healthy: bool
    investigation_data: Optional[Dict[str, Any]]
    current_action: Optional[Dict[str, Any]]
    actions_taken: List[Dict[str, Any]]
    attempt_count: int
    max_attempts: int
    verification_passed: bool
    status: str  # "HEALTHY", "ALERTED", "INVESTIGATING", "REMEDIATING", "VERIFIED", "RESOLVED", "ESCALATED"
    handover_notes: Optional[str]
    timeline: List[Dict[str, Any]]

# --- Graph Node Implementations ---

def detect_node(state: IncidentWorkflowState) -> Dict[str, Any]:
    """Node 1: Evaluates telemetry against SLA thresholds and anomaly rules."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    service = state["service_ref"]
    detector = IncidentDetector()

    metrics_df = service.get_metrics_df()
    alert: Alert = detector.evaluate(metrics_df)

    latest_metrics = metrics_df.iloc[-1].to_dict() if not metrics_df.empty else {}

    timeline = list(state.get("timeline", []))
    timeline.append({
        "timestamp": ts,
        "station": "DETECT",
        "message": f"Evaluated telemetry. SLA Alert: {alert.is_alert} (Severity: {alert.severity})",
        "metrics": latest_metrics,
    })

    if not alert.is_alert:
        return {
            "metrics_snapshot": latest_metrics,
            "alert_data": None,
            "is_healthy": True,
            "status": "HEALTHY",
            "timeline": timeline,
        }

    logger.warning(f"SLA Breach detected for incident {state['incident_id']}: {alert.message}")
    return {
        "metrics_snapshot": latest_metrics,
        "alert_data": alert.to_dict(),
        "is_healthy": False,
        "status": "ALERTED",
        "timeline": timeline,
    }

def investigate_node(state: IncidentWorkflowState) -> Dict[str, Any]:
    """Node 2: Employs LLM reasoning and evidence correlation to deduce root cause."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    service = state["service_ref"]
    alert_dict = state["alert_data"]

    # Reconstruct Alert
    alert = Alert(
        is_alert=alert_dict["is_alert"],
        severity=alert_dict["severity"],
        message=alert_dict["message"],
        timestamp=alert_dict["timestamp"],
        metrics_snapshot=alert_dict["metrics_snapshot"]
    )

    metrics_df = service.get_metrics_df()
    recent_logs = service.get_recent_logs(25)

    investigator = LLMInvestigator()
    result: LLMInvestigationResult = investigator.investigate(
        incident_id=state["incident_id"],
        alert=alert,
        metrics_df=metrics_df,
        recent_logs=recent_logs,
    )

    timeline = list(state.get("timeline", []))
    timeline.append({
        "timestamp": ts,
        "station": "INVESTIGATE",
        "root_cause": result.root_cause,
        "confidence": result.confidence_score,
        "recommended_action": result.recommended_action,
        "explanation": result.explanation_plain_text,
    })

    logger.info(f"Root cause diagnosed by LLM: {result.root_cause} (Confidence: {result.confidence_score*100:.0f}%)")
    return {
        "investigation_data": result.model_dump(),
        "status": "INVESTIGATING",
        "timeline": timeline,
    }

def safety_eval_node(state: IncidentWorkflowState) -> Dict[str, Any]:
    """Node 3: Safety Guardrails evaluation (whitelist, attempt budget, parameters)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safety = state.get("safety_ref") or SafetyEngine(max_attempts=state["max_attempts"])
    inv = state["investigation_data"]
    attempts = state["attempt_count"]

    # Determine which action to run: primary on attempt 0, secondary on attempt 1
    if attempts == 0:
        action_name = inv["recommended_action"]
        params = inv.get("action_parameters", {})
    else:
        action_name = inv.get("secondary_action") or inv["recommended_action"]
        params = {}

    is_valid, reason, code = safety.validate_action(state["incident_id"], action_name, params)

    timeline = list(state.get("timeline", []))
    timeline.append({
        "timestamp": ts,
        "station": "SAFETY_EVAL",
        "action_name": action_name,
        "is_approved": is_valid,
        "status_code": code,
        "reason": reason,
    })

    if not is_valid:
        logger.warning(f"Action blocked by safety engine: {reason}")
        return {
            "current_action": {
                "action_name": action_name,
                "parameters": params,
                "is_approved": False,
                "rejection_reason": reason,
            },
            "timeline": timeline,
        }

    return {
        "current_action": {
            "action_name": action_name,
            "parameters": params,
            "is_approved": True,
            "rejection_reason": None,
        },
        "timeline": timeline,
    }

def remediate_node(state: IncidentWorkflowState) -> Dict[str, Any]:
    """Node 4: Dispatches approved safe action to the application service via SafetyEngine."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    service = state["service_ref"]
    safety = state.get("safety_ref")
    action_info = state["current_action"]
    action_name = action_info["action_name"]
    params = action_info["parameters"]

    new_attempt = state["attempt_count"] + 1

    if safety is not None:
        record = safety.execute_action(
            incident_id=state["incident_id"],
            action_name=action_name,
            parameters=params,
            service=service,
        )
        action_record = record.to_dict()
        exec_msg = record.execution_message
    else:
        exec_ok, exec_msg = service.apply_action(action_name, params)
        action_record = {
            "action_id": str(uuid.uuid4())[:8],
            "incident_id": state["incident_id"],
            "attempt_number": new_attempt,
            "action_name": action_name,
            "parameters": params,
            "is_approved": True,
            "status": "EXECUTED" if exec_ok else "FAILED",
            "execution_message": exec_msg,
            "timestamp": ts,
        }

    actions_taken = list(state.get("actions_taken", []))
    actions_taken.append(action_record)

    timeline = list(state.get("timeline", []))
    timeline.append({
        "timestamp": ts,
        "station": "REMEDIATE",
        "attempt": new_attempt,
        "action": action_name,
        "result": exec_msg,
    })

    logger.info(f"Remediation action {action_name} executed (Attempt {new_attempt}/{state['max_attempts']})")
    return {
        "attempt_count": new_attempt,
        "actions_taken": actions_taken,
        "status": "REMEDIATING",
        "timeline": timeline,
    }

def verify_node(state: IncidentWorkflowState) -> Dict[str, Any]:
    """Node 5: Waits for stabilization cycles and evaluates post-fix telemetry."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    service = state["service_ref"]
    detector = IncidentDetector()

    # Advance service simulation ticks to observe stabilization
    wait_cycles = SAFETY_CONFIG["verification_wait_cycles"]
    for _ in range(wait_cycles):
        service.tick()

    post_df = service.get_metrics_df()
    post_alert = detector.evaluate(post_df)
    latest_metrics = post_df.iloc[-1].to_dict() if not post_df.empty else {}

    is_recovered = not post_alert.is_alert

    timeline = list(state.get("timeline", []))
    timeline.append({
        "timestamp": ts,
        "station": "VERIFY",
        "recovered": is_recovered,
        "post_metrics": latest_metrics,
        "message": "SLA restored within nominal bounds." if is_recovered else f"SLA breach remains: {post_alert.message}",
    })

    logger.info(f"Verification station completed: Recovered={is_recovered}")
    return {
        "verification_passed": is_recovered,
        "metrics_snapshot": latest_metrics,
        "status": "RESOLVED" if is_recovered else "VERIFYING",
        "timeline": timeline,
    }

def escalate_node(state: IncidentWorkflowState) -> Dict[str, Any]:
    """Node 6: Synthesizes SRE Handover Dossier for human on-call engineer."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inv = state.get("investigation_data", {})
    metrics = state.get("metrics_snapshot", {})
    attempts = state.get("attempt_count", 0)

    handover = (
        f"🚨 CRITICAL SRE ESCALATION HANDOVER DOSSIER - ESCALATED TO HUMAN ON-CALL ENGINEER\n"
        f"====================================================\n"
        f"Incident ID:   {state['incident_id']}\n"
        f"Scenario:      {state.get('scenario_id', 'Unknown')}\n"
        f"Diagnosed Cause: {inv.get('root_cause', 'Unknown')}\n"
        f"Attempts Made: {attempts}/{state['max_attempts']}\n"
        f"Failure SLA:   Response Time={metrics.get('response_time_ms')}ms (Limit {THRESHOLDS['max_response_time_ms']}ms), "
        f"Error Rate={metrics.get('error_rate_pct')}% (Limit {THRESHOLDS['max_error_rate_pct']}%)\n"
        f"Recommendation: Automated actions were exhausted without SLA recovery. "
        f"Immediate human manual inspection required.\n"
    )

    timeline = list(state.get("timeline", []))
    timeline.append({
        "timestamp": ts,
        "station": "ESCALATE",
        "handover_dossier": handover,
    })

    logger.error(f"Incident {state['incident_id']} escalated to human on-call engineer.")
    return {
        "status": "ESCALATED",
        "handover_notes": handover,
        "timeline": timeline,
    }

# --- Conditional Edge Routing ---

def route_after_detect(state: IncidentWorkflowState) -> str:
    if state["is_healthy"]:
        return END
    return "investigate_node"

def route_after_safety(state: IncidentWorkflowState) -> str:
    action = state.get("current_action", {})
    if not action.get("is_approved", False):
        return "escalate_node"
    return "remediate_node"

def route_after_verify(state: IncidentWorkflowState) -> str:
    if state["verification_passed"]:
        return END
    if state["attempt_count"] < state["max_attempts"]:
        return "safety_eval_node"
    return "escalate_node"

def build_incident_graph() -> StateGraph:
    """Builds and compiles the production LangGraph incident investigation workflow."""
    workflow = StateGraph(IncidentWorkflowState)

    # Register Nodes
    workflow.add_node("detect_node", detect_node)
    workflow.add_node("investigate_node", investigate_node)
    workflow.add_node("safety_eval_node", safety_eval_node)
    workflow.add_node("remediate_node", remediate_node)
    workflow.add_node("verify_node", verify_node)
    workflow.add_node("escalate_node", escalate_node)

    # Set Entry Point
    workflow.add_edge(START, "detect_node")

    # Conditional Routing
    workflow.add_conditional_edges(
        "detect_node",
        route_after_detect,
        {"investigate_node": "investigate_node", END: END}
    )

    workflow.add_edge("investigate_node", "safety_eval_node")

    workflow.add_conditional_edges(
        "safety_eval_node",
        route_after_safety,
        {"remediate_node": "remediate_node", "escalate_node": "escalate_node"}
    )

    workflow.add_edge("remediate_node", "verify_node")

    workflow.add_conditional_edges(
        "verify_node",
        route_after_verify,
        {"safety_eval_node": "safety_eval_node", "escalate_node": "escalate_node", END: END}
    )

    workflow.add_edge("escalate_node", END)

    return workflow.compile()
