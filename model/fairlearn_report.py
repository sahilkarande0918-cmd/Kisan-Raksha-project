"""Fairlearn bias audit for the FSI model (mandatory — rubric slide 14 §8.3).

The FSI drives officer alerts for a vulnerable population, so we audit whether
model error or alert rates differ systematically across groups:
- sensitive feature 1: region (Vidarbha vs Marathwada)
- sensitive feature 2: crop (proxy for farmer segment)

Outputs model/fairlearn_report.json + a human-readable markdown summary.
An equalized-odds style check on the critical-alert decision (FSI > 75):
false-negative rate parity matters most — a missed alert is a missed farmer.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fairlearn.metrics import MetricFrame, false_negative_rate, false_positive_rate, selection_rate
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import DATASET_DIR, MODEL_DIR  # noqa: E402
from model.train_fsi import FEATURES, prepare  # noqa: E402

CRITICAL = 75


def audit(test: pd.DataFrame, pred: np.ndarray, sensitive: str) -> dict:
    y_true = (test["financial_stress"] > CRITICAL).astype(int)
    y_pred = (pred > CRITICAL).astype(int)
    mf = MetricFrame(
        metrics={
            "alert_rate": selection_rate,
            "false_negative_rate": false_negative_rate,
            "false_positive_rate": false_positive_rate,
        },
        y_true=y_true, y_pred=y_pred, sensitive_features=test[sensitive])
    mae_frame = MetricFrame(
        metrics=mean_absolute_error,
        y_true=test["financial_stress"], y_pred=pred, sensitive_features=test[sensitive])
    return {
        "by_group": {str(k): {m: round(float(v), 4) for m, v in row.items()}
                     for k, row in mf.by_group.iterrows()},
        "mae_by_group": {str(k): round(float(v), 3) for k, v in mae_frame.by_group.items()},
        "fnr_gap": round(float(mf.difference()["false_negative_rate"]), 4),
        "alert_rate_gap": round(float(mf.difference()["alert_rate"]), 4),
        "mae_gap": round(float(mae_frame.difference()), 3),
    }


def main() -> None:
    df = prepare(pd.read_csv(DATASET_DIR / "maharashtra_ag_stress_dataset.csv"))
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    _, test_idx = next(splitter.split(df, groups=df["taluka"]))
    test = df.iloc[test_idx]
    bundle = joblib.load(MODEL_DIR / "risk_model.pkl")
    pred = np.clip(bundle["model"].predict(test[FEATURES]), 0, 100)

    report = {
        "model": "LightGBM FSI regressor",
        "decision_audited": f"critical alert (FSI > {CRITICAL})",
        "note": "false_negative_rate = share of truly-critical cases NOT alerted; "
                "this is the harm metric for farmers.",
        "region": audit(test, pred, "region"),
        "crop": audit(test, pred, "crop"),
    }
    # simple pass/fail gates for the doc
    report["gates"] = {
        "fnr_gap_region_lt_0.10": report["region"]["fnr_gap"] < 0.10,
        "fnr_gap_crop_lt_0.10": report["crop"]["fnr_gap"] < 0.10,
        "mae_gap_region_lt_2.0": report["region"]["mae_gap"] < 2.0,
    }
    with open(MODEL_DIR / "fairlearn_report.json", "w") as f:
        json.dump(report, f, indent=2)

    lines = ["# Fairlearn Bias Report — KisaanRaksha FSI model\n",
             f"Decision audited: **critical alert (FSI > {CRITICAL})** on held-out talukas.\n"]
    for sf in ("region", "crop"):
        r = report[sf]
        lines.append(f"\n## By {sf}\n")
        lines.append("| group | alert rate | FNR | FPR | MAE |")
        lines.append("|---|---|---|---|---|")
        for g, m in r["by_group"].items():
            lines.append(f"| {g} | {m['alert_rate']:.3f} | {m['false_negative_rate']:.3f} "
                         f"| {m['false_positive_rate']:.3f} | {r['mae_by_group'][g]:.2f} |")
        lines.append(f"\nGaps — FNR: {r['fnr_gap']}, alert rate: {r['alert_rate_gap']}, MAE: {r['mae_gap']}")
    lines.append("\n## Gates\n")
    for gate, ok in report["gates"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — {gate}")
    (MODEL_DIR / "fairlearn_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
