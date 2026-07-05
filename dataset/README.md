# Maharashtra Agricultural Stress Dataset (synthetic, grounded)

`maharashtra_ag_stress_dataset.csv` — 13,644 rows · (district × taluka × crop × year × month) for 16 Vidarbha + Marathwada districts, 2023–2025.

**No real farmer PII.** Fully reproducible: `python dataset/build_dataset.py` (seeded RNG).

## Columns

| column | meaning |
|---|---|
| district, taluka, region | real administrative units (Vidarbha / Marathwada) |
| crop | cotton, soybean or tur (district's actual major crops) |
| year, month | synthetic panel index |
| drought_signal | 0–1 rainfall-deficit stress |
| price_signal | 0–1 mandi-price-below-MSP stress (40% gap = 1.0) |
| ndvi_signal | 0–1 vegetation stress from NDVI |
| repayment_proximity | 0–1 nearness to crop-loan due window |
| financial_stress | label 0–100 |

## Grounding

- District/taluka lists and region tags are real (Census / LGD names).
- Crop calendars and MSP 2025-26 from CACP; loan repayment windows follow harvest.
- Regional drought propensity: Marathwada mean deficit > Vidarbha (IMD drought history).
- Price-gap distributions per crop match observed 2024–26 Agmarknet-vs-MSP gaps (soybean 15–25% below MSP; cotton 5–12%).
- NDVI seasonality follows the MODIS kharif curve (trough pre-sowing, peak Sep–Oct).

## Label construction

`financial_stress = 34·drought + 26·price + 22·ndvi + 18·repay + amplification + noise`

Amplification (`22·drought·repay + 14·price·repay + 10·drought·ndvi`) encodes the core domain insight: distress spikes when **crop failure coincides with the loan repayment deadline** — the documented pattern behind farmer suicide clustering in Oct–Jan.

## Intended use

Training/benchmarking early-warning models for agrarian financial distress. Candidate for IEEE Dataport publication per Hack4Humanity organizer support.
