import csv
import pathlib
import statistics

import numpy as np
import pandas as pd

CACHE_FEATURES = [
    "I_miss_rate",
    "IL_miss_rate",
    "D_read_miss_rate",
    "DL_read_miss_rate",
    "D_write_miss_rate",
    "DL_write_miss_rate",
]

SYSTEM_FEATURES = [
    "system_cpu_percent",
    "system_load_1m",
    "ctx_switches",
]

def telemetry_summary(path):
    with path.open() as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {}

    output = {}

    for field in SYSTEM_FEATURES:
        values = [float(row[field]) for row in rows]
        output[field] = statistics.mean(values)

    return output

def main():
    source = pathlib.Path("results/cache_features_labeled.csv")
    df = pd.read_csv(source)
    records = []

    for _, row in df.iterrows():
        annotation = pathlib.Path(row["annotation_file"])
        telemetry = annotation.parent / "telemetry.csv"

        if not telemetry.exists():
            continue

        item = row.to_dict()
        item.update(telemetry_summary(telemetry))
        records.append(item)

    result = pd.DataFrame(records)

    if result.empty:
        raise SystemExit("No records with both cache and telemetry data")

    result.to_csv("results/cache_features_with_load.csv", index=False)

    steady = result[result["mode"] == "steady"]

    if len(steady) < 3:
        raise SystemExit("At least three steady records are required")

    calibration_rows = []

    for feature in CACHE_FEATURES:
        x = steady[SYSTEM_FEATURES].astype(float).to_numpy()
        y = steady[feature].astype(float).to_numpy()

        design = np.column_stack([np.ones(len(x)), x])
        coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)

        all_x = result[SYSTEM_FEATURES].astype(float).to_numpy()
        all_design = np.column_stack([np.ones(len(all_x)), all_x])
        expected = all_design @ coefficients

        residual_column = feature + "_residual"
        result[residual_column] = result[feature] - expected

        steady_scale = result.loc[
            result["mode"] == "steady",
            residual_column
        ].std()

        if not steady_scale or np.isnan(steady_scale):
            steady_scale = 1e-9

        result[feature + "_z"] = (
            result[residual_column].abs() / steady_scale
        )

        calibration_rows.append({
            "feature": feature,
            "intercept": coefficients[0],
            "system_cpu_coefficient": coefficients[1],
            "system_load_coefficient": coefficients[2],
            "ctx_switches_coefficient": coefficients[3],
        })

    z_columns = [feature + "_z" for feature in CACHE_FEATURES]
    result["calibrated_residual_score"] = result[z_columns].mean(axis=1)

    result.to_csv("results/cache_load_calibrated.csv", index=False)

    pd.DataFrame(calibration_rows).to_csv(
        "results/load_calibration_coefficients.csv",
        index=False
    )

    print("records=", len(result))
    print("\nMean calibrated residual score by mode:")
    print(
        result.groupby("mode")["calibrated_residual_score"]
        .agg(["count", "mean", "std", "min", "max"])
        .round(6)
    )

if __name__ == "__main__":
    main()
