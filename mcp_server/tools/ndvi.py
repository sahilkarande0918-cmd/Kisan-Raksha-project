"""NDVI crop-health signal — real MODIS MOD13Q1 via NASA ORNL Subsets REST API.

Keyless, synchronous, free: https://modis.ornl.gov/rst/api/v1/
Compares the latest NDVI composite at the district HQ against the mean of the
available composites this season. Low absolute NDVI during the growing season
= vegetation stress. Signal 0..1.
"""
from datetime import date, timedelta

import requests

from .common import cache_get, cache_put, clamp01, find_district

ORNL_URL = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
SCALE = 0.0001
# NDVI benchmarks for kharif cropland: >=0.6 healthy canopy, <=0.25 bare/failed
NDVI_HEALTHY = 0.60
NDVI_FAILED = 0.25


def _adate(d: date) -> str:
    return f"A{d.year}{d.timetuple().tm_yday:03d}"


def get_ndvi_signal(district: str) -> dict:
    """Return NDVI stress signal for district HQ pixel. Cache fallback."""
    d = find_district(district)
    if not d:
        return {"error": f"Unknown district/taluka: {district}"}

    try:
        end = date.today()
        start = end - timedelta(days=95)  # ~5-6 MOD13Q1 16-day composites
        r = requests.get(
            ORNL_URL,
            params={
                "latitude": d["lat"],
                "longitude": d["lon"],
                "startDate": _adate(start),
                "endDate": _adate(end),
                "kmAboveBelow": 1,
                "kmLeftRight": 1,
                "band": "250m_16_days_NDVI",
            },
            headers={"Accept": "application/json"},
            timeout=40,
        )
        r.raise_for_status()
        subset = r.json().get("subset", [])
        composites = []
        for comp in subset:
            vals = [v * SCALE for v in comp.get("data", []) if isinstance(v, (int, float)) and v != -3000]
            if vals:
                composites.append({"date": comp.get("calendar_date"), "ndvi": sum(vals) / len(vals)})
        if not composites:
            raise ValueError("no valid NDVI composites returned")

        latest = composites[-1]
        season_mean = sum(c["ndvi"] for c in composites) / len(composites)
        # stress rises as latest NDVI falls from healthy toward failed
        stress = (NDVI_HEALTHY - latest["ndvi"]) / (NDVI_HEALTHY - NDVI_FAILED)
        result = {
            "district": d["name"],
            "latest_ndvi": round(latest["ndvi"], 3),
            "latest_composite_date": latest["date"],
            "season_mean_ndvi": round(season_mean, 3),
            "composites_used": len(composites),
            "ndvi_signal": round(clamp01(stress), 3),
            "source": "NASA MODIS MOD13Q1 via ORNL Subsets API (modis.ornl.gov)",
            "cached": False,
        }
        cache_put("ndvi", d["name"], result)
        return result
    except Exception as e:
        cached = cache_get("ndvi", d["name"])
        if cached:
            cached["fallback_reason"] = str(e)
            return cached
        return {"error": f"NDVI fetch failed and no cache: {e}", "district": d["name"]}


if __name__ == "__main__":
    import json, sys
    print(json.dumps(get_ndvi_signal(sys.argv[1] if len(sys.argv) > 1 else "Amravati"), indent=2))
