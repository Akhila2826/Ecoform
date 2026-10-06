"""DatabaseManager: SQLite storage for user_inputs and eco_reports (session tracking & reuse)."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "data" / "ecofarm.db"


class DatabaseManager:
    def __init__(self, db_path: str | Path = DB_FILE):
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._connect()
        try:
            with conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_inputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    name TEXT, land_area REAL, crop_type TEXT,
                    fertilizer_type TEXT, fertilizer_used REAL,
                    pump_type TEXT, irrigation_hours REAL, pump_kw REAL,
                    machinery_diesel REAL
                );
                CREATE TABLE IF NOT EXISTS eco_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_id INTEGER NOT NULL REFERENCES user_inputs(id),
                    created_at TEXT NOT NULL,
                    total_emission REAL, per_hectare REAL, eco_score INTEGER,
                    rating TEXT, summary TEXT
                );""")
        finally:
            conn.close()

    def save_data(self, farmer, result, summary: str = "") -> int:
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute(
                    """INSERT INTO user_inputs (created_at, name, land_area, crop_type, fertilizer_type,
                       fertilizer_used, pump_type, irrigation_hours, pump_kw, machinery_diesel)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (now, farmer.name, farmer.land_area, farmer.crop_type, farmer.fertilizer_type,
                     farmer.fertilizer_used, farmer.pump_type, farmer.irrigation_hours,
                     farmer.pump_kw, farmer.machinery_diesel))
                input_id = cur.lastrowid
                conn.execute(
                    """INSERT INTO eco_reports (input_id, created_at, total_emission, per_hectare,
                       eco_score, rating, summary) VALUES (?,?,?,?,?,?,?)""",
                    (input_id, now, result.total, result.per_hectare, result.eco_score,
                     result.rating, json.dumps({"text": summary})))
            return input_id
        finally:
            conn.close()

    def fetch_data(self, farmer_name: str | None = None, limit: int = 50) -> list[dict]:
        query = """SELECT r.id AS report_id, r.created_at, u.name, u.crop_type, u.land_area,
                          u.fertilizer_type, u.fertilizer_used, u.pump_type, u.irrigation_hours,
                          u.pump_kw, u.machinery_diesel,
                          r.total_emission, r.per_hectare, r.eco_score, r.rating
                   FROM eco_reports r JOIN user_inputs u ON u.id = r.input_id"""
        params: tuple = ()
        if farmer_name:
            query += " WHERE LOWER(u.name) = LOWER(?)"
            params = (farmer_name,)
        query += " ORDER BY r.id DESC LIMIT ?"
        conn = self._connect()
        try:
            return [dict(r) for r in conn.execute(query, params + (limit,))]
        finally:
            conn.close()

    def delete_all(self):
        conn = self._connect()
        try:
            with conn:
                conn.execute("DELETE FROM eco_reports")
                conn.execute("DELETE FROM user_inputs")
        finally:
            conn.close()
