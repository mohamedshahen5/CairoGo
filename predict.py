"""predict.py — CairoGo Probability of Request Failure Predictor
Implements the PREDICT_CONTRACT CLI:
    python predict.py --input in.csv --output out.csv

Maintained by Member B (Modeler) in collaboration with Member A (Data Cleaning).
Uses Member A's prep.clean_requests to ensure unit shift and zone repairs are applied.
"""

import argparse
import os
import sys
import joblib
import numpy as np
import pandas as pd

# Import Member A's standardized cleaning module
from prep import clean_requests

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")


def predict(input_path: str, output_path: str, model_path: str = MODEL_PATH):
    """Loads input CSV, cleans it using prep.py, generates predictions, and writes output."""
    # 1. Load raw incoming request data
    df_raw = pd.read_csv(input_path)
    if "trip_id" not in df_raw.columns:
        raise ValueError("Input CSV must contain 'trip_id'.")

    trip_ids = df_raw["trip_id"].copy()

    # 2. Member A's shared cleaning:
    # - Repairs unit shift (distance_km miles -> km)
    # - Maps legacy zone names (Agouza -> Agouza District, Badr City -> Badr City District)
    # - Drops any leakage columns if accidentally present
    # - Imputes missing weather
    df_clean = clean_requests(df_raw, is_training=False)

    # 3. Load trained model artifact (trained by Member B)
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        # Predict probability of class 1 (request_failed)
        p_fail = model.predict_proba(df_clean)[:, 1]
    else:
        # Fallback heuristic predictor if model artifact is not yet trained/exported:
        # Higher surge and longer distance correlate with failure
        sys.stderr.write(f"Warning: {model_path} not found. Running baseline fallback.\n")
        dist = df_clean["distance_km"].fillna(10.0)
        surge = df_clean["surge_multiplier"].fillna(1.0)
        score = 0.20 + 0.05 * (surge - 1.0) + 0.005 * (dist - 10.0)
        p_fail = np.clip(score, 0.01, 0.99)

    # 4. Write required output contract: exactly trip_id,p_fail
    out_df = pd.DataFrame({
        "trip_id": trip_ids,
        "p_fail": np.round(p_fail, 4)
    })
    out_df.to_csv(output_path, index=False)
    print(f"Predictions written to {output_path} ({len(out_df)} rows).")


def main():
    parser = argparse.ArgumentParser(description="CairoGo Failure Predictor CLI")
    parser.add_argument("--input", required=True, help="Path to input CSV (e.g. holdout_inputs.csv)")
    parser.add_argument("--output", required=True, help="Path to write predictions CSV (trip_id,p_fail)")
    parser.add_argument("--model", default=MODEL_PATH, help="Path to model artifact (default: model.joblib)")
    args = parser.parse_args()

    predict(args.input, args.output, args.model)


if __name__ == "__main__":
    main()
