"""
Predefined failure scenarios for IntelliTrace.
Author: Gajraj Jangid
"""
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class FailureScenario:
    id: str
    name: str
    description: str
    expected_root_cause: str
    effective_actions: List[str]
    symptoms: str
    resolvable: bool = True

SCENARIOS = {
    "queue_bottleneck": FailureScenario(
        id="queue_bottleneck",
        name="Request Queue Too Long",
        description="Surge in concurrent shopping requests causes request backlog and worker thread starvation.",
        expected_root_cause="Request Queue Bottleneck (Worker Starvation)",
        effective_actions=["SCALE_WORKERS", "DRAIN_QUEUE", "ENABLE_RATE_LIMITING"],
        symptoms="Queue length > 80, Response time > 600ms, Thread pool saturation",
        resolvable=True,
    ),
    "high_error_rate": FailureScenario(
        id="high_error_rate",
        name="High Error Rate (Bad Configuration)",
        description="Defective configuration flag (v2.5.0-bad) causing HTTP 500 Internal Server Errors across checkout routes.",
        expected_root_cause="Faulty Configuration Deployment",
        effective_actions=["ROLLBACK_CONFIG"],
        symptoms="Error rate > 25%, HTTP 500 NullPointerExceptions in config parser",
        resolvable=True,
    ),
    "slow_response": FailureScenario(
        id="slow_response",
        name="Slow Response (Cache Saturation / Latency Spike)",
        description="Cache leak and database connection locking causing response times to soar beyond 1800ms.",
        expected_root_cause="Cache Saturation & Memory Lock Contention",
        effective_actions=["CLEAR_CACHE", "RESTART_SERVICE"],
        symptoms="Response time > 1500ms, Cache eviction failures, Lock timeouts",
        resolvable=True,
    ),
    "unfixable_outage": FailureScenario(
        id="unfixable_outage",
        name="Unrecoverable Outage (External Provider Failure)",
        description="Downstream payment gateway provider completely unreachable and core storage volume degraded.",
        expected_root_cause="Fatal External Upstream Provider Outage",
        effective_actions=[],  # No automated action can fix external vendor blackout
        symptoms="Error rate 100%, Third-party connection refused, Storage I/O degraded",
        resolvable=False,
    ),
}
