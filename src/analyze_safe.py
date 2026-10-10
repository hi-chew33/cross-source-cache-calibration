#!/usr/bin/env python3
"""Build robust temporal features, fit a baseline, and score runs.

This script is offline and observation-only. It never controls or terminates a process.
"""
from __future__ import annotations
import argparse, csv, json, pathlib, statistics
import numpy as np

FEATURES = ["cpu_percent", "rss_bytes", "read_bytes", "write_bytes",
            "num_threads", "ctx_switches", "system_cpu_percent",
            "system_load_1m", "available_memory"]


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return [{k: float(r[k]) for k in FEATURES} for r in rows]


def delta(values):
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / max(1.0, len(values) - 1)


def vector(rows):
    if not rows:
        raise ValueError("empty telemetry")
    # Rates and robust summaries are less sensitive to total runtime than raw totals.
    out = []
    for key in FEATURES:
        x = [r[key] for r in rows]
        out.extend([statistics.median(x), statistics.pstdev(x), delta(x)])
    return np.asarray(out, dtype=float)


def load_runs(root):
    data = []
    for meta_path in sorted(pathlib.Path(root).glob("*/metadata.json")):
        meta = json.loads(meta_path.read_text())
        csv_path = meta_path.parent / "telemetry.csv"
        if csv_path.exists():
            data.append((meta, vector(read_csv(csv_path))))
    return data


def robust_baseline(vectors):
    x = np.vstack(vectors)
    med = np.median(x, axis=0)
    mad = np.median(np.abs(x - med), axis=0)
    scale = np.maximum(1.4826 * mad, 1e-9)
    return med, scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--label", default="baseline")
    ap.add_argument("--baseline")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    pathlib.Path(args.out).mkdir(parents=True, exist_ok=True)
    runs = load_runs(args.runs)
    if not runs:
        raise SystemExit("no completed runs found")
    if args.baseline:
        b = json.loads(pathlib.Path(args.baseline).read_text())
        med, scale = np.asarray(b["median"]), np.asarray(b["scale"])
    else:
        selected = [v for m, v in runs if m.get("label") == args.label and m.get("mode") == "steady"]
        if len(selected) < 3:
            raise SystemExit("need at least 3 steady baseline runs with matching --label")
        med, scale = robust_baseline(selected)
        b = {"feature_order": FEATURES, "median": med.tolist(), "scale": scale.tolist(),
             "baseline_label": args.label, "baseline_policy": "operator-selected steady runs"}
        pathlib.Path(args.out, "baseline.json").write_text(json.dumps(b, indent=2) + "\n")
    results = []
    for meta, v in runs:
        z = np.abs((v - med) / scale)
        # Persistence proxy: a robust vector score over the complete observation window.
        score = float(np.median(z))
        results.append({"run_id": meta["run_id"], "label": meta["label"],
                        "mode": meta["mode"], "score": score,
                        "alert": bool(score >= 6.0)})
    pathlib.Path(args.out, "scores.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"baseline": str(pathlib.Path(args.out, "baseline.json")),
                      "scores": str(pathlib.Path(args.out, "scores.json")),
                      "runs_scored": len(results)}, indent=2))

if __name__ == "__main__":
    main()
