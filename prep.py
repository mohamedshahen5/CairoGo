"""prep.py — CairoGo Operations Data Preparation & Shared Preprocessing Module
Author: Member A (Data Audit, Cleaning & Frozen Split)

This module is the single source of truth for data cleaning across the team:
- Used in dataAnalysis.ipynb / team_analysis.ipynb
- Used in predict.py (Member B)
- Used in Task 5 (Local-k)
- Used in Task 6 (Recent-data repair & evaluation)
Nobody writes duplicate cleaning code.
"""

from typing import Optional, Tuple
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants & Reference Maps
# ---------------------------------------------------------------------------
# Date the new app version rolled out with unit shift (miles instead of km)
SHIFT_DATE = "2026-08-26"
MILES_TO_KM = 1.609344

# Legacy zone name mapping from zones.csv (legacy_name -> zone_name)
ZONE_MAPPING = {
    "Agouza": "Agouza District",
    "Badr City": "Badr City District",
}

# Columns recorded strictly after request time (Target Leakage)
LEAKING_COLUMNS = [
    "actual_trip_time_min",
    "cancel_reason",
    "fare_final",
    "support_ticket_flag",
]

# Standard request-time feature columns expected by models
REQUEST_NUMERIC_FEATURES = [
    "distance_km",
    "surge_multiplier",
    "est_fare",
    "eta_estimate_min",
]

REQUEST_CATEGORICAL_FEATURES = [
    "pickup_zone",
    "dropoff_zone",
    "weather",
    "payment_method",
    "service_level",
]

# Shared frozen validation cut date: last 14 days of trips.csv (Aug 12 - Aug 25)
# Consistent across all team members for Task 3, 5, calibration, and policy tests.
FROZEN_CUT_DATE = "2026-08-12"


# ---------------------------------------------------------------------------
# Core Cleaning Function
# ---------------------------------------------------------------------------
def clean_requests(
    df: pd.DataFrame,
    is_training: bool = False,
    force_unit_fix: Optional[bool] = None,
    drop_leakage: bool = True,
    fill_missing: bool = True,
) -> pd.DataFrame:
    """Cleans a DataFrame of ride requests (trips, recent, holdout, or live requests).
    
    Operations performed:
    1. Repairs unit shift: converts distance_km from miles to km for requests
       on or after 2026-08-26, or when force_unit_fix is True.
    2. Fixes zone names: replaces legacy zone names with current names.
    3. Drops target leakage columns: removes post-request features if present.
    4. Handles missing values: fills missing weather and flags informative missingness.
    
    Parameters:
        df: Input DataFrame.
        is_training: True if processing historical trips.csv (before shift).
        force_unit_fix: Explicitly force or disable distance unit conversion.
                        If None, auto-detected from request_ts or dataset type.
        drop_leakage: Whether to drop leaking post-request columns (default True).
        fill_missing: Whether to handle missing values (default True).
        
    Returns:
        Cleaned copy of the DataFrame.
    """
    clean_df = df.copy()

    # 1. Zone Name Standardization (Legacy to Current)
    for col in ["pickup_zone", "dropoff_zone"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].replace(ZONE_MAPPING)

    # 2. Unit Shift Repair (miles -> km)
    # If explicit flag given, obey it
    if force_unit_fix is True:
        clean_df["distance_km"] = clean_df["distance_km"] * MILES_TO_KM
    elif force_unit_fix is False:
        pass
    else:
        # Auto-detect using request_ts
        if "request_ts" in clean_df.columns:
            ts = pd.to_datetime(clean_df["request_ts"], errors="coerce")
            # If all dates are on or after shift date, or for specific rows
            mask = ts >= pd.to_datetime(SHIFT_DATE)
            if mask.any():
                clean_df.loc[mask, "distance_km"] = clean_df.loc[mask, "distance_km"] * MILES_TO_KM
        else:
            # If no timestamp is provided (e.g., live scoring in predict.py for new requests),
            # all new production data comes from post-shift versions:
            if not is_training:
                clean_df["distance_km"] = clean_df["distance_km"] * MILES_TO_KM

    # 3. Drop Target Leakage Columns
    if drop_leakage:
        cols_to_drop = [c for c in LEAKING_COLUMNS if c in clean_df.columns]
        if cols_to_drop:
            clean_df = clean_df.drop(columns=cols_to_drop)

    # 4. Handle Missing Values
    if fill_missing:
        # Weather missingness is random (~4.4%), impute with 'unknown' or 'clear'
        if "weather" in clean_df.columns:
            clean_df["weather"] = clean_df["weather"].fillna("unknown")

        # Driver rating missingness is informative (MNAR: new drivers fail +4.4% more)
        if "rating_avg" in clean_df.columns:
            clean_df["rating_isna"] = clean_df["rating_avg"].isna().astype(int)
            # median imputation for numeric rating
            clean_df["rating_avg"] = clean_df["rating_avg"].fillna(clean_df["rating_avg"].median())

    return clean_df


# ---------------------------------------------------------------------------
# Frozen Time Split
# ---------------------------------------------------------------------------
def get_train_val_split(
    trips_df: pd.DataFrame,
    cut_date: str = FROZEN_CUT_DATE,
    as_xy: bool = False,
    target_col: str = "request_failed",
) -> Tuple:
    """Splits trips.csv chronologically into frozen Train and Validation sets.
    
    Cut Date: 2026-08-12 (Last 14 days of trips.csv as validation).
    - Train: 2026-05-01 through 2026-08-11 (23,664 requests, ~87.1%)
    - Val:   2026-08-12 through 2026-08-25 (3,518 requests, ~12.9%)
    
    This frozen split is shared by:
    - Member B: model comparison (Task 3: Logistic, HGB, kNN, NN)
    - Member C: segmentation and feature scaling (Task 4)
    - Member D: Local-k validation and decision policy simulation (Tasks 5, 8)
    
    Parameters:
        trips_df: Cleaned trips DataFrame.
        cut_date: Split cut date string 'YYYY-MM-DD'.
        as_xy: If True, returns (X_train, y_train, X_val, y_val).
               If False, returns (train_df, val_df).
        target_col: Target column name ('request_failed').
        
    Returns:
        (train_df, val_df) OR (X_train, y_train, X_val, y_val)
    """
    df = trips_df.copy()
    if "request_ts" not in df.columns:
        raise ValueError("trips_df must contain 'request_ts' to perform time split.")

    ts = pd.to_datetime(df["request_ts"])
    split_dt = pd.to_datetime(cut_date)

    train_mask = ts < split_dt
    val_mask = ts >= split_dt

    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()

    if as_xy:
        feature_cols = [
            c for c in train_df.columns
            if c not in [target_col, "trip_id", "customer_id", "driver_id", "request_ts"]
        ]
        X_train = train_df[feature_cols]
        y_train = train_df[target_col].values
        X_val = val_df[feature_cols]
        y_val = val_df[target_col].values
        return X_train, y_train, X_val, y_val

    return train_df, val_df


# ---------------------------------------------------------------------------
# Optional Metadata Enrichment
# ---------------------------------------------------------------------------
def enrich_requests(
    requests_df: pd.DataFrame,
    drivers_df: Optional[pd.DataFrame] = None,
    zones_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Enriches requests with driver attributes (rating, experience) and zone types."""
    df = requests_df.copy()

    if drivers_df is not None and "driver_id" in df.columns:
        driver_cols = [c for c in ["driver_id", "vehicle_type", "experience_months", "rating_avg"] if c in drivers_df.columns]
        df = df.merge(drivers_df[driver_cols], on="driver_id", how="left")

    if zones_df is not None and "pickup_zone" in df.columns:
        # Map pickup zone to zone_type
        z_map = dict(zip(zones_df["zone_name"], zones_df["zone_type"]))
        if "legacy_name" in zones_df.columns:
            z_map.update(dict(zip(zones_df["legacy_name"], zones_df["zone_type"])))
        df["pickup_zone_type"] = df["pickup_zone"].map(z_map)

    return df
