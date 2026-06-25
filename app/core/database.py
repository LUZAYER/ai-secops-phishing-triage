import sqlite3
import os
from datetime import datetime
from typing import Optional


class Database:
    def __init__(self, db_path: str = "state/alerts.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id            TEXT PRIMARY KEY,
                    sender_email        TEXT,
                    sender_display_name TEXT,
                    subject             TEXT,
                    body_text           TEXT,
                    urls                TEXT,
                    attachments         TEXT,
                    spf                 TEXT,
                    dkim                TEXT,
                    dmarc               TEXT,
                    reported_by         TEXT,
                    reported_at         TEXT,
                    classification      TEXT,
                    severity            TEXT,
                    confidence          INTEGER,
                    threat_score        INTEGER,
                    status              TEXT DEFAULT 'NEW',
                    rationale           TEXT,
                    recommended_action  TEXT,
                    social_engineering_tactics TEXT,
                    processed_at        TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id    TEXT,
                    action      TEXT,
                    note        TEXT,
                    timestamp   TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyst_notes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id    TEXT,
                    note        TEXT,
                    created_at  TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_jobs (
                    job_id      TEXT PRIMARY KEY,
                    filename    TEXT,
                    source      TEXT,
                    status      TEXT,
                    created_at  TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()


    # ─── Alerts ───────────────────────────────────────────────────────────────

    def upsert_alert(self, raw: dict, analysis: dict, threat_score: int):
        now = datetime.utcnow().isoformat()
        import json
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO alerts (
                    alert_id, sender_email, sender_display_name, subject, body_text,
                    urls, attachments, spf, dkim, dmarc, reported_by, reported_at,
                    classification, severity, confidence, threat_score, status,
                    rationale, recommended_action, social_engineering_tactics, processed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    classification=excluded.classification,
                    severity=excluded.severity,
                    confidence=excluded.confidence,
                    threat_score=excluded.threat_score,
                    rationale=excluded.rationale,
                    recommended_action=excluded.recommended_action,
                    social_engineering_tactics=excluded.social_engineering_tactics,
                    processed_at=excluded.processed_at
            """, (
                raw["alert_id"],
                raw.get("sender_email"),
                raw.get("sender_display_name"),
                raw.get("subject"),
                raw.get("body_text"),
                json.dumps(raw.get("urls", [])),
                json.dumps(raw.get("attachments", [])),
                raw.get("headers", {}).get("spf"),
                raw.get("headers", {}).get("dkim"),
                raw.get("headers", {}).get("dmarc"),
                raw.get("reported_by"),
                raw.get("reported_at"),
                analysis.get("classification"),
                analysis.get("severity"),
                analysis.get("confidence"),
                threat_score,
                "PROCESSED",
                analysis.get("rationale"),
                analysis.get("recommended_action"),
                json.dumps(analysis.get("social_engineering_tactics", [])),
                now,
            ))

    def get_all_alerts(self, severity_filter: Optional[str] = None,
                       status_filter: Optional[str] = None,
                       search: Optional[str] = None) -> list:
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        if severity_filter:
            query += " AND severity = ?"
            params.append(severity_filter)
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        if search:
            query += " AND (alert_id LIKE ? OR subject LIKE ? OR sender_email LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        query += " ORDER BY processed_at DESC"
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def get_alert(self, alert_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            return dict(row) if row else None

    def exists(self, alert_id: str) -> bool:
        with self._conn() as conn:
            return conn.execute("SELECT 1 FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone() is not None

    def update_status(self, alert_id: str, status: str):
        with self._conn() as conn:
            conn.execute("UPDATE alerts SET status = ? WHERE alert_id = ?", (status, alert_id))
        self.log_action(alert_id, f"Status changed to {status}")

    def get_stats(self) -> dict:
        with self._conn() as conn:
            total     = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            critical  = conn.execute("SELECT COUNT(*) FROM alerts WHERE severity='Critical'").fetchone()[0]
            high      = conn.execute("SELECT COUNT(*) FROM alerts WHERE severity='High'").fetchone()[0]
            medium    = conn.execute("SELECT COUNT(*) FROM alerts WHERE severity='Medium'").fetchone()[0]
            low       = conn.execute("SELECT COUNT(*) FROM alerts WHERE severity='Low'").fetchone()[0]
            escalated = conn.execute("SELECT COUNT(*) FROM alerts WHERE status='ESCALATED'").fetchone()[0]
            benign    = conn.execute("SELECT COUNT(*) FROM alerts WHERE classification='Benign'").fetchone()[0]
            # classification breakdown
            class_rows = conn.execute(
                "SELECT classification, COUNT(*) as cnt FROM alerts GROUP BY classification"
            ).fetchall()
            
            # trend over time (by date)
            trend_rows = conn.execute("""
                SELECT date(processed_at) as date, severity, COUNT(*) as cnt 
                FROM alerts 
                WHERE processed_at IS NOT NULL
                GROUP BY date(processed_at), severity
                ORDER BY date ASC
            """).fetchall()

            # top domains
            domain_rows = conn.execute("""
                SELECT SUBSTR(sender_email, INSTR(sender_email, '@') + 1) as domain, COUNT(*) as cnt
                FROM alerts
                WHERE sender_email IS NOT NULL AND INSTR(sender_email, '@') > 0
                GROUP BY domain
                ORDER BY cnt DESC
                LIMIT 5
            """).fetchall()
        return {
            "total": total,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "escalated": escalated,
            "benign": benign,
            "classification_breakdown": [dict(r) for r in class_rows],
            "trend_data": [dict(r) for r in trend_rows],
            "top_domains": [dict(r) for r in domain_rows],
        }

    # ─── Audit Log ────────────────────────────────────────────────────────────

    def log_action(self, alert_id: str, action: str, note: str = ""):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (alert_id, action, note, timestamp) VALUES (?,?,?,?)",
                (alert_id, action, note, now)
            )

    def get_audit_log(self, alert_id: str) -> list:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM audit_log WHERE alert_id = ? ORDER BY timestamp ASC", (alert_id,)
            ).fetchall()]

    # ─── Analyst Notes ────────────────────────────────────────────────────────

    def add_note(self, alert_id: str, note: str):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO analyst_notes (alert_id, note, created_at) VALUES (?,?,?)",
                (alert_id, note, now)
            )
        self.log_action(alert_id, "Note added", note[:80])

    def get_notes(self, alert_id: str) -> list:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM analyst_notes WHERE alert_id = ? ORDER BY created_at ASC", (alert_id,)
            ).fetchall()]

    # ─── Processing Jobs ──────────────────────────────────────────────────────

    def add_job(self, job_id: str, filename: str, source: str):
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO processing_jobs (job_id, filename, source, status, created_at) VALUES (?,?,?,?,?)",
                (job_id, filename, source, "QUEUED", now)
            )

    def update_job_status(self, job_id: str, status: str):
        with self._conn() as conn:
            conn.execute("UPDATE processing_jobs SET status = ? WHERE job_id = ?", (status, job_id))

    def get_jobs(self) -> list:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM processing_jobs ORDER BY created_at DESC"
            ).fetchall()]

    def get_job(self, job_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM processing_jobs WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def delete_job(self, job_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM processing_jobs WHERE job_id = ?", (job_id,))
