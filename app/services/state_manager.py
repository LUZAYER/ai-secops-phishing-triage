import sqlite3
import os
from datetime import datetime

class StateManager:
    def __init__(self, db_path: str = "state/alerts.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                classification TEXT,
                severity TEXT,
                confidence INTEGER,
                status TEXT,
                processed_at TEXT
            )
        ''')
        self.conn.commit()

    def exists(self, alert_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM alerts WHERE alert_id = ?", (alert_id,))
        return cursor.fetchone() is not None

    def insert(self, alert_id: str, classification: str, severity: str, confidence: int, status: str = "PROCESSED"):
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute('''
            INSERT INTO alerts (alert_id, classification, severity, confidence, status, processed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (alert_id, classification, severity, confidence, status, now))
        self.conn.commit()

    def update_status(self, alert_id: str, status: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE alerts SET status = ? WHERE alert_id = ?
        ''', (status, alert_id))
        self.conn.commit()

    def get(self, alert_id: str) -> dict:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT alert_id, classification, severity, confidence, status, processed_at
            FROM alerts WHERE alert_id = ?
        ''', (alert_id,))
        row = cursor.fetchone()
        if row:
            return {
                "alert_id": row[0],
                "classification": row[1],
                "severity": row[2],
                "confidence": row[3],
                "status": row[4],
                "processed_at": row[5]
            }
        return None
