"""
Integration tests for IntelliTrace FastAPI Server & Web Console.
Validates telemetry endpoints, LangGraph scenario execution, Web UI serving, and safety endpoints.
"""
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_api_root_and_health():
    res = client.get("/", headers={"Accept": "application/json"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "IntelliTrace"
    assert data["author"] == "Gajraj Jangid"
    assert data["orchestrator"] == "LangGraph StateGraph"

    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"


def test_web_console_served():
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "IntelliTrace" in res.text
    assert "Gajraj Jangid" in res.text


def test_api_telemetry_and_scenarios():
    res_t = client.get("/api/v1/telemetry/live")
    assert res_t.status_code == 200
    assert "latest_metrics" in res_t.json()

    res_hist = client.get("/api/v1/telemetry/history?limit=10")
    assert res_hist.status_code == 200
    assert len(res_hist.json()["history"]) >= 1

    res_s = client.get("/api/v1/scenarios")
    assert res_s.status_code == 200
    scenarios = res_s.json()
    assert "queue_bottleneck" in scenarios
    assert "high_error_rate" in scenarios


def test_api_execute_scenario_and_audit():
    res = client.post("/api/v1/scenarios/execute", json={"scenario_id": "queue_bottleneck"})
    assert res.status_code == 200
    result = res.json()
    assert result["status"] == "RESOLVED"
    assert "Queue Bottleneck" in result["root_cause"]
    assert len(result["actions_taken"]) >= 1

    res_audit = client.get("/api/v1/safety/audit")
    assert res_audit.status_code == 200
    assert res_audit.json()["total_actions"] >= 1


def test_api_logs_and_traffic_and_reset():
    assert client.get("/api/v1/logs").status_code == 200
    assert client.get("/api/v1/traffic/status").status_code == 200
    assert client.post("/api/v1/service/tick").status_code == 200
    assert client.post("/api/v1/service/reset").status_code == 200


def test_api_graph_info():
    res = client.get("/api/v1/graph/info")
    assert res.status_code == 200
    assert len(res.json()["nodes"]) == 6
