# Data Dictionary

This document describes the schema and directory organization of experimental data collected in this research project.

## Directory Structure

```
data/
├── raw/
│   ├── seed11-corrected.csv
│   └── seed17-corrected.csv
└── processed/
    ├── marker-aligned/
    │   ├── marker-aligned-summary.csv
    │   ├── native-perf/
    │   └── *.manifest.json
    ├── holdout-seed300/
    │   ├── holdout-paired-summary.csv
    │   ├── per-workload-results.csv
    │   ├── physical/
    │   └── final-holdout-result.txt
    ├── quality-filtered/
    │   ├── quality-paired-summary.csv
    │   ├── physical/
    │   ├── physical-v2/
    │   └── ablation-result.txt
    └── evidence-summaries/
        ├── current-evidence.txt
        └── final-evidence-summary.txt
```

## Schema Definitions

### 1. `marker-aligned-summary.csv`
Contains the 75 configuration-matched replay intervals across the five workload patterns:
- `pattern`: Workload access pattern (`sequential`, `strided`, `random`, `hash`, `transition`).
- `repeat`: Replay repetition index (1, 2, or 3). Repeat 1 and 2 comprise the training set (50 observations); Repeat 3 comprises the untouched holdout set (25 observations).
- `epoch`: Interval epoch index (1 through 5).
- `marker_id`: Unique identifier formatted as `<pattern>-run<repeat>-epoch<epoch>`.
- `hardware_miss_rate_pct`: Hardware L1/generic cache miss rate measured via Linux `perf stat` (`100 * cache-misses / cache-references`).
- `simulation_d1_miss_rate_pct`: D1 cache miss rate computed via Valgrind Cachegrind (`100 * (d1mr + d1mw) / (dr + dw)`).

### 2. `native-perf/<marker_id>.csv`
Raw CSV event output from `perf stat -x,` capturing:
- `cycles`
- `instructions`
- `cache-references`
- `cache-misses`
- `context-switches`
- `cpu-migrations`

### 3. `<marker_id>.manifest.json`
Metadata manifest recording the execution configuration for each replay pair:
- `pattern`: Access pattern name.
- `repeat`: Repeat sequence number.
- `epoch`: Epoch sequence number.
- `marker_id`: Matching identifier.
- `seed`: PRNG seed value.
- `seconds`: Execution time window.
- `size_kb`: Allocated working buffer size in KiB.
- `cpu`: Physical CPU core affinity binding.
