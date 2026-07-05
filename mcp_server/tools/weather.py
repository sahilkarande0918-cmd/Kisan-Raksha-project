"""Drought signal from Open-Meteo (keyless, free) — 30-day rainfall deficit.

Compares the last 30 days of rainfall at the district HQ against the mean of
the same calendar window over the previous 5 years (Open-Meteo ERA5 archive).
Signal = deficit fraction, 0 (no deficit) .. 1 (total failure of rains).
"""
from datetime import date, timedelta

import requests

from .common import cache_get, cache_put, clamp01, find_district

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
LOOKBACK_DAYS = 30
BASELINE_YEARS = 5


def _window_rainfall(lat: float, lon: float, start: date, end: date) -> float | None:
    r = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "precipitation_sum",
            "timezone": "Asia/Kolkata",
        },
        timeout=20,
    )
    r.raise_for_status()
    vals = r.json().get("daily", {}).get("precipitation_sum") or []
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def get_weather_signal(district: str) -> dict:
    """Return drought stress signal for a district. Falls back to offline cache."""
    d = find_district(district)
    if not d:
        return {"error": f"Unknown district/taluka: {district}"}

    try:
        end = date.today() - timedelta(days=6)  # archive lags ~5 days
        start = end - timedelta(days=LOOKBACK_DAYS - 1)
        current = _window_rainfall(d["lat"], d["lon"], start, end)

        baseline_totals = []
        for y in range(1, BASELINE_YEARS + 1):
            b_start = start.replace(year=start.year - y)
            b_end = end.replace(year=end.year - y)
            total = _window_rainfall(d["lat"], d["lon"], b_start, b_end)
            if total is not None:
                baseline_totals.append(total)

        if current is None or not baseline_totals:
            raise ValueError("no rainfall data returned")

        baseline = sum(baseline_totals) / len(baseline_totals)
        deficit_pct = 0.0 if baseline <= 0 else max(0.0, (baseline - current) / baseline) * 100
        # dry-spell length: consecutive rainless days at window end
        result = {
            "district": d["name"],
            "region": d["region"],
            "window_days": LOOKBACK_DAYS,
            "rainfall_mm": round(current, 1),
            "baseline_mm": round(baseline, 1),
            "deficit_pct": round(deficit_pct, 1),
            "drought_signal": round(clamp01(deficit_pct / 100), 3),
            "source": "Open-Meteo ERA5 archive (open-meteo.com)",
            "cached": False,
        }
        cache_put("weather", d["name"], result)
        return result
    except Exception as e:  # offline-first fallback
        cached = cache_get("weather", d["name"])
        if cached:
            cached["fallback_reason"] = str(e)
            return cached
        return {"error": f"weather fetch failed and no cache: {e}", "district": d["name"]}


if __name__ == "__main__":
    import json, sys
    print(json.dumps(get_weather_signal(sys.argv[1] if len(sys.argv) > 1 else "Amravati"), indent=2))
