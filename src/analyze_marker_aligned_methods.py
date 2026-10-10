import csv, math, pathlib, statistics, re
import numpy as np

if pathlib.Path("data/processed/marker-aligned").exists():
    ROOT = pathlib.Path("data/processed/marker-aligned")
    DATA = ROOT / "marker-aligned-summary.csv"
    OUT = pathlib.Path("results/tables")
else:
    ROOT = pathlib.Path("results/journal-study/marker-aligned")
    DATA = ROOT / "marker-aligned-summary.csv"
    OUT = ROOT / "final-method-analysis"
OUT.mkdir(parents=True, exist_ok=True)

def parse_float(x):
    try:
        return float(x)
    except:
        return None

def rmse(x):
    return math.sqrt(sum(v*v for v in x) / len(x))

def mae(x):
    return sum(abs(v) for v in x) / len(x)

def robust_location_scale(values):
    med = statistics.median(values)
    mad = statistics.median(abs(v-med) for v in values)
    return med, max(1.4826 * mad, 1e-12)

def ordinary_affine(rows):
    x = np.array([r["simulation"] for r in rows])
    y = np.array([r["hardware"] for r in rows])
    A = np.column_stack([np.ones(len(x)), x])
    return tuple(np.linalg.lstsq(A, y, rcond=None)[0])

def theil_sen(rows):
    slopes = []
    for i in range(len(rows)):
        for j in range(i+1, len(rows)):
            dx = rows[j]["simulation"] - rows[i]["simulation"]
            if abs(dx) > 1e-12:
                dy = rows[j]["hardware"] - rows[i]["hardware"]
                slopes.append(dy / dx)

    slope = statistics.median(slopes)
    intercept = statistics.median(
        r["hardware"] - slope*r["simulation"] for r in rows
    )
    return intercept, slope

def perf_quality(tag):
    path = ROOT / "native-perf" / f"{tag}.csv"
    text = path.read_text(errors="ignore") if path.exists() else ""
    migrations = None
    switches = None

    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            value = float(parts[0])
        except:
            continue

        event = parts[2].strip()
        if event == "cpu-migrations":
            migrations = value
        elif event == "context-switches":
            switches = value

    return migrations, switches

rows = []
with DATA.open(newline="") as f:
    for r in csv.DictReader(f):
        h = parse_float(r["hardware_miss_rate_pct"])
        s = parse_float(r["simulation_d1_miss_rate_pct"])
        if h is None or s is None:
            continue

        migrations, switches = perf_quality(r["marker_id"])

        rows.append({
            "pattern": r["pattern"],
            "repeat": int(r["repeat"]),
            "epoch": int(r["epoch"]),
            "marker_id": r["marker_id"],
            "hardware": h,
            "simulation": s,
            "migrations": migrations,
            "context_switches": switches
        })

train = [r for r in rows if r["repeat"] in (1, 2)]
test = [r for r in rows if r["repeat"] == 3]

# Only rows known to have zero migrations are used by the quality-filtered model.
quality_train = [
    r for r in train
    if r["migrations"] is not None and r["migrations"] == 0
]

if not quality_train:
    quality_train = train
    quality_note = "migration_metadata_unavailable; all_training_rows_used"
else:
    quality_note = "zero_migration_training_rows_used"

h_med, h_scale = robust_location_scale([r["hardware"] for r in quality_train])
s_med, s_scale = robust_location_scale([r["simulation"] for r in quality_train])

ordinary_i, ordinary_s = ordinary_affine(quality_train)
robust_i, robust_s = theil_sen(quality_train)

models = {
    "rate_only": None,
    "independent_robust_normalisation": None,
    "ordinary_affine": (ordinary_i, ordinary_s),
    "robust_affine_theil_sen": (robust_i, robust_s),
    "quality_filtered_affine": (ordinary_i, ordinary_s)
}

errors = {name: [] for name in models}
per_workload = []

for r in test:
    h = r["hardware"]
    s = r["simulation"]

    predictions = {
        "rate_only": s,
        # Transform the simulation robust z-score back into hardware units.
        "independent_robust_normalisation":
            h_med + h_scale * ((s - s_med) / s_scale),
        "ordinary_affine": ordinary_i + ordinary_s*s,
        "robust_affine_theil_sen": robust_i + robust_s*s,
        "quality_filtered_affine": ordinary_i + ordinary_s*s
    }

    for name, prediction in predictions.items():
        errors[name].append(h - prediction)

    for name, prediction in predictions.items():
        per_workload.append({
            "pattern": r["pattern"],
            "repeat": r["repeat"],
            "epoch": r["epoch"],
            "method": name,
            "absolute_error": abs(h-prediction),
            "squared_error": (h-prediction)**2
        })

raw_rmse = rmse(errors["rate_only"])

summary = []
for name in models:
    e = errors[name]
    summary.append({
        "method": name,
        "test_rows": len(e),
        "rmse_percentage_points": rmse(e),
        "mae_percentage_points": mae(e),
        "improvement_vs_rate_only_percent":
            100*(raw_rmse-rmse(e))/raw_rmse
    })

with (OUT/"method-comparison.csv").open("w", newline="") as f:
    fields = list(summary[0].keys())
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(summary)

with (OUT/"per-workload-methods.csv").open("w", newline="") as f:
    fields = ["pattern", "method", "test_rows",
              "mae_percentage_points", "rmse_percentage_points"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()

    for pattern in sorted(set(r["pattern"] for r in test)):
        for method in models:
            values = [
                abs(r["hardware"] - (
                    r["simulation"] if method == "rate_only"
                    else h_med + h_scale*((r["simulation"]-s_med)/s_scale)
                    if method == "independent_robust_normalisation"
                    else (ordinary_i + ordinary_s*r["simulation"])
                    if method in ("ordinary_affine", "quality_filtered_affine")
                    else robust_i + robust_s*r["simulation"]
                ))
                for r in test if r["pattern"] == pattern
            ]
            w.writerow({
                "pattern": pattern,
                "method": method,
                "test_rows": len(values),
                "mae_percentage_points": mae(values),
                "rmse_percentage_points": rmse(values)
            })

quality_rows = []
for r in rows:
    quality_rows.append({
        "marker_id": r["marker_id"],
        "pattern": r["pattern"],
        "repeat": r["repeat"],
        "epoch": r["epoch"],
        "cpu_migrations": r["migrations"],
        "context_switches": r["context_switches"],
        "accepted_for_quality_model":
            int(r in quality_train)
    })

with (OUT/"quality-audit.csv").open("w", newline="") as f:
    fields = list(quality_rows[0].keys())
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(quality_rows)

with (OUT/"parameters.txt").open("w") as f:
    f.write(f"all_rows={len(rows)}\n")
    f.write(f"training_rows={len(train)}\n")
    f.write(f"holdout_rows={len(test)}\n")
    f.write(f"quality_training_rows={len(quality_train)}\n")
    f.write(f"quality_note={quality_note}\n")
    f.write(f"ordinary_intercept={ordinary_i}\n")
    f.write(f"ordinary_slope={ordinary_s}\n")
    f.write(f"theil_sen_intercept={robust_i}\n")
    f.write(f"theil_sen_slope={robust_s}\n")
    f.write("holdout_definition=repeat_3_only\n")
    f.write("holdout_not_used_for_fitting=true\n")

print("=== MARKER-ALIGNED FINAL METHODS ===")
print(f"all_rows={len(rows)}")
print(f"training_rows={len(train)}")
print(f"holdout_rows={len(test)}")
print(f"quality_training_rows={len(quality_train)}")
print(f"quality_note={quality_note}")
print(f"ordinary_intercept={ordinary_i:.6f}")
print(f"ordinary_slope={ordinary_s:.6f}")
print(f"theil_sen_intercept={robust_i:.6f}")
print(f"theil_sen_slope={robust_s:.6f}")

for r in summary:
    print(
        f"{r['method']} "
        f"rmse={r['rmse_percentage_points']:.4f} "
        f"mae={r['mae_percentage_points']:.4f} "
        f"improvement={r['improvement_vs_rate_only_percent']:.2f}%"
    )

print(f"SAVED={OUT/'method-comparison.csv'}")
print(f"SAVED={OUT/'per-workload-methods.csv'}")
print(f"SAVED={OUT/'quality-audit.csv'}")
print(f"SAVED={OUT/'parameters.txt'}")
