"""Structured farmer memory — SQLite session history across interactions.

No real PII: farmers are keyed by (hashed) WhatsApp number. Stores each
interaction (transcript, district, crop, FSI at the time, actions taken) so
the agent has continuity: "आपण गेल्या आठवड्यात कापसाबद्दल विचारले होते…"
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from .common import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS farmers (
    farmer_id TEXT PRIMARY KEY,          -- sha256 of whatsapp number (no raw PII)
    district TEXT,
    crop TEXT,
    language TEXT DEFAULT 'mr',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id TEXT REFERENCES farmers(farmer_id),
    ts TEXT,
    transcript TEXT,
    district TEXT,
    crop TEXT,
    fsi REAL,
    fsi_level TEXT,
    actions TEXT                          -- JSON list: alerts sent, claims drafted
);
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id TEXT REFERENCES farmers(farmer_id),
    ts TEXT,
    district TEXT,
    crop TEXT,
    claim_text TEXT,
    status TEXT DEFAULT 'drafted'
);
"""


def farmer_id_from_phone(phone: str) -> str:
    return hashlib.sha256(phone.strip().encode()).hexdigest()[:16]


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def upsert_farmer(phone: str, district: str | None = None, crop: str | None = None) -> str:
    fid = farmer_id_from_phone(phone)
    with _conn() as c:
        row = c.execute("SELECT farmer_id FROM farmers WHERE farmer_id=?", (fid,)).fetchone()
        if row is None:
            c.execute("INSERT INTO farmers (farmer_id, district, crop, created_at) VALUES (?,?,?,?)",
                      (fid, district, crop, _now()))
        else:
            if district:
                c.execute("UPDATE farmers SET district=? WHERE farmer_id=?", (district, fid))
            if crop:
                c.execute("UPDATE farmers SET crop=? WHERE farmer_id=?", (crop, fid))
    return fid


def log_interaction(phone: str, transcript: str, district: str | None, crop: str | None,
                    fsi: float | None, fsi_level: str | None, actions: list[str]) -> None:
    fid = upsert_farmer(phone, district, crop)
    with _conn() as c:
        c.execute(
            "INSERT INTO interactions (farmer_id, ts, transcript, district, crop, fsi, fsi_level, actions) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (fid, _now(), transcript, district, crop, fsi, fsi_level, json.dumps(actions, ensure_ascii=False)))


def log_claim(phone: str, district: str, crop: str, claim_text: str) -> None:
    fid = upsert_farmer(phone)
    with _conn() as c:
        c.execute("INSERT INTO claims (farmer_id, ts, district, crop, claim_text) VALUES (?,?,?,?,?)",
                  (fid, _now(), district, crop, claim_text))


def get_farmer_history(phone: str, limit: int = 5) -> dict:
    """Return farmer profile + recent interactions + claims (agent memory)."""
    fid = farmer_id_from_phone(phone)
    with _conn() as c:
        farmer = c.execute("SELECT * FROM farmers WHERE farmer_id=?", (fid,)).fetchone()
        if farmer is None:
            return {"farmer_id": fid, "known": False, "interactions": [], "claims": []}
        inter = c.execute(
            "SELECT ts, transcript, district, crop, fsi, fsi_level, actions FROM interactions "
            "WHERE farmer_id=? ORDER BY id DESC LIMIT ?", (fid, limit)).fetchall()
        claims = c.execute(
            "SELECT ts, district, crop, status FROM claims WHERE farmer_id=? ORDER BY id DESC LIMIT ?",
            (fid, limit)).fetchall()
    return {
        "farmer_id": fid,
        "known": True,
        "district": farmer["district"],
        "crop": farmer["crop"],
        "interactions": [dict(r) for r in inter],
        "claims": [dict(r) for r in claims],
    }


def all_latest_fsi() -> list[dict]:
    """Latest logged FSI per district — feeds the dashboard."""
    with _conn() as c:
        rows = c.execute(
            "SELECT district, crop, fsi, fsi_level, MAX(ts) as ts FROM interactions "
            "WHERE fsi IS NOT NULL GROUP BY district").fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    log_interaction("+911234567890", "test transcript", "Amravati", "cotton", 87.9, "CRITICAL", ["alert_sent"])
    print(json.dumps(get_farmer_history("+911234567890"), indent=2, ensure_ascii=False))
