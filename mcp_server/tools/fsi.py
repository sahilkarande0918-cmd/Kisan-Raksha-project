"""Financial Stress Index — live computation combining the 4 signals.

Pulls live drought / price / NDVI signals, computes repayment proximity from
the crop calendar, feeds all through the trained LightGBM model, and returns
FSI 0-100 with a full signal breakdown. FSI > 75 = critical.
"""
import hashlib
from datetime import date

import joblib
import numpy as np
import pandas as pd

from .common import MODEL_DIR, cache_get, cache_put, crop_calendar, find_district
from .mandi import get_mandi_signal
from .ndvi import get_ndvi_signal
from .weather import get_weather_signal

CRITICAL_THRESHOLD = 75
_bundle = None


def _model():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_DIR / "risk_model.pkl")
    return _bundle


def _repayment_proximity(month: int, window: dict) -> float:
    def in_window(m, s, e):
        return (s <= m <= e) if s <= e else (m >= s or m <= e)
    if in_window(month, window["start_month"], window["end_month"]):
        return 1.0
    for lead, val in ((1, 0.6), (2, 0.3)):
        if in_window((month + lead - 1) % 12 + 1, window["start_month"], window["end_month"]):
            return val
    return 0.0


# Replays the Oct-Nov 2024 Vidarbha stress pattern (drought + cotton glut +
# harvest-loan squeeze) for demo purposes. Always labeled "SIMULATION".
SIMULATED_CRISIS = {
    "weather": {"drought_signal": 0.70, "deficit_pct": 58.0, "cached": False},
    "mandi": {"price_signal": 0.45, "gap_below_msp_pct": 18.0,
              "market_price_rs_qtl": 4200, "msp_rs_qtl": 7710, "cached": False},
    "ndvi": {"ndvi_signal": 0.60, "latest_ndvi": 0.39, "cached": False},
    "month": 1,  # peak of cotton loan-repayment window (Jan-Mar)
}


def compute_fsi(district: str, crop: str = "cotton", simulate_crisis: bool = False) -> dict:
    """Compute the live Financial Stress Index for a district + crop.

    simulate_crisis=True replays a documented 2024-style drought/price-crash
    scenario instead of live signals (demo mode, clearly labeled).
    """
    d = find_district(district)
    if not d:
        return {"error": f"Unknown district/taluka: {district}"}
    cal = crop_calendar()["crops"]
    crop_key = crop.strip().lower()
    if crop_key not in cal:
        crop_key = d["major_crops"][0]

    if simulate_crisis:
        # deterministic per-district spread so the demo heatmap shows a
        # realistic gradient (epicentre-style), not one flat value
        # Amravati is the scenario epicentre (matches the demo narrative)
        epicentre = {"Amravati": 0.0, "Yavatmal": -0.04}
        jitter = epicentre.get(
            d["name"],
            (int(hashlib.md5(d["name"].encode()).hexdigest(), 16) % 100) / 100 - 0.62)
        weather = dict(SIMULATED_CRISIS["weather"])
        weather["drought_signal"] = round(min(1.0, max(0.15, weather["drought_signal"] + jitter * 0.9)), 3)
        weather["deficit_pct"] = round(weather["drought_signal"] * 82, 1)
        mandi = dict(SIMULATED_CRISIS["mandi"])
        ndvi = dict(SIMULATED_CRISIS["ndvi"])
        ndvi["ndvi_signal"] = round(min(1.0, max(0.1, ndvi["ndvi_signal"] + jitter * 0.7)), 3)
        ndvi["latest_ndvi"] = round(0.60 - ndvi["ndvi_signal"] * 0.35, 3)
    else:
        weather = get_weather_signal(d["name"])
        mandi = get_mandi_signal(crop_key, d["name"])
        ndvi = get_ndvi_signal(d["name"])

    signals = {
        "drought_signal": weather.get("drought_signal"),
        "price_signal": mandi.get("price_signal"),
        "ndvi_signal": ndvi.get("ndvi_signal"),
    }
    missing = [k for k, v in signals.items() if v is None]
    if missing:
        cached = cache_get("fsi", f"{d['name']}:{crop_key}")
        if cached:
            cached["fallback_reason"] = f"live signals unavailable: {missing}"
            return cached
        return {"error": f"cannot compute FSI, missing signals: {missing}", "district": d["name"]}

    month = SIMULATED_CRISIS["month"] if simulate_crisis else date.today().month
    repay = _repayment_proximity(month, cal[crop_key]["loan_repayment_window"])
    b = _model()
    row = pd.DataFrame([{
        "drought_signal": signals["drought_signal"], "price_signal": signals["price_signal"],
        "ndvi_signal": signals["ndvi_signal"], "repayment_proximity": repay,
        "month": month, "crop_code": b["crop_codes"][crop_key],
        "region_code": b["region_codes"][d["region"]],
    }])
    fsi = float(np.clip(b["model"].predict(row)[0], 0, 100))

    result = {
        "district": d["name"],
        "region": d["region"],
        "crop": crop_key,
        "fsi": round(fsi, 1),
        "level": "CRITICAL" if fsi > CRITICAL_THRESHOLD else ("HIGH" if fsi > 55 else ("MODERATE" if fsi > 35 else "LOW")),
        "critical_threshold": CRITICAL_THRESHOLD,
        "signals": {
            "drought": {"value": signals["drought_signal"], "deficit_pct": weather.get("deficit_pct"),
                        "cached": weather.get("cached", False)},
            "price": {"value": signals["price_signal"], "gap_below_msp_pct": mandi.get("gap_below_msp_pct"),
                      "market_price": mandi.get("market_price_rs_qtl"), "msp": mandi.get("msp_rs_qtl"),
                      "cached": mandi.get("cached", False)},
            "ndvi": {"value": signals["ndvi_signal"], "latest_ndvi": ndvi.get("latest_ndvi"),
                     "cached": ndvi.get("cached", False)},
            "repayment_proximity": repay,
        },
        "model": "LightGBM (model/risk_model.pkl)",
        "cached": False,
    }
    if simulate_crisis:
        result["mode"] = "SIMULATION — replays Oct-Nov 2024 Vidarbha stress pattern, not live data"
    else:
        cache_put("fsi", f"{d['name']}:{crop_key}", result)
    return result


if __name__ == "__main__":
    import json, sys
    dist = sys.argv[1] if len(sys.argv) > 1 else "Amravati"
    crop_arg = sys.argv[2] if len(sys.argv) > 2 else "cotton"
    print(json.dumps(compute_fsi(dist, crop_arg), indent=2, ensure_ascii=False))
