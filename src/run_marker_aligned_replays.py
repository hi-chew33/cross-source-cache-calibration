#!/usr/bin/env python3
import argparse, csv, json, pathlib, re, subprocess, sys, time

PATS = ["sequential", "strided", "random", "hash", "transition"]

def perf_rate(path):
    refs = misses = None
    for line in pathlib.Path(path).read_text(errors="ignore").splitlines():
        x = line.split(",")
        if len(x) >= 3:
            try:
                v = float(x[0])
            except ValueError:
                continue
            if x[2] == "cache-references":
                refs = v
            elif x[2] == "cache-misses":
                misses = v
    return 100 * misses / refs if refs else None

def cachegrind_rate(path):
    text = subprocess.run(
        ["cg_annotate", str(path)],
        capture_output=True, text=True, check=False
    ).stdout

    for line in text.splitlines():
        if "PROGRAM TOTALS" not in line:
            continue
        prefix = line.split("PROGRAM TOTALS")[0]
        vals = [
            int(x.replace(",", ""))
            for x in re.findall(r"([0-9][0-9,]*)\s+\(", prefix)
        ]
        if len(vals) >= 9:
            dr, d1mr, dw, d1mw = vals[3], vals[4], vals[6], vals[7]
            return 100 * (d1mr + d1mw) / (dr + dw)
    return None

p = argparse.ArgumentParser()
p.add_argument("--out", default="results/journal-study/marker-aligned")
p.add_argument("--cpu", type=int, default=2)
p.add_argument("--epochs", type=int, default=5)
p.add_argument("--seconds", type=int, default=1)
p.add_argument("--size-kb", type=int, default=1024)
p.add_argument("--seed", type=int, default=400)
p.add_argument("--repeats", type=int, default=3)
a = p.parse_args()

root = pathlib.Path(a.out)
native = root / "native-perf"
sim = root / "cachegrind"
native.mkdir(parents=True, exist_ok=True)
sim.mkdir(parents=True, exist_ok=True)

rows = []

for pattern in PATS:
    for repeat in range(1, a.repeats + 1):
        seed = a.seed + repeat - 1

        for epoch in range(1, a.epochs + 1):
            tag = f"{pattern}-run{repeat}-epoch{epoch}"
            perf_file = native / f"{tag}.csv"
            cg_file = sim / f"{tag}.out"

            base = [
                sys.executable,
                "workloads/pattern_workload.py",
                "--pattern", pattern,
                "--seconds", str(a.seconds),
                "--size-kb", str(a.size_kb),
                "--seed", str(seed)
            ]

            manifest = {
                "pattern": pattern,
                "repeat": repeat,
                "epoch": epoch,
                "marker_id": f"{pattern}-run{repeat}-epoch{epoch}",
                "seed": seed,
                "seconds": a.seconds,
                "size_kb": a.size_kb,
                "cpu": a.cpu
            }

            (root / f"{tag}.manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n"
            )

            subprocess.run(
                [
                    "sudo", "taskset", "-c", str(a.cpu),
                    "perf", "stat", "-x,", "-o", str(perf_file),
                    "-e", "cycles,instructions,cache-references,cache-misses,context-switches,cpu-migrations"
                ] + base,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )

            subprocess.run(
                [
                    "valgrind", "--tool=cachegrind", "--cache-sim=yes",
                    f"--cachegrind-out-file={cg_file}"
                ] + base,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )

            rows.append({
                **manifest,
                "hardware_miss_rate_pct": perf_rate(perf_file),
                "simulation_d1_miss_rate_pct": cachegrind_rate(cg_file)
            })

with (root / "marker-aligned-summary.csv").open("w", newline="") as f:
    fields = [
        "pattern", "repeat", "epoch", "marker_id", "seed",
        "seconds", "size_kb", "cpu",
        "hardware_miss_rate_pct",
        "simulation_d1_miss_rate_pct"
    ]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"MARKER_ALIGNED_ROWS={len(rows)}")
print(f"SAVED={root/'marker-aligned-summary.csv'}")
