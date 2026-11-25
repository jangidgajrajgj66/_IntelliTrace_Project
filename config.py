"""
IntelliTrace — Production Configuration.
Author: Gajraj Jangid
Defines system thresholds, safety boundaries, storage paths, API endpoints,
and LLM configuration for autonomous SRE incident investigation.
"""
import os
from pathlib import Path

APP_NAME = "IntelliTrace"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Gajraj Jangid"
APP_DESCRIPTION = "Autonomous SRE & Incident Intelligence Platform"

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "incidents.db"
INCIDENTS_JSON_PATH = DATA_DIR / "incident_records.json"
AUDIT_LOG_PATH = DATA_DIR / "audit_trail.log"
APP_LOG_PATH = LOGS_DIR / "application.log"

# FastAPI Network Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
REAL_APP_PORT = int(os.getenv("REAL_APP_PORT", "8080"))
REAL_APP_URL = f"http://{API_HOST}:{REAL_APP_PORT}"

# LLM & Reasoning Engine Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # "auto", "gemini", "openai", "ollama", "heuristic"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini" if OPENAI_API_KEY else "gemini-1.5-flash")

# Synthetic Traffic Generator Configuration
TRAFFIC_CONFIG = {
    "default_rps": 15,
    "concurrency": 4,
    "timeout_seconds": 3.0,
    "endpoints": ["/health", "/catalog", "/orders"],
}

# Healthy Metric Thresholds (SLA / SLO limits)
THRESHOLDS = {
    "max_response_time_ms": 300.0,    # Max acceptable response time in ms
    "max_error_rate_pct": 5.0,        # Max acceptable error rate in percent (e.g., 5%)
    "max_queue_length": 25,           # Max acceptable pending requests in queue
    "max_cpu_percent": 85.0,          # Max acceptable CPU usage
}

# Healthy Baseline Metrics (Normal steady-state operation)
BASELINE_METRICS = {
    "response_time_ms": 110.0,
    "error_rate_pct": 0.2,
    "queue_length": 2,
    "throughput_rps": 50.0,
    "cpu_percent": 28.0,
    "memory_percent": 35.0,
}

# Safety & Remediation Configuration (Strict SRE Guardrails)
SAFETY_CONFIG = {
    "max_fix_attempts": 2,            # Strictly limit remediation loops (No infinite retries)
    "min_workers": 1,
    "max_workers": 16,
    "default_workers": 4,
    "verification_wait_cycles": 3,    # Cycles of metrics to collect post-fix to verify recovery
    "stabilization_seconds": 2.0,     # Time to wait for system stabilization in real app
}

# Approved Safe Actions Whitelist
APPROVED_ACTIONS = [
    "SCALE_WORKERS",           # Scale worker thread pool up or down
    "ROLLBACK_CONFIG",         # Revert to last-known-good configuration
    "RESTART_SERVICE",         # Controlled graceful service restart
    "CLEAR_CACHE",             # Flush corrupted or bloated in-memory cache
    "DRAIN_QUEUE",             # Safely shed or process backlogged queue
    "ENABLE_RATE_LIMITING",    # Throttle incoming burst traffic
]

# Structured Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "format": "%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
