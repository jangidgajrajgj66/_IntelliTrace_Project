"""
Detection Engine for IntelliTrace.
Author: Gajraj Jangid
Monitors service telemetry and triggers alerts when SLA/SLO thresholds are breached.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from config import THRESHOLDS

@dataclass
class MetricViolation:
    metric_name: str
    current_value: float
    threshold: float
    unit: str
    diff_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Alert:
    is_alert: bool
    severity: str  # "OK", "WARNING", "CRITICAL"
    violations: List[MetricViolation] = field(default_factory=list)
    message: str = ""
    timestamp: str = ""
    metrics_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_alert": self.is_alert,
            "severity": self.severity,
            "violations": [v.to_dict() for v in self.violations],
            "message": self.message,
            "timestamp": self.timestamp,
            "metrics_snapshot": self.metrics_snapshot,
        }

class IncidentDetector:
    """
    Watches metric timeseries data, calculates moving averages and statistical anomalies,
    and triggers structured alerts when operational health limits are breached.
    """
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or THRESHOLDS.copy()

    def evaluate(self, metrics_df: pd.DataFrame) -> Alert:
        """
        Evaluate recent metrics dataframe against health thresholds.
        Returns an Alert object detailing health status and any SLA violations.
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if metrics_df.empty:
            return Alert(
                is_alert=False,
                severity="OK",
                message="No metrics available yet.",
                timestamp=ts,
            )

        # Look at the most recent 3 observations for smoothing
        window = metrics_df.tail(3)
        latest = metrics_df.iloc[-1]
        snapshot = latest.to_dict()

        violations: List[MetricViolation] = []

        # 1. Check Response Time SLA
        avg_resp_time = float(window["response_time_ms"].mean())
        max_resp = self.thresholds["max_response_time_ms"]
        if avg_resp_time > max_resp:
            diff_pct = round(((avg_resp_time - max_resp) / max_resp) * 100, 1)
            violations.append(MetricViolation(
                metric_name="response_time_ms",
                current_value=round(avg_resp_time, 2),
                threshold=max_resp,
                unit="ms",
                diff_percent=diff_pct,
            ))

        # 2. Check Error Rate SLA
        avg_err_rate = float(window["error_rate_pct"].mean())
        max_err = self.thresholds["max_error_rate_pct"]
        if avg_err_rate > max_err:
            diff_pct = round(((avg_err_rate - max_err) / max_err) * 100, 1)
            violations.append(MetricViolation(
                metric_name="error_rate_pct",
                current_value=round(avg_err_rate, 2),
                threshold=max_err,
                unit="%",
                diff_percent=diff_pct,
            ))

        # 3. Check Queue Length
        avg_queue = float(window["queue_length"].mean())
        max_queue = float(self.thresholds["max_queue_length"])
        if avg_queue > max_queue:
            diff_pct = round(((avg_queue - max_queue) / max_queue) * 100, 1)
            violations.append(MetricViolation(
                metric_name="queue_length",
                current_value=round(avg_queue, 1),
                threshold=max_queue,
                unit="reqs",
                diff_percent=diff_pct,
            ))

        # 4. Check CPU Usage
        avg_cpu = float(window["cpu_percent"].mean())
        max_cpu = self.thresholds["max_cpu_percent"]
        if avg_cpu > max_cpu:
            diff_pct = round(((avg_cpu - max_cpu) / max_cpu) * 100, 1)
            violations.append(MetricViolation(
                metric_name="cpu_percent",
                current_value=round(avg_cpu, 1),
                threshold=max_cpu,
                unit="%",
                diff_percent=diff_pct,
            ))

        if not violations:
            return Alert(
                is_alert=False,
                severity="OK",
                message="All service health metrics are within nominal SLA bounds.",
                timestamp=ts,
                metrics_snapshot=snapshot,
            )

        # Determine severity based on breach magnitude
        is_critical = any(
            (v.metric_name == "error_rate_pct" and v.current_value > 20.0) or
            (v.metric_name == "response_time_ms" and v.current_value > 1000.0) or
            (v.metric_name == "queue_length" and v.current_value > 80)
            for v in violations
        )

        severity = "CRITICAL" if is_critical else "WARNING"
        violation_summaries = [f"{v.metric_name}={v.current_value}{v.unit} (limit {v.threshold}{v.unit}, +{v.diff_percent}%)" for v in violations]
        msg = f"Health check breach ({severity}): " + ", ".join(violation_summaries)

        return Alert(
            is_alert=True,
            severity=severity,
            violations=violations,
            message=msg,
            timestamp=ts,
            metrics_snapshot=snapshot,
        )
