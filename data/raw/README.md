# Raw Experimental Data

This directory contains the baseline paired measurement observations collected prior to calibration:

- `seed11-corrected.csv`: Initial 15 paired observations under seed 11 across all five workload patterns.
- `seed17-corrected.csv`: Initial 15 paired observations under seed 17 across all five workload patterns.

## Excluded Files Note
As documented in `metadata/collection-notes.txt`, raw binary profiling traces (`perf.data`) and raw Valgrind Cachegrind dumps (`*.out`) were intentionally excluded from this repository due to storage and portability considerations. The extracted comma-separated metric counters and execution manifests are preserved in `data/processed/`.
