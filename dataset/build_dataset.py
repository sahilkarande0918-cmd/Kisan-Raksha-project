"""Build maharashtra_ag_stress_dataset.csv — synthetic-but-grounded training data.

No real farmer PII. Each row = (district, taluka, crop, year, month) with the
four KisaanRaksha signals and a financial-stress label 0-100.

Grounding (documented for IEEE Dataport):
- District list, talukas, region tags: data/maharashtra_districts.json (real).
- Crop calendar + MSP 2025-26: data/crop_calendar.json (real, CACP).
- Rainfall deficit distributions seeded per region from IMD drought history:
  Marathwada is structurally more drought-prone than Vidarbha.
- Price gap distributions seeded from real 2024-26 Agmarknet-vs-MSP gaps
  (soybean traded 15-25% below MSP through 2025; cotton 5-12% below).
- NDVI seasonality follows the MODIS kharif curve (low pre-sowing June,
  peak Sep-Oct, senescence Dec+).
- Label = domain-logic stress formula + interaction amplification + noise;
  the formula reflects that distress peaks when the loan-repayment window
  coincides with crop failure and depressed prices (documented below).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import DATASET_DIR, crop_calendar, districts  # noqa: E402

RNG = np.random.default_rng(42)
YEARS = [2023, 2024, 2025]

# per-region climatology knobs (mean deficit tendency, spread)
REGION_DROUGHT = {"Vidarbha": (0.25, 0.18), "Marathwada": (0.38, 0.20)}
# per-crop price-gap tendency (fraction below MSP), grounded in 2024-26 gaps
CROP_PRICE_GAP = {"cotton": (0.08, 0.06), "soybean": (0.19, 0.08), "tur": (0.09, 0.07)}
# MODIS kharif NDVI seasonal curve by month (healthy year)
NDVI_CURVE = {1: .38, 2: .33, 3: .30, 4: .27, 5: .26, 6: .30, 7: .45, 8: .58, 9: .65, 10: .62, 11: .52, 12: .43}


def month_in_window(month: int, start: int, end: int) -> bool:
    return (start <= month <= end) if start <= end else (month >= start or month <= end)


def repayment_proximity(month: int, window: dict) -> float:
    """1.0 inside the repayment window, ramping up the two months before."""
    if month_in_window(month, window["start_month"], window["end_month"]):
        return 1.0
    for lead, val in ((1, 0.6), (2, 0.3)):
        if month_in_window((month + lead - 1) % 12 + 1, window["start_month"], window["end_month"]):
            return val
    return 0.0


def stress_label(drought, price, ndvi, repay, rng) -> float:
    """Domain-logic ground truth: weighted base + coincidence amplification."""
    base = 34 * drought + 26 * price + 22 * ndvi + 18 * repay
    # distress spikes when crop failure AND repayment deadline coincide
    amplify = 22 * drought * repay + 14 * price * repay + 10 * drought * ndvi
    noise = rng.normal(0, 4.5)
    return float(np.clip(base + amplify + noise, 0, 100))


def build() -> pd.DataFrame:
    cal = crop_calendar()["crops"]
    rows = []
    for d in districts():
        dr_mu, dr_sd = REGION_DROUGHT[d["region"]]
        for taluka in d["talukas"]:
            # stable per-taluka vulnerability offset (soil, irrigation access)
            t_offset = RNG.normal(0, 0.06)
            for crop, info in cal.items():
                if crop not in d["major_crops"]:
                    continue
                gap_mu, gap_sd = CROP_PRICE_GAP[crop]
                for year in YEARS:
                    # year-level shocks shared within a district-year
                    year_drought_shock = RNG.normal(0, 0.10)
                    for month in range(1, 13):
                        monsoon = month in (6, 7, 8, 9)
                        drought = np.clip(
                            RNG.normal(dr_mu + t_offset + year_drought_shock, dr_sd)
                            * (1.25 if monsoon else 0.8), 0, 1)
                        price = np.clip(RNG.normal(gap_mu, gap_sd) / 0.40, 0, 1)
                        ndvi_healthy = NDVI_CURVE[month]
                        ndvi_actual = np.clip(
                            ndvi_healthy * (1 - 0.55 * drought) + RNG.normal(0, 0.03), 0.05, 0.9)
                        ndvi_sig = np.clip((0.60 - ndvi_actual) / 0.35, 0, 1)
                        repay = repayment_proximity(month, info["loan_repayment_window"])
                        label = stress_label(drought, price, ndvi_sig, repay, RNG)
                        rows.append({
                            "district": d["name"], "taluka": taluka, "region": d["region"],
                            "crop": crop, "year": year, "month": month,
                            "drought_signal": round(float(drought), 3),
                            "price_signal": round(float(price), 3),
                            "ndvi_signal": round(float(ndvi_sig), 3),
                            "repayment_proximity": repay,
                            "financial_stress": round(label, 1),
                        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build()
    out = DATASET_DIR / "maharashtra_ag_stress_dataset.csv"
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows -> {out}")
    print(df["financial_stress"].describe().round(1))
    print("critical (>75) share:", round((df.financial_stress > 75).mean() * 100, 1), "%")
