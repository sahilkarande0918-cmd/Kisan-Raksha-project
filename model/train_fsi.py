"""Train the LightGBM Financial Stress Index model on the synthetic dataset.

Regression target: financial_stress 0-100. Features: the four signals plus
month/crop/region context. Saves model + metrics to model/risk_model.pkl.
"""
import json
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server.tools.common import DATASET_DIR, MODEL_DIR  # noqa: E402

FEATURES = ["drought_signal", "price_signal", "ndvi_signal", "repayment_proximity",
            "month", "crop_code", "region_code"]
CROP_CODES = {"cotton": 0, "soybean": 1, "tur": 2}
REGION_CODES = {"Vidarbha": 0, "Marathwada": 1}


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["crop_code"] = df["crop"].map(CROP_CODES)
    df["region_code"] = df["region"].map(REGION_CODES)
    return df


def main() -> None:
    df = prepare(pd.read_csv(DATASET_DIR / "maharashtra_ag_stress_dataset.csv"))
    # group split by taluka so the model is evaluated on unseen talukas
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(df, groups=df["taluka"]))
    train, test = df.iloc[train_idx], df.iloc[test_idx]

    model = lgb.LGBMRegressor(
        n_estimators=400, learning_rate=0.06, num_leaves=31,
        subsample=0.9, colsample_bytree=0.9, random_state=42, verbose=-1)
    model.fit(train[FEATURES], train["financial_stress"])

    pred = np.clip(model.predict(test[FEATURES]), 0, 100)
    mae = mean_absolute_error(test["financial_stress"], pred)
    r2 = r2_score(test["financial_stress"], pred)
    # alert-level agreement (critical = FSI > 75)
    crit_true, crit_pred = test["financial_stress"] > 75, pred > 75
    recall = float((crit_true & crit_pred).sum() / max(crit_true.sum(), 1))
    precision = float((crit_true & crit_pred).sum() / max(crit_pred.sum(), 1))

    metrics = {
        "test_mae": round(float(mae), 2),
        "test_r2": round(float(r2), 3),
        "critical_alert_recall": round(recall, 3),
        "critical_alert_precision": round(precision, 3),
        "n_train": len(train), "n_test": len(test),
        "features": FEATURES,
        "feature_importance": dict(zip(FEATURES, [int(v) for v in model.feature_importances_])),
    }
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES,
                 "crop_codes": CROP_CODES, "region_codes": REGION_CODES},
                MODEL_DIR / "risk_model.pkl")
    with open(MODEL_DIR / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
