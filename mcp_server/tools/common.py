"""Shared paths, config and offline-cache helpers for KisaanRaksha tools."""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "model"
DATASET_DIR = PROJECT_ROOT / "dataset"
OFFLINE_CACHE_PATH = DATA_DIR / "offline_cache.json"
DB_PATH = DATA_DIR / "kisaanraksha.db"

load_dotenv(PROJECT_ROOT / ".env")

_cache_lock = threading.Lock()


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def districts() -> list[dict]:
    return load_json(DATA_DIR / "maharashtra_districts.json")["districts"]


def crop_calendar() -> dict:
    return load_json(DATA_DIR / "crop_calendar.json")


def find_district(name: str) -> dict | None:
    """Match a district by name or by one of its talukas (case-insensitive)."""
    name_l = name.strip().lower()
    for d in districts():
        if d["name"].lower() == name_l:
            return d
    for d in districts():
        for t in d["talukas"]:
            if t.lower() == name_l:
                return d
    # loose contains-match as last resort
    for d in districts():
        if name_l in d["name"].lower() or d["name"].lower() in name_l:
            return d
    return None


def _read_cache() -> dict:
    if OFFLINE_CACHE_PATH.exists():
        try:
            return load_json(OFFLINE_CACHE_PATH)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def cache_get(section: str, key: str) -> dict | None:
    """Return last-known value for key, or None. Offline-first fallback."""
    entry = _read_cache().get(section, {}).get(key)
    if entry:
        entry = dict(entry)
        entry["cached"] = True
    return entry


def cache_put(section: str, key: str, value: dict) -> None:
    with _cache_lock:
        cache = _read_cache()
        cache.setdefault(section, {})[key] = {
            **value,
            "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        OFFLINE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OFFLINE_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1, ensure_ascii=False)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
