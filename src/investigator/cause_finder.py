"""
Root Cause Analysis Engine for IntelliTrace.
Author: Gajraj Jangid
Reads metric trends and structured logs to deduce the underlying fault with evidence.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from src.fake_app.models import LogEntry
from src.monitor.detector import Alert

@dataclass
class InvestigationReport:
    incident_id: str
    root_cause: str
    category: str
    confidence_score: float
    evidence_metrics: List[str] = field(default_factory=list)
    evidence_logs: List[str] = field(default_factory=list)
    recommended_action: str = ""
    action_parameters: Dict[str, Any] = field(default_factory=dict)
    secondary_action: Optional[str] = None
    explanation_plain_text: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class RootCauseFinder:
    """
    Correlates metric anomalies with application logs to determine the true root cause
    and select the optimal approved remediation action.
    """
    def __init__(self):
        pass

    def investigate(
        self,
        incident_id: str,
        alert: Alert,
        metrics_df: pd.DataFrame,
        recent_logs: List[LogEntry]
    ) -> InvestigationReport:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract recent metric windows
        window = metrics_df.tail(5) if not metrics_df.empty else pd.DataFrame()
        avg_resp = float(window["response_time_ms"].mean()) if not window.empty else 0.0
        avg_err = float(window["error_rate_pct"].mean()) if not window.empty else 0.0
        avg_queue = float(window["queue_length"].mean()) if not window.empty else 0.0
        avg_cpu = float(window["cpu_percent"].mean()) if not window.empty else 0.0

        # Collect log messages for keyword and pattern correlation
        error_logs = [str(log) for log in recent_logs if log.level in ["WARN", "ERROR", "CRITICAL"]]
        log_text_blob = " ".join([l.lower() for l in error_logs])

        evidence_metrics: List[str] = []
        evidence_logs: List[str] = []
        root_cause = "Unknown Anomaly"
        category = "UNKNOWN"
        confidence = 0.50
        recommended_action = "RESTART_SERVICE"
        action_params: Dict[str, Any] = {}
        secondary_action = None

        # Evidence collection from metrics
        for v in alert.violations:
            evidence_metrics.append(
                f"{v.metric_name} spiked to {v.current_value}{v.unit} (healthy threshold is {v.threshold}{v.unit}, +{v.diff_percent}%)"
            )

        # Evidence collection from logs (last 3 relevant entries)
        for log in recent_logs[-8:]:
            if log.level in ["WARN", "ERROR", "CRITICAL"]:
                evidence_logs.append(f"[{log.level}] {log.message}")

        # --- Case 1: Unrecoverable External Hardware / Provider Outage ---
        if any(kw in log_text_blob for kw in ["hardware failure", "econnreset", "connection refused", "external payment gateway", "storage array"]):
            root_cause = "Fatal External Infrastructure & Hardware Outage"
            category = "INFRASTRUCTURE_FAILURE"
            confidence = 0.98
            recommended_action = "RESTART_SERVICE"
            secondary_action = "ROLLBACK_CONFIG"
            evidence_metrics.append(f"System failure rate reached {avg_err:.1f}% with severe timeout latency of {avg_resp:.1f}ms")

        # --- Case 2: High Error Rate from Bad Configuration ---
        elif any(kw in log_text_blob for kw in ["config", "nullpointerexception", "route_timeout", "gateway.route_timeout"]) or avg_err > 15.0:
            root_cause = "Faulty Configuration Deployment"
            category = "CONFIGURATION_ERROR"
            confidence = 0.95
            recommended_action = "ROLLBACK_CONFIG"
            secondary_action = "RESTART_SERVICE"
            evidence_metrics.append(f"HTTP error rate surged to {avg_err:.1f}% while queue remained moderate ({avg_queue:.1f} reqs)")

        # --- Case 3: Request Queue Too Long / Worker Starvation ---
        elif avg_queue > 40.0 or any(kw in log_text_blob for kw in ["queue length critical", "worker pool saturated", "waiting for worker"]):
            root_cause = "Request Queue Bottleneck (Worker Thread Starvation)"
            category = "CAPACITY_BOTTLENECK"
            confidence = 0.96
            recommended_action = "SCALE_WORKERS"
            action_params = {"worker_count": 8}
            secondary_action = "DRAIN_QUEUE"
            evidence_metrics.append(f"Queue backlog reached {avg_queue:.1f} pending requests; CPU utilization at {avg_cpu:.1f}%")

        # --- Case 4: Slow Response Time / Cache Saturation / Lock Contention ---
        elif avg_resp > 800.0 or any(kw in log_text_blob for kw in ["cache", "fragmentation", "slow query", "lock wait timeout"]):
            root_cause = "Cache Saturation & Database Lock Contention"
            category = "PERFORMANCE_DEGRADATION"
            confidence = 0.93
            recommended_action = "CLEAR_CACHE"
            secondary_action = "RESTART_SERVICE"
            evidence_metrics.append(f"Latency P95 surged to {avg_resp:.1f}ms (threshold 300ms) with low error rate ({avg_err:.1f}%)")

        # Fallback
        else:
            root_cause = "General Performance Degradation"
            category = "GENERAL"
            confidence = 0.70
            recommended_action = "RESTART_SERVICE"
            secondary_action = None

        return InvestigationReport(
            incident_id=incident_id,
            root_cause=root_cause,
            category=category,
            confidence_score=round(confidence, 2),
            evidence_metrics=evidence_metrics,
            evidence_logs=evidence_logs,
            recommended_action=recommended_action,
            action_parameters=action_params,
            secondary_action=secondary_action,
            timestamp=ts,
        )
