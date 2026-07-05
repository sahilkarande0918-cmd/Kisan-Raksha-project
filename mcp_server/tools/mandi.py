"""Mandi price deviation signal — Agmarknet daily prices via data.gov.in.

Fetches the latest modal price for a crop in (or nearest to) a district and
computes the % gap below MSP. Signal = gap fraction vs MSP, 0..1.
Resource: 9ef84268-d588-465a-a308-a864a43d0070
"Current Daily Price of Various Commodities from Various Markets (Mandi)".
"""
import json
import statistics
import subprocess
from urllib.parse import urlencode

from .common import cache_get, cache_put, clamp01, crop_calendar, find_district, get_env

RESOURCE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# Agmarknet Maharashtra 2025-26 season modal-price averages (Rs/quintal).
# Used only when zero markets report arrivals (crop off-season).
SEASONAL_BASELINE_RS_QTL = {
    "cotton": 7100,   # traded below MSP 7710 through much of 2025-26
    "soybean": 4350,  # persistently below MSP 5328 in 2025
    "tur": 7250,      # below MSP 8000 in 2025-26 season
}


def _fetch_records(params: dict, retries: int = 2) -> list[dict]:
    # data.gov.in's WAF tarpits Python's TLS/HTTP fingerprint but serves curl
    # (Windows Schannel) fine — so shell out to curl for this API only.
    base = {
        "api-key": get_env("DATA_GOV_IN_API_KEY"),
        "format": "json",
        "limit": 50,
    }
    url = f"{RESOURCE_URL}?{urlencode({**base, **params})}"
    last_err: Exception = RuntimeError("no attempt made")
    for _ in range(retries + 1):
        try:
            out = subprocess.run(
                ["curl", "-s", "--max-time", "40", url],
                capture_output=True, text=True, timeout=50, check=True,
            )
            return json.loads(out.stdout).get("records", [])
        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
            last_err = e
    raise last_err


def get_mandi_signal(crop: str, district: str) -> dict:
    """Return price-stress signal for crop near district. Cache fallback."""
    d = find_district(district)
    if not d:
        return {"error": f"Unknown district/taluka: {district}"}
    cal = crop_calendar()["crops"]
    crop_key = crop.strip().lower()
    if crop_key not in cal:
        return {"error": f"Unknown crop: {crop}. Known: {list(cal)}"}
    info = cal[crop_key]
    commodity = info["agmarknet_commodity"]
    msp = info["msp_rs_per_quintal"]
    cache_key = f"{d['name']}:{crop_key}"

    try:
        # widening scope until we find live rows: district → state → national
        records = _fetch_records({
            "filters[state]": "Maharashtra",
            "filters[district]": d["name"],
            "filters[commodity]": commodity,
        })
        scope = "district"
        if not records:
            records = _fetch_records({
                "filters[state]": "Maharashtra",
                "filters[commodity]": commodity,
            })
            scope = "state"
        if not records:
            records = _fetch_records({"filters[commodity]": commodity})
            scope = "national"
        prices = []
        for rec in records:
            try:
                p = float(rec.get("modal_price") or 0)
                if p > 100:  # filter out zero/garbage rows
                    prices.append(p)
            except (TypeError, ValueError):
                continue
        if not prices:
            raise ValueError(f"no live mandi price rows for {commodity}")

        market_price = statistics.median(prices)  # robust to single-market outliers
        gap_pct = max(0.0, (msp - market_price) / msp) * 100
        result = {
            "district": d["name"],
            "crop": crop_key,
            "commodity": commodity,
            "market_price_rs_qtl": round(market_price, 0),
            "msp_rs_qtl": msp,
            "gap_below_msp_pct": round(gap_pct, 1),
            "price_signal": round(clamp01(gap_pct / 40), 3),  # 40% below MSP = max stress
            "markets_sampled": len(prices),
            "scope": scope,
            "source": "Agmarknet via data.gov.in (Ministry of Agriculture)",
            "cached": False,
        }
        cache_put("mandi", cache_key, result)
        return result
    except Exception as e:
        cached = cache_get("mandi", cache_key)
        if cached:
            cached["fallback_reason"] = str(e)
            return cached
        # last resort: documented seasonal-average baseline (Agmarknet 2025-26
        # season averages) — keeps the pipeline alive when the crop is
        # off-season and no market anywhere reported arrivals today.
        baseline = SEASONAL_BASELINE_RS_QTL.get(crop_key)
        if baseline:
            gap_pct = max(0.0, (msp - baseline) / msp) * 100
            result = {
                "district": d["name"],
                "crop": crop_key,
                "commodity": commodity,
                "market_price_rs_qtl": baseline,
                "msp_rs_qtl": msp,
                "gap_below_msp_pct": round(gap_pct, 1),
                "price_signal": round(clamp01(gap_pct / 40), 3),
                "markets_sampled": 0,
                "scope": "seasonal_baseline",
                "source": "Agmarknet 2025-26 season average (static fallback — no live arrivals)",
                "cached": False,
                "fallback_reason": str(e),
            }
            cache_put("mandi", cache_key, result)
            return result
        return {"error": f"mandi fetch failed and no cache: {e}", "district": d["name"], "crop": crop_key}


if __name__ == "__main__":
    import json, sys
    crop_arg = sys.argv[1] if len(sys.argv) > 1 else "cotton"
    dist_arg = sys.argv[2] if len(sys.argv) > 2 else "Amravati"
    print(json.dumps(get_mandi_signal(crop_arg, dist_arg), indent=2, ensure_ascii=False))
