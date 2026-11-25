# IntelliTrace — Autonomous SRE & Incident Intelligence Platform

[![Author](https://img.shields.io/badge/Author-Gajraj%20Jangid-6366f1.svg)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/Orchestrator-LangGraph%20StateGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Safety](https://img.shields.io/badge/Safety%20Guardrails-Strict%20Whitelist-red.svg)]()

**IntelliTrace** is an autonomous Site Reliability Engineering (SRE) and incident intelligence platform crafted by **Gajraj Jangid**. Built with **LangGraph StateGraph**, **FastAPI**, **LLM Telemetry Reasoning**, and a modern **HTML/CSS/JavaScript Web Console**, IntelliTrace continuously monitors application health, detects SLA breaches, performs evidence-backed root cause analysis, executes whitelisted safe remediations, verifies system recovery, and escalates unrecoverable outages to human engineers.

---

## Screenshots & Live Telemetry Graphs

### IntelliTrace Web Console (KPIs, Live SLA Charts & LangGraph Pipeline)
![IntelliTrace Dashboard Overview](docs/screenshots/dashboard_overview.png)

### Full SRE Workspace (Fault Scenarios, Triage Dossier & Historical Incident Log)
![IntelliTrace Full Workspace](docs/screenshots/dashboard_full.png)

---

## Architecture

```mermaid
flowchart TD
    subgraph Traffic & Services
        TG[Synthetic Traffic Generator] --> API[FastAPI E-Commerce Service]
        API --> METRICS[Live Telemetry: Latency, Error Rate, Queue, CPU/RAM]
    end

    subgraph LangGraph State Machine
        START((START)) --> DETECT["1. detect_node (SLA Breach Detector)"]
        DETECT -->|Nominal| HEALTHY((Healthy: END))
        DETECT -->|SLA Breach| INVEST["2. investigate_node (LLM Root Cause Analysis)"]
        INVEST --> SAFETY["3. safety_eval_node (Whitelist & Attempt Guardrails)"]
        SAFETY -->|Approved| REMED["4. remediate_node (Safe Operational Action)"]
        SAFETY -->|Blocked| ESCALATE["6. escalate_node (Human Handover Dossier)"]
        REMED --> VERIFY["5. verify_node (Post-Fix SLA Verification)"]
        VERIFY -->|SLA Restored| RESOLVED((Resolved: END))
        VERIFY -->|Unresolved & Attempts < 2| SAFETY
        VERIFY -->|Attempts >= 2| ESCALATE
        ESCALATE --> HANDOVER((Escalated: END))
    end

    METRICS -.-> DETECT
    REMED -.->|API / Direct Action| API
    ESCALATE -.-> SRE_ENG[Human On-Call Engineer]
```

---

## Key Capabilities

### 1. Modern IntelliTrace Web Console (`src/web/`)
- Served directly by FastAPI at `http://127.0.0.1:8000/` (or `/dashboard`).
- Real-time KPI cards, HTML5 Canvas telemetry charts with SLA threshold overlays, interactive LangGraph pipeline tracker, one-click fault injection, synthetic traffic generator controls, safety policy validator, tabbed triage dossier, historical incident inspector, and live log stream.

### 2. LangGraph StateGraph Orchestration (`src/workflow/`)
- **`detect_node`**: Moving-average anomaly detection against SLA thresholds.
- **`investigate_node`**: Evidence extraction from telemetry and structured logs.
- **`safety_eval_node`**: Enforces action whitelist, parameter boundaries, and remediation budgets.
- **`remediate_node`**: Dispatches safe operational actions through `SafetyEngine` with full audit logging.
- **`verify_node`**: Evaluates stabilization telemetry to confirm SLA recovery.
- **`escalate_node`**: Synthesizes an executive SRE handover dossier when automated attempts are exhausted.

### 3. Multi-Provider LLM Telemetry Reasoning (`src/investigator/`)
- Supports OpenAI (`gpt-4o-mini`), Google Gemini (`gemini-1.5-flash`), or local Ollama instances via environment variables.
- Includes a deterministic offline heuristic reasoning engine for zero-cost, reliable execution without external API keys.

### 4. Strict SRE Safety Guardrails (`src/safety/`)
- **Action Whitelist**: `SCALE_WORKERS`, `ROLLBACK_CONFIG`, `CLEAR_CACHE`, `RESTART_SERVICE`, `DRAIN_QUEUE`, `ENABLE_RATE_LIMITING`.
- **Zero Arbitrary Execution**: Unapproved commands are blocked immediately and logged to `data/audit_trail.log`.
- **Remediation Budget**: Capped at **2 attempts** per incident to prevent cascading outages.

---

## Repeatable Failure Scenarios

| Scenario | Simulated Anomaly | Diagnosed Root Cause | Approved Safe Action | Result |
| :--- | :--- | :--- | :--- | :--- |
| **1. Request Queue Too Long** | Traffic surge exhausts worker concurrency | `Request Queue Bottleneck (Worker Starvation)` | `SCALE_WORKERS` | **RESOLVED** |
| **2. High Error Rate** | Bad config deployment (`v2.5.0-bad`) triggers 500s | `Faulty Configuration Deployment` | `ROLLBACK_CONFIG` | **RESOLVED** |
| **3. Slow Response Time** | Cache fragmentation & DB locks spike latency > 1800ms | `Cache Saturation & Database Lock Contention` | `CLEAR_CACHE` | **RESOLVED** |
| **4. Unfixable Outage** | External payment provider ECONNRESET + storage array crash | `Fatal External Infrastructure & Hardware Outage` | Attempts restart, halts at budget | **ESCALATED** |

---

## Quick Start

### macOS / Linux (`run.sh`)
```bash
chmod +x run.sh
./run.sh --api        # Start IntelliTrace Server + Web Console (http://127.0.0.1:8000)
./run.sh --all        # Run all 4 scenarios and display CLI scorecard
./run.sh --test       # Run pytest suite
./run.sh --dashboard  # Launch optional Streamlit dashboard
```

### Windows (`run.bat`)
```cmd
run.bat --api
run.bat --all
run.bat --test
```

### Direct Python CLI
```bash
python3 main.py --api
python3 main.py --all
python3 main.py --scenario queue
```

---

## Repository Structure

```
IntelliTrace/
├── config.py                     # Thresholds, ports, branding & safety bounds
├── main.py                       # Unified CLI and evaluation runner
├── requirements.txt              # Python dependencies
├── run.sh / run.bat              # Cross-platform startup scripts
├── .env.example                  # Environment configuration template
├── src/
│   ├── web/                      # Modern HTML/CSS/JS IntelliTrace Web Console
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   ├── api/server.py             # FastAPI REST API + Web Console host
│   ├── real_app/                 # FastAPI E-Commerce service & traffic generator
│   ├── fake_app/                 # Simulated telemetry service & failure scenarios
│   ├── monitor/detector.py       # SLA breach & anomaly detector
│   ├── investigator/             # LLM & heuristic root cause engines
│   ├── safety/safety_engine.py   # Whitelist, budget & parameter guardrails
│   ├── storage/                  # SQLite + JSON incident persistence
│   ├── workflow/                 # LangGraph StateGraph & loop orchestrator
│   ├── dashboard/app.py          # Optional Streamlit dashboard
│   └── utils/logger.py           # Structured rotating logger
└── tests/                        # Unit & integration test suite
```

---

## Author

**Gajraj Jangid**
