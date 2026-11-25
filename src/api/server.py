"""
IntelliTrace — Production FastAPI Server & Web Console.
Author: Gajraj Jangid
Exposes RESTful endpoints for autonomous telemetry monitoring, LangGraph workflow execution,
safety audit queries, traffic generation, and serves the IntelliTrace Web Console.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import (
    APP_NAME,
    APP_VERSION,
    APP_AUTHOR,
    APP_DESCRIPTION,
    API_HOST,
    API_PORT,
    THRESHOLDS,
    APPROVED_ACTIONS,
    SAFETY_CONFIG,
    LLM_PROVIDER,
    LLM_MODEL,
)
from src.utils.logger import get_logger
from src.fake_app.service import SimulatedService
from src.fake_app.scenarios import SCENARIOS
from src.workflow.loop import AutonomousInvestigator
from src.storage.repository import IncidentRepository
from src.safety.safety_engine import SafetyEngine
from src.real_app.api import app as real_app_router
from src.real_app.traffic_generator import TrafficGenerator

logger = get_logger("api.server")
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Shared singletons
service_instance = SimulatedService()
repository_instance = IncidentRepository()
safety_instance = SafetyEngine()
traffic_instance = TrafficGenerator()
investigator_instance = AutonomousInvestigator(
    service=service_instance,
    repository=repository_instance,
    safety_engine=safety_instance,
)

# Pydantic Schemas
class ScenarioExecutionRequest(BaseModel):
    scenario_id: str = Field(description="Scenario to trigger: queue_bottleneck, high_error_rate, slow_response, unfixable_outage")

class DirectActionRequest(BaseModel):
    incident_id: str
    action_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class TrafficStartRequest(BaseModel):
    target_rps: int = Field(default=15, ge=1, le=200)

def create_investigator_api() -> FastAPI:
    api = FastAPI(
        title=f"{APP_NAME} API",
        description=f"{APP_DESCRIPTION} — Powered by LangGraph, FastAPI, and LLM telemetry reasoning. Crafted by {APP_AUTHOR}.",
        version=APP_VERSION,
    )

    # Enable CORS for modern web dashboards and microservices
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static web assets and the real e-commerce application under /service
    if WEB_DIR.exists():
        api.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
    api.mount("/service", real_app_router)

    def _api_info_payload() -> Dict[str, Any]:
        return {
            "name": APP_NAME,
            "author": APP_AUTHOR,
            "description": APP_DESCRIPTION,
            "version": APP_VERSION,
            "orchestrator": "LangGraph StateGraph",
            "llm_provider": LLM_PROVIDER,
            "llm_model": LLM_MODEL,
            "status": "operational",
            "endpoints": {
                "web_console": "/dashboard",
                "telemetry": "/api/v1/telemetry/live",
                "telemetry_history": "/api/v1/telemetry/history",
                "scenarios": "/api/v1/scenarios",
                "execute": "/api/v1/scenarios/execute",
                "incidents": "/api/v1/incidents",
                "safety_audit": "/api/v1/safety/audit",
                "graph_info": "/api/v1/graph/info",
                "logs": "/api/v1/logs",
                "traffic": "/api/v1/traffic/status",
                "ecommerce_app": "/service",
            },
        }

    @api.get("/", tags=["Info"])
    def root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept and (WEB_DIR / "index.html").exists():
            return FileResponse(WEB_DIR / "index.html")
        return JSONResponse(_api_info_payload())

    @api.get("/dashboard", tags=["Web Console"], include_in_schema=False)
    @api.get("/ui", tags=["Web Console"], include_in_schema=False)
    def web_console():
        index_path = WEB_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Web console assets not found.")
        return FileResponse(index_path)

    @api.get("/api/v1/info", tags=["Info"])
    def api_info():
        return _api_info_payload()

    @api.get("/api/v1/health", tags=["System"])
    def health_check():
        return {
            "status": "healthy",
            "llm_provider": LLM_PROVIDER,
            "max_attempts": SAFETY_CONFIG["max_fix_attempts"],
            "approved_actions": APPROVED_ACTIONS,
        }

    @api.get("/api/v1/telemetry/live", tags=["Telemetry"])
    def get_live_telemetry():
        df = service_instance.get_metrics_df(limit=10)
        latest = df.iloc[-1].to_dict() if not df.empty else {}
        return {
            "latest_metrics": latest,
            "thresholds": THRESHOLDS,
            "service_state": {
                "workers": service_instance.state.workers,
                "config_version": service_instance.state.config_version,
                "active_scenario": service_instance.state.active_scenario,
                "is_healthy": service_instance.state.is_healthy,
            }
        }

    @api.get("/api/v1/telemetry/history", tags=["Telemetry"])
    def get_telemetry_history(limit: int = Query(default=30, ge=5, le=200)):
        df = service_instance.get_metrics_df(limit=limit)
        records = df.to_dict(orient="records") if not df.empty else []
        return {
            "count": len(records),
            "history": records,
            "thresholds": THRESHOLDS,
            "service_state": {
                "workers": service_instance.state.workers,
                "config_version": service_instance.state.config_version,
                "active_scenario": service_instance.state.active_scenario,
                "is_healthy": service_instance.state.is_healthy,
                "uptime_seconds": service_instance.state.uptime_seconds,
            },
        }

    @api.post("/api/v1/service/tick", tags=["Telemetry"])
    def tick_service():
        point = service_instance.tick()
        return {"status": "ok", "metric": point.to_dict()}

    @api.post("/api/v1/service/reset", tags=["Telemetry"])
    def reset_service():
        service_instance.reset()
        return {"status": "reset", "message": "Service restored to nominal baseline."}

    @api.get("/api/v1/logs", tags=["Telemetry"])
    def get_recent_logs(limit: int = Query(default=30, ge=1, le=200)):
        logs = service_instance.get_recent_logs(limit=limit)
        return {"logs": [l.to_dict() for l in reversed(logs)]}

    @api.get("/api/v1/traffic/status", tags=["Traffic"])
    def get_traffic_status():
        return traffic_instance.get_stats()

    @api.post("/api/v1/traffic/start", tags=["Traffic"])
    def start_traffic(req: TrafficStartRequest = TrafficStartRequest()):
        traffic_instance.set_rps(req.target_rps)
        traffic_instance.start()
        return traffic_instance.get_stats()

    @api.post("/api/v1/traffic/stop", tags=["Traffic"])
    def stop_traffic():
        traffic_instance.stop()
        return traffic_instance.get_stats()

    @api.get("/api/v1/scenarios", tags=["Scenarios"])
    def list_scenarios():
        return {
            k: {
                "id": v.id,
                "name": v.name,
                "description": v.description,
                "symptoms": v.symptoms,
                "resolvable": v.resolvable,
            }
            for k, v in SCENARIOS.items()
        }

    @api.post("/api/v1/scenarios/execute", tags=["Investigation"])
    def execute_scenario(req: ScenarioExecutionRequest):
        if req.scenario_id not in SCENARIOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown scenario '{req.scenario_id}'. Available: {list(SCENARIOS.keys())}"
            )

        logger.info(f"API request to run scenario: {req.scenario_id}")
        result = investigator_instance.run_scenario(req.scenario_id)
        return result.to_dict()

    @api.get("/api/v1/incidents", tags=["Incidents"])
    def list_incidents(limit: int = Query(default=50, ge=1, le=200)):
        incidents = repository_instance.list_incidents()
        return {"total": len(incidents), "incidents": incidents[:limit]}

    @api.get("/api/v1/incidents/{incident_id}", tags=["Incidents"])
    def get_incident(incident_id: str):
        inc = repository_instance.get_incident(incident_id)
        if not inc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")
        return inc

    @api.get("/api/v1/safety/audit", tags=["Safety"])
    def get_safety_audit():
        actions = [a.to_dict() for a in safety_instance.action_history]
        return {
            "max_attempts": SAFETY_CONFIG["max_fix_attempts"],
            "approved_actions": APPROVED_ACTIONS,
            "total_actions": len(actions),
            "audit_trail": actions[-50:],
        }

    @api.post("/api/v1/safety/validate", tags=["Safety"])
    def validate_action(req: DirectActionRequest):
        is_valid, reason, code = safety_instance.validate_action(req.incident_id, req.action_name, req.parameters)
        return {
            "action_name": req.action_name,
            "is_approved": is_valid,
            "status_code": code,
            "reason": reason,
        }

    @api.get("/api/v1/graph/info", tags=["LangGraph"])
    def get_graph_info():
        return {
            "orchestrator": "LangGraph StateGraph",
            "nodes": [
                {"id": "detect_node", "role": "Telemetry SLA Anomaly Evaluation"},
                {"id": "investigate_node", "role": "LLM Root Cause Diagnosis & Evidence Extraction"},
                {"id": "safety_eval_node", "role": "Whitelist, Parameter & Attempt Guardrails"},
                {"id": "remediate_node", "role": "Safe Operational Remediation Execution"},
                {"id": "verify_node", "role": "Post-Fix Stabilization & SLA Recovery Verification"},
                {"id": "escalate_node", "role": "Human On-Call Engineer Handover Synthesis"},
            ],
            "routing": {
                "from_detect": "If healthy -> END; If breach -> investigate_node",
                "from_investigate": "Always -> safety_eval_node",
                "from_safety_eval": "If approved -> remediate_node; If blocked -> escalate_node",
                "from_remediate": "Always -> verify_node",
                "from_verify": "If recovered -> END (RESOLVED); If retry allowed -> safety_eval_node; Else -> escalate_node",
                "from_escalate": "Always -> END (ESCALATED)",
            }
        }

    return api

app = create_investigator_api()
