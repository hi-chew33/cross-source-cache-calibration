# Cross-Source Calibration of Hardware Cache Measurements and Software Cache Simulation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

This repository provides the replication code, experimental datasets, configuration manifests, and analysis pipelines for the study **"Cross-Source Calibration of Hardware Cache Measurements and Software Cache Simulation"**.

---

## Study Purpose

Software cache simulators (such as Valgrind Cachegrind) provide deterministic, functional models of cache hierarchies, but they do not account for physical microarchitectural nuances such as hardware prefetchers, out-of-order execution, system noise, and memory bus contention. Conversely, hardware performance counters (accessible via Linux `perf`) reflect true execution on physical silicon, but vary due to kernel background activity and multi-core scheduling.

This research establishes and evaluates statistical calibration models that bridge software cache simulation and physical hardware counter measurements across reproducible, memory-intensive workload patterns.

---

## Experimental Setup and Sources

- **Hardware-Counter Source**: Linux `perf` (`perf stat`) monitoring hardware cache performance events (`cache-references`, `cache-misses`, `cycles`, `instructions`, `context-switches`, `cpu-migrations`) on a dedicated core of an AMD Ryzen 7 7445HS processor (6 physical cores, 12 logical CPUs, 16 MiB L3 cache, Ubuntu Linux).
- **Software-Simulation Source**: Valgrind Cachegrind (`cg_annotate`) simulating a deterministic cache hierarchy and recording Level 1 Data cache events (`dr`, `d1mr`, `dw`, `d1mw`).
- **Core Pinning & Zero-CPU-Migration Quality Rule**: Hardware executions are strictly pinned to a dedicated core (CPU 2) using `taskset`. Only runs with **zero CPU migrations** (`cpu-migrations == 0`) are admitted into the quality-controlled training set.

---

## Workload Patterns

The study evaluates five memory access patterns implemented in [`workloads/pattern_workload.py`](workloads/pattern_workload.py):

1. **`sequential`**: Continuous, unit-stride linear access across an allocated buffer.
2. **`strided`**: Multi-line stride traversal inducing regular, non-consecutive line accesses.
3. **`random`**: Pseudorandom permutation-indexed access across memory lines.
4. **`hash`**: Non-linear table indexing driven by integer hashing.
5. **`transition`**: Multi-phase alternating access pattern exhibiting temporal phase shifts.

---

## Replay Protocol and Dataset Split

To prevent software simulator overhead and instruction instrumentation from interfering with physical hardware counters, measurements were collected in **75 configuration-matched, interval-indexed replay pairs**:
- **75 Pairs**: 5 workload patterns &times; 3 repetition runs &times; 5 interval epochs.
- **50-Training / 25-Holdout Split**:
  - **Training Set (50 pairs)**: Replay repeats 1 and 2 across all patterns and epochs. All 50 training observations satisfied the zero-CPU-migration quality rule.
  - **Holdout Set (25 pairs)**: Replay repeat 3 across all patterns and epochs, kept completely untouched during model parameter fitting.

---

## Evaluated Methods

The study evaluates five prediction methods on the untouched 25-pair holdout set:

1. **`rate_only`**: Direct software simulation miss rate baseline (uncalibrated).
2. **`independent_robust_normalisation`**: Independent source normalisation using median and median absolute deviation (MAD).
3. **`ordinary_affine`**: Ordinary least squares affine calibration ($y = \alpha + \beta x$).
4. **`robust_affine_theil_sen`**: Robust non-parametric Theil-Sen regression resisting potential outliers.
5. **`quality_filtered_affine`**: Affine calibration fitted exclusively on certified zero-migration observations.

### Primary Holdout Results (75-Replay Study)

| Method | Test Rows | RMSE (% pts) | MAE (% pts) | Improvement vs Baseline |
| :--- | :---: | :---: | :---: | :---: |
| `rate_only` (uncalibrated) | 25 | 11.8621 | 10.7796 | Baseline (0.00%) |
| `independent_robust_normalisation` | 25 | 3.3418 | 2.7197 | **71.83%** |
| `ordinary_affine` | 25 | 3.2046 | 2.7209 | **72.98%** |
| `robust_affine_theil_sen` | 25 | 3.8378 | 2.2747 | **67.65%** |
| `quality_filtered_affine` | 25 | 3.2046 | 2.7209 | **72.98%** |

*Model parameters (fitted on 50 training rows):*
- Ordinary Affine: $\text{Intercept} = -1.850580$, $\text{Slope} = 34.676190$
- Theil-Sen Robust Affine: $\text{Intercept} = -7.088850$, $\text{Slope} = 51.784780$

---

## Repository Structure

```
cross-source-cache-calibration/
├── README.md               # Study overview and replication instructions
├── LICENSE                 # MIT License
├── CITATION.cff            # Citation metadata in Citation File Format
├── .gitignore              # Ignored files (bytecode, envs, raw traces, drafts)
├── src/                    # Python experiment and analysis scripts
│   ├── analyze_marker_aligned_methods.py
│   ├── run_marker_aligned_replays.py
│   ├── collect_safe.py
│   └── ...
├── workloads/              # Workload generators
│   ├── pattern_workload.py
│   └── benign_workload.py
├── data/
│   ├── raw/                # Baseline paired comparison data (seeds 11 & 17)
│   └── processed/          # 75 marker-aligned runs, manifests, and holdouts
│       ├── marker-aligned/
│       ├── holdout-seed300/
│       └── quality-filtered/
├── results/
│   ├── figures/            # Figure outputs
│   └── tables/             # Summary comparison tables and audit logs
├── docs/                   # Documentation and replication guides
│   ├── SAFE_STEP_BY_STEP_GUIDE.md
│   └── DATA_DICTIONARY.md
└── metadata/               # Environment, collection notes, and file inventories
    ├── collection-notes.txt
    ├── environment.txt
    └── collected-files.txt
```

---

## Replication Quick Start

### 1. Requirements
- Python 3.11+
- `numpy`, `pandas`, `scipy`, `matplotlib`, `psutil`

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt # or pip install numpy pandas scipy matplotlib psutil
```

### 2. Reproduce Calibration Analysis
To evaluate the calibration models against the processed experimental dataset and reproduce all tables:
```bash
python src/analyze_marker_aligned_methods.py
```
This writes the summary tables to [`results/tables/`](results/tables/):
- `method-comparison.csv`
- `per-workload-methods.csv`
- `quality-audit.csv`
- `parameters.txt`

---

## Scientific Limitations

1. **Separate Replay Executions**: Hardware counter measurements and Cachegrind simulations were collected in configuration-matched, interval-indexed replay pairs rather than measured simultaneously, to prevent simulator binary translation overhead from corrupting physical counters.
2. **Single Hardware Architecture**: The experimental evaluation was conducted on an AMD Ryzen 7 7445HS processor; calibration models are not claimed to be processor-independent.
3. **Metric Semantics**: Generic Linux `perf` cache events (`cache-references`, `cache-misses`) and Cachegrind Level 1 Data cache events (`D1`) measure related but non-identical architectural boundaries.
4. **Residual Attribution**: The calibration residual demonstrates systematic differences between functional simulation and physical execution, but does not directly prove a specific underlying microarchitectural mechanism.

---

## Citation

If you use this dataset or replication code, please cite:
```bibtex
@software{prasanna2026crosssource,
  author = {Prasanna, Hrithik},
  title = {Cross-Source Calibration of Hardware Cache Measurements and Software Cache Simulation},
  year = {2026},
  url = {https://github.com/hi-chew33/cross-source-cache-calibration}
}
```
