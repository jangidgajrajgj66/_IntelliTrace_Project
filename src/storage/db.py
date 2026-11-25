"""
SQLite Database Manager for IntelliTrace.
Author: Gajraj Jangid
Stores structured incidents, applied actions, and audit logs.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import DB_PATH

class DatabaseManager:
    """Manages SQLite connection and schema for incident telemetry."""
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                scenario_id TEXT,
                title TEXT,
                status TEXT,
                root_cause TEXT,
                severity TEXT,
                detection_timestamp TEXT,
                resolution_timestamp TEXT,
                duration_seconds REAL,
                before_metrics TEXT,
                after_metrics TEXT,
                explanation TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS incident_actions (
                id TEXT PRIMARY KEY,
                incident_id TEXT,
                attempt_number INTEGER,
                action_name TEXT,
                parameters TEXT,
                status TEXT,
                execution_message TEXT,
                timestamp TEXT,
                FOREIGN KEY (incident_id) REFERENCES incidents (id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                details TEXT
            )
            """)
            conn.commit()

    def save_incident(self, incident_data: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO incidents (
                id, scenario_id, title, status, root_cause, severity,
                detection_timestamp, resolution_timestamp, duration_seconds,
                before_metrics, after_metrics, explanation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_data["id"],
                incident_data.get("scenario_id", ""),
                incident_data.get("title", ""),
                incident_data.get("status", "IN_PROGRESS"),
                incident_data.get("root_cause", ""),
                incident_data.get("severity", "WARNING"),
                incident_data.get("detection_timestamp", ""),
                incident_data.get("resolution_timestamp", ""),
                incident_data.get("duration_seconds", 0.0),
                json.dumps(incident_data.get("before_metrics", {})),
                json.dumps(incident_data.get("after_metrics", {})),
                incident_data.get("explanation", ""),
            ))
            conn.commit()

    def save_action(self, action_data: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO incident_actions (
                id, incident_id, attempt_number, action_name, parameters, status, execution_message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action_data["action_id"],
                action_data["incident_id"],
                action_data["attempt_number"],
                action_data["action_name"],
                json.dumps(action_data.get("parameters", {})),
                action_data["status"],
                action_data["execution_message"],
                action_data["timestamp"],
            ))
            conn.commit()

    def get_all_incidents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incidents ORDER BY detection_timestamp DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["before_metrics"] = json.loads(item["before_metrics"]) if item["before_metrics"] else {}
                item["after_metrics"] = json.loads(item["after_metrics"]) if item["after_metrics"] else {}
                results.append(item)
            return results

    def get_actions_for_incident(self, incident_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incident_actions WHERE incident_id = ? ORDER BY attempt_number ASC", (incident_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["parameters"] = json.loads(item["parameters"]) if item["parameters"] else {}
                results.append(item)
            return results
