# CairoGo Operations — Team Analysis & Repository Documentation

## 1. Project Overview & Team Roles
This repository implements the end-to-end operational dispatch failure prediction, customer segmentation, and decision policy for CairoGo.

* **Member A (Data Cleaner / Auditor):**
  * Built `prep.py`: centralized data cleaning and preprocessing (`clean_requests`).
  * Defined and froze the chronological time split (`FROZEN_CUT_DATE = 2026-08-12`).
  * Completed **Task 1** (Audit: Join, Shift, Leakage, Confounding), **Task 2** (Missingness & MNAR), and **Task 6** (Recent-period degradation audit & repair).
* **Member B (Predictive Modeler):**
  * Model exploration (Logistic, HGB, kNN, Neural Net) and final predictor pipeline.
  * Authors `predict.py` using `prep.clean_requests`.
* **Member C (Customer Segmentation):**
  * K-Means clustering, silhouette/ARI diagnostics, and segment interpretations.
* **Member D (Local-k & Decision Analysis):**
  * Spatial kNN / Local-k implementation and policy simulation under dispatch capacity.

---

## 2. Frozen Time Split (Shared by Members B, C, D)

To prevent data leakage and guarantee that all team members benchmark models on the identical training and validation observations, the team uses a single **frozen chronological time split**:

* **Cut Date:** **`2026-08-12`** (Last 14 days of `trips.csv` as validation, as specified in `memo_3`)
* **Training Set:** `2026-05-01` through `2026-08-11` ($23,664$ requests, $\approx 87.1\%$)
* **Validation Set:** `2026-08-12` through `2026-08-25` ($3,518$ requests, $\approx 12.9\%$)

### How to use the Frozen Split:
```python
from prep import clean_requests, get_train_val_split

trips_clean = clean_requests(trips, is_training=True)
train_df, val_df = get_train_val_split(trips_clean)
# Or extract (X, y) directly:
X_train, y_train, X_val, y_val = get_train_val_split(trips_clean, as_xy=True)
```
Every model (Logistic, HGB, kNN, Local-k, MLP), probability calibration check, and policy test must be fitted strictly on `train_df` and evaluated on `val_df`.

---

## 3. Shared Preprocessing Module (`prep.py`)

All team members must import and use `clean_requests` from `prep.py`. Nobody writes custom or duplicate cleaning logic.

```python
from prep import clean_requests

# For historical training data:
trips_clean = clean_requests(raw_trips_df, is_training=True)

# For holdout inputs or recent requests:
test_clean = clean_requests(raw_holdout_df, is_training=False)
```

### What `clean_requests(df)` does:
1. **Fixes Zone Names:** Standardizes legacy zone names from `zones.csv`:
   * `"Agouza"` $\to$ `"Agouza District"`
   * `"Badr City"` $\to$ `"Badr City District"`
2. **Repairs Unit Shift:** Automatically converts `distance_km` from **miles to kilometers** ($\times 1.609344$) for all requests on or after `2026-08-26`, as well as incoming production/holdout inputs.
3. **Drops Target Leakage:** Strips post-request columns (`actual_trip_time_min`, `cancel_reason`, `fare_final`, `support_ticket_flag`).
4. **Handles Missing Values:** Imputes missing `weather` (`'unknown'`) and flags missing driver ratings (`rating_isna = 1`).

---

## 4. Summary of Member A Results (`results.json`)

### Task 1 — Data Audit
* **1a. Join:**
  * `unmatched_before`: `0.090317` (2,455 rows, ~9.03%)
  * `unmatched_zones`: `["Agouza", "Badr City"]`
  * `fix`: `"Mapped legacy pickup-zone names to current zone names using zones.csv"`
* **1b. Unit Shift:**
  * `field`: `"distance_km"`
  * `day_estimate`: `"2026-08-26"`
  * *Cause:* Rollout of new app version changed measurement from km to miles ($1\text{ mile} \approx 1.60934\text{ km}$).
* **1c. Leakage:**
  * `columns_removed`: `["actual_trip_time_min", "cancel_reason", "fare_final", "support_ticket_flag"]`
  * `single_feature_auc`:
    * `actual_trip_time_min`: `1.0` (missing on all failed trips)
    * `cancel_reason`: `1.0` (present only on failed trips)
    * `fare_final`: `1.0` (missing on all failed trips)
    * `support_ticket_flag`: `0.6173` (filed more often after failures)
* **1d. Confounding (Simpson's Paradox):**
  * `global_slope`: `-0.1897` min/km
  * `within_slope`: `0.4546` min/km (weighted: `0.4672` min/km)
  * `confounder`: `"zone_type"`
  * *Mechanism:* Downtown pickups are short but heavily congested (slow), while airport/suburb pickups are long highway trips (fast). Conditioning on `zone_type` reveals the true positive slope (+0.34 to +0.62 min/km).

### Task 2 — Missingness
* `weather_missing_share`: `0.0440` (4.40%)
* `weather_missing_fail_diff`: `0.0166` (negligible difference, random / MCAR)
* `rating_missing_share`: `0.1191` (11.91% in trips)
* `rating_missing_fail_diff`: `0.0441` (unrated new drivers have 25.1% fail rate vs 20.7% for rated)
* `interpretation`: `"informative"` (Missing Not At Random — unrated drivers fail +4.4% more).

### Task 6 — Recent Period Audit & Repair
* `recall_before_fix`: `0.2709` (27.09% on raw `recent_labelled.csv`)
* `recall_after_fix`: `0.6409` (64.09% after multiplying `distance_km * 1.609344`)
* `improvement`: `+0.3700` (+37.0 percentage points)

---

## 5. Instructions for Member B (`predict.py`)

To ensure that `predict.py` maintains high performance on hidden holdout evaluation batches (which were collected in September 2026, post-app version rollout):

1. **Import `clean_requests`:**
   ```python
   from prep import clean_requests
   ```
2. **Apply in pipeline before scoring:**
   ```python
   df_clean = clean_requests(raw_input_df, is_training=False)
   p_fail = model.predict_proba(df_clean)[:, 1]
   ```
   This automatically multiplies `distance_km` by `1.609344` and resolves legacy zone names.
