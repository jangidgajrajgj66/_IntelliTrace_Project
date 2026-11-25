"""
Streamlit Web Dashboard for IntelliTrace.
Author: Gajraj Jangid
Features real-time telemetry charts, live synthetic traffic generation,
LangGraph workflow visualization, and LLM-powered incident dossiers.
"""
import time
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from config import THRESHOLDS, APPROVED_ACTIONS, SAFETY_CONFIG, LLM_PROVIDER, LLM_MODEL, REAL_APP_URL
from src.fake_app.service import SimulatedService
from src.fake_app.scenarios import SCENARIOS
from src.storage.repository import IncidentRepository
from src.safety.safety_engine import SafetyEngine
from src.workflow.loop import AutonomousInvestigator
from src.real_app.traffic_generator import TrafficGenerator

# Streamlit Page Config
st.set_page_config(
    page_title="IntelliTrace — Autonomous SRE & Incident Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State Singletons
if "service" not in st.session_state:
    st.session_state.service = SimulatedService()
if "repository" not in st.session_state:
    st.session_state.repository = IncidentRepository()
if "safety_engine" not in st.session_state:
    st.session_state.safety_engine = SafetyEngine()
if "investigator" not in st.session_state:
    st.session_state.investigator = AutonomousInvestigator(
        service=st.session_state.service,
        repository=st.session_state.repository,
        safety_engine=st.session_state.safety_engine,
    )
if "traffic_gen" not in st.session_state:
    st.session_state.traffic_gen = TrafficGenerator()
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# --- Sidebar Controls ---
st.sidebar.title("🎛️ SRE Control Center")
st.sidebar.markdown(f"**Orchestrator:** `LangGraph StateGraph`")
st.sidebar.markdown(f"**LLM Reasoner:** `{LLM_PROVIDER}` (`{LLM_MODEL}`)")
st.sidebar.markdown("---")

st.sidebar.subheader("1. Fault Injection (Scenarios)")
scenario_options = {
    "queue_bottleneck": "1. Request Queue Too Long",
    "high_error_rate": "2. High Error Rate (Bad Config)",
    "slow_response": "3. Slow Response Time (Cache Latency)",
    "unfixable_outage": "4. Unfixable Outage (Escalate to Human)",
}

selected_scenario_key = st.sidebar.selectbox(
    "Select Incident Scenario:",
    options=list(scenario_options.keys()),
    format_func=lambda k: scenario_options[k],
)

scenario_info = SCENARIOS[selected_scenario_key]
st.sidebar.info(f"**Description:** {scenario_info.description}\n\n**Expected Outcome:** {'Auto-Resolved' if scenario_info.resolvable else 'Escalated to Human'}")

if st.sidebar.button("🚀 Trigger Scenario & Run LangGraph Investigator", type="primary", use_container_width=True):
    with st.spinner("LangGraph agent executing Detect -> Investigate -> Safety -> Remediate -> Verify..."):
        result = st.session_state.investigator.run_scenario(selected_scenario_key)
        st.session_state.last_result = result
        st.sidebar.success(f"Execution complete: Status = [{result.status}]")

if st.sidebar.button("🔄 Reset Service to Nominal Baseline", use_container_width=True):
    st.session_state.service.reset()
    st.session_state.last_result = None
    st.sidebar.success("Service reset to healthy baseline.")

st.sidebar.markdown("---")
st.sidebar.subheader("2. Synthetic Traffic Generator")
traffic_stats = st.session_state.traffic_gen.get_stats()
is_traffic_running = traffic_stats["is_running"]

col_t1, col_t2 = st.sidebar.columns(2)
with col_t1:
    if st.button("▶️ Start Traffic", disabled=is_traffic_running, use_container_width=True):
        st.session_state.traffic_gen.start()
        st.rerun()
with col_t2:
    if st.button("⏹️ Stop Traffic", disabled=not is_traffic_running, use_container_width=True):
        st.session_state.traffic_gen.stop()
        st.rerun()

rps_slider = st.sidebar.slider("Target Requests / Sec (RPS):", min_value=5, max_value=100, value=traffic_stats["target_rps"])
st.session_state.traffic_gen.set_rps(rps_slider)
st.sidebar.caption(f"Traffic status: **{'ACTIVE' if is_traffic_running else 'IDLE'}** | Total sent: `{traffic_stats['requests_sent']}` | Errors: `{traffic_stats['error_count']}`")

st.sidebar.markdown("---")
st.sidebar.subheader("3. SRE Safety Guardrails")
st.sidebar.markdown(f"- **Max Fix Attempts:** `{SAFETY_CONFIG['max_fix_attempts']}` (Strict limit)")
st.sidebar.markdown("- **Approved Actions Whitelist:**")
for act in APPROVED_ACTIONS:
    st.sidebar.markdown(f"  • `{act}`")

# --- Main Dashboard Header ---
st.title("⚡ IntelliTrace — Autonomous SRE Console")
st.caption("Crafted by Gajraj Jangid • Powered by LangGraph, FastAPI & LLM Telemetry Reasoning")

# --- Section 1: Real-time Telemetry Cards ---
metrics_df = st.session_state.service.get_metrics_df(limit=30)
latest = metrics_df.iloc[-1] if not metrics_df.empty else None

if latest is not None:
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    resp_delta = round(latest["response_time_ms"] - 110.0, 1)
    err_delta = round(latest["error_rate_pct"] - 0.2, 1)
    queue_delta = int(latest["queue_length"] - 2)

    resp_color = "normal" if latest["response_time_ms"] <= THRESHOLDS["max_response_time_ms"] else "inverse"
    err_color = "normal" if latest["error_rate_pct"] <= THRESHOLDS["max_error_rate_pct"] else "inverse"
    q_color = "normal" if latest["queue_length"] <= THRESHOLDS["max_queue_length"] else "inverse"

    kpi1.metric("Response Time (P95)", f"{latest['response_time_ms']:.1f} ms", f"{resp_delta:+} ms", delta_color=resp_color)
    kpi2.metric("Error Rate", f"{latest['error_rate_pct']:.2f} %", f"{err_delta:+} %", delta_color=err_color)
    kpi3.metric("Queue Backlog", f"{latest['queue_length']} reqs", f"{queue_delta:+} reqs", delta_color=q_color)
    kpi4.metric("Throughput", f"{latest['throughput_rps']:.1f} rps")
    kpi5.metric("Active Workers", f"{st.session_state.service.state.workers} threads")

# --- Section 2: Real-time Telemetry Charts ---
st.subheader("📈 Live Telemetry & SLA Boundaries")
if not metrics_df.empty:
    col1, col2, col3 = st.columns(3)

    with col1:
        fig_resp = px.line(metrics_df, x="timestamp", y="response_time_ms", title="Response Time (ms)", markers=True)
        fig_resp.add_hline(y=THRESHOLDS["max_response_time_ms"], line_dash="dash", line_color="red", annotation_text=f"SLA {THRESHOLDS['max_response_time_ms']}ms")
        fig_resp.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_resp, use_container_width=True)

    with col2:
        fig_err = px.line(metrics_df, x="timestamp", y="error_rate_pct", title="Error Rate (%)", markers=True)
        fig_err.add_hline(y=THRESHOLDS["max_error_rate_pct"], line_dash="dash", line_color="red", annotation_text=f"SLA {THRESHOLDS['max_error_rate_pct']}%")
        fig_err.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_err, use_container_width=True)

    with col3:
        fig_q = px.line(metrics_df, x="timestamp", y="queue_length", title="Queue Backlog (reqs)", markers=True)
        fig_q.add_hline(y=THRESHOLDS["max_queue_length"], line_dash="dash", line_color="red", annotation_text=f"SLA {THRESHOLDS['max_queue_length']} reqs")
        fig_q.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_q, use_container_width=True)

# --- Section 3: LangGraph State Machine Architecture View ---
with st.expander("🧩 LangGraph Agent Architecture & State Machine Flow", expanded=False):
    st.markdown("""
    ```mermaid
    flowchart LR
        START((START)) --> detect["1. detect_node"]
        detect -->|SLA Breach| invest["2. investigate_node (LLM)"]
        detect -->|Nominal| END_H((END: Healthy))
        invest --> safety["3. safety_eval_node"]
        safety -->|Approved| remed["4. remediate_node"]
        safety -->|Blocked| esc["6. escalate_node"]
        remed --> verify["5. verify_node"]
        verify -->|Recovered| END_R((END: Resolved))
        verify -->|Unresolved & Attempts < 2| safety
        verify -->|Attempts >= 2| esc
        esc --> END_E((END: Escalated))
    ```
    """)
    st.caption("Every state transition is strictly typed, auditable, and bounded by safety policies.")

# --- Section 4: Autonomous Triage Dossier ---
st.markdown("---")
st.subheader("📋 Autonomous Triage Dossier (LangGraph Output)")

if st.session_state.last_result:
    res = st.session_state.last_result
    status_color = "green" if res.status == "RESOLVED" else "red"
    st.markdown(
        f"### Status: <span style='color:{status_color}; font-weight:bold;'>[{res.status}]</span> — {res.title} (`{res.incident_id}`)",
        unsafe_allow_html=True
    )

    t1, t2, t3, t4 = st.tabs([
        "🔍 Root Cause & LLM Briefing",
        "🛠️ Actions & Safety Audit",
        "📊 Before vs After Metrics",
        "⏱️ LangGraph Execution Timeline"
    ])

    with t1:
        st.markdown(f"**Diagnosed Root Cause:** `{res.root_cause}`")
        st.markdown(f"**Severity:** `{res.severity}` | **Detected At:** `{res.detected_at}` | **Closed At:** `{res.resolved_at or 'N/A'}`")
        st.markdown("---")
        st.markdown("**LLM Plain-Language Briefing:**")
        st.info(res.explanation)

        if res.human_handover_notes:
            st.error(res.human_handover_notes)

    with t2:
        st.markdown("#### Operational Actions Executed via Safety Engine")
        if res.actions_taken:
            actions_table = []
            for act in res.actions_taken:
                actions_table.append({
                    "Attempt": act.get("attempt_number"),
                    "Action": act.get("action_name"),
                    "Parameters": str(act.get("parameters", {})),
                    "Status": act.get("status"),
                    "Approved": "✅ YES" if act.get("is_approved") else "❌ NO",
                    "Message": act.get("execution_message"),
                    "Timestamp": act.get("timestamp"),
                })
            st.dataframe(pd.DataFrame(actions_table), use_container_width=True)
        else:
            st.write("No remediation actions required.")

    with t3:
        st.markdown("#### Metric Recovery Verification")
        c_b, c_a = st.columns(2)
        with c_b:
            st.markdown("##### ❌ Before Remediation (Breach Point)")
            st.json(res.before_metrics)
        with c_a:
            st.markdown("##### ✅ After Remediation (Verified Recovery)")
            st.json(res.after_metrics)

    with t4:
        st.markdown("#### LangGraph Node Execution Steps")
        if res.timeline:
            for step in res.timeline:
                station = step.get("station", "STEP")
                ts = step.get("timestamp", "")
                st.markdown(f"- **`{station}`** `[{ts}]`: {step.get('message') or step.get('root_cause') or step.get('action') or ''}")
        else:
            st.write("Timeline details recorded in SQLite database.")

else:
    st.info("No active incident simulated yet. Choose a scenario in the sidebar and click 'Trigger Scenario & Run LangGraph Investigator'.")

# --- Section 5: Historical Incident Log ---
st.markdown("---")
st.subheader("🗄️ Historical Incident Log (SQLite Database)")
all_incidents = st.session_state.repository.list_incidents()
if all_incidents:
    clean_history = []
    for inc in all_incidents:
        clean_history.append({
            "Incident ID": inc["id"],
            "Scenario": inc["title"],
            "Root Cause": inc["root_cause"],
            "Status": inc["status"],
            "Severity": inc["severity"],
            "Detected": inc["detection_timestamp"],
            "Resolved": inc["resolution_timestamp"],
        })
    st.dataframe(pd.DataFrame(clean_history), use_container_width=True)
else:
    st.write("No incidents recorded in database yet.")

# --- Section 6: Live Application Logs ---
st.markdown("---")
st.subheader("📜 Application Live Log Stream")
logs = st.session_state.service.get_recent_logs(15)
log_display = "\n".join([str(l) for l in reversed(logs)])
st.text_area("Live Stream", log_display, height=180)
