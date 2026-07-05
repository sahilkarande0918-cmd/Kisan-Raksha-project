# Fairlearn Bias Report — KisaanRaksha FSI model

Decision audited: **critical alert (FSI > 75)** on held-out talukas.


## By region

| group | alert rate | FNR | FPR | MAE |
|---|---|---|---|---|
| Marathwada | 0.077 | 0.229 | 0.015 | 3.75 |
| Vidarbha | 0.064 | 0.205 | 0.011 | 3.74 |

Gaps — FNR: 0.024, alert rate: 0.0134, MAE: 0.015

## By crop

| group | alert rate | FNR | FPR | MAE |
|---|---|---|---|---|
| cotton | 0.048 | 0.269 | 0.011 | 3.88 |
| soybean | 0.093 | 0.196 | 0.015 | 3.68 |
| tur | 0.075 | 0.210 | 0.014 | 3.65 |

Gaps — FNR: 0.0736, alert rate: 0.0453, MAE: 0.226

## Gates

- PASS — fnr_gap_region_lt_0.10
- PASS — fnr_gap_crop_lt_0.10
- PASS — mae_gap_region_lt_2.0