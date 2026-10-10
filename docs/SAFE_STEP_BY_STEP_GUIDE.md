# Safe Step-by-Step Guide

This guide details the replication workflow for the study: **Cross-Source Calibration of Hardware Cache Measurements and Software Cache Simulation**.

## 1. Environment & Prerequisites

The study was developed and evaluated on:
- OS: Ubuntu Linux (6.8+ / 7.0+ kernel)
- Processor: AMD Ryzen 7 7445HS (6 physical cores, 12 logical CPUs, 16 MiB L3 cache)
- Profiling tools: Linux `perf` (`linux-tools-common`), Valgrind (`valgrind`, `cg_annotate`)
- Python: Version 3.11+ / 3.12+

Install the required Python packages:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy pandas scipy matplotlib psutil
```

## 2. Safety and Observation Guarantees

The measurement harnesses and analysis scripts are strictly **observation-only**:
- They read hardware performance counters via `perf stat`.
- They simulate memory hierarchies via Valgrind Cachegrind (`cg_annotate`).
- They do **not** terminate, suspend, throttle, isolate, scan, encrypt, or modify user processes or files.

## 3. Workload Patterns

Five distinct workload access patterns are implemented in `workloads/pattern_workload.py`:
1. `sequential`: Linear streaming array traversal.
2. `strided`: Non-unit stride array traversals across cache lines.
3. `random`: Permutation-indexed pseudorandom access across allocated memory.
4. `hash`: Pointer/key lookup traversal driven by integer hashing.
5. `transition`: Multi-phase execution alternating access modes across epochs.

## 4. Replay Protocol & Zero-CPU-Migration Quality Rule

Because hardware performance counters and software cache simulation cannot execute within the exact same process context without simulation artifacts polluting hardware counters, measurements are collected in **configuration-matched, interval-indexed replay pairs**:

1. **CPU Pinning**: Hardware runs are pinned to a dedicated physical CPU core (e.g., CPU 2 via `taskset -c 2`).
2. **Quality Criterion**: Training observations are strictly audited for zero CPU migrations (`cpu-migrations == 0`). Observations with migrations or unexpected interruptions are isolated.
3. **Matched Parameters**: Execution duration (seconds), memory buffer size (`--size-kb`), and pseudo-random seed values are identical across paired replays.

## 5. Running the Calibration Analysis

To reproduce the primary calibration models and evaluate holdout performance:
```bash
python src/analyze_marker_aligned_methods.py
```

This script evaluates:
- `rate_only`: Raw, uncalibrated software simulation miss rate baseline.
- `independent_robust_normalisation`: Independent robust z-score source normalisation.
- `ordinary_affine`: Ordinary least-squares affine calibration.
- `robust_affine_theil_sen`: Non-parametric Theil-Sen robust slope-intercept calibration.
- `quality_filtered_affine`: Affine calibration trained exclusively on certified zero-migration replays.

The script outputs result tables into `results/tables/`:
- `method-comparison.csv`
- `per-workload-methods.csv`
- `quality-audit.csv`
- `parameters.txt`
