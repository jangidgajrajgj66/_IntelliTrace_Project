"""
Plain-language Explanation Generator for IntelliTrace.
Author: Gajraj Jangid
Translates technical metrics and logs into a simple, clear briefing for engineers.
"""
from typing import Dict, Any
from src.investigator.cause_finder import InvestigationReport

class Explainer:
    """
    Transforms structured incident investigation reports into natural, concise,
    plain-language explanations suitable for engineers and stakeholders.
    """
    def __init__(self):
        pass

    def explain(self, report: InvestigationReport) -> str:
        """
        Produce a clear, simple incident briefing in plain English.
        """
        rc = report.root_cause
        rec = report.recommended_action
        conf_pct = int(report.confidence_score * 100)

        explanation_lines = [
            f"🔍 Incident Summary: {rc} (Confidence: {conf_pct}%)",
            "",
            "What happened:",
        ]

        if "Queue Bottleneck" in rc:
            explanation_lines.append(
                "The application received a surge of customer requests, but the worker thread pool "
                "ran out of capacity. Because all workers were busy, incoming requests began piling up "
                "in a long waiting line, causing severe website slowdowns."
            )
        elif "Configuration" in rc:
            explanation_lines.append(
                "A recent configuration update introduced an invalid or missing setting. As a result, "
                "the web server threw 500 Internal Server Errors when trying to handle customer requests, "
                "causing immediate order and page failures."
            )
        elif "Cache Saturation" in rc:
            explanation_lines.append(
                "The in-memory cache became bloated and fragmented, causing database locks and query timeouts. "
                "Requests took far too long to finish, degrading page load times well beyond acceptable limits."
            )
        elif "External Infrastructure" in rc:
            explanation_lines.append(
                "A critical downstream third-party payment provider and physical storage array went offline. "
                "Because this is an external hardware/provider failure, it cannot be fixed by standard internal application actions."
            )
        else:
            explanation_lines.append(
                "The application encountered anomalous latency and performance degradation crossing our healthy SLA boundaries."
            )

        explanation_lines.append("")
        explanation_lines.append("Key Evidence:")
        for em in report.evidence_metrics[:2]:
            explanation_lines.append(f"  • Metric: {em}")
        for el in report.evidence_logs[:2]:
            explanation_lines.append(f"  • Log: {el}")

        explanation_lines.append("")
        explanation_lines.append(f"Recommended Safe Action:")
        explanation_lines.append(
            f"  • Apply approved action `{rec}` to remediate the system safely without human intervention."
        )

        return "\n".join(explanation_lines)
