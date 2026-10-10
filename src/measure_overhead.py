#!/usr/bin/env python3
"""Measure bounded benign workload overhead; no target process control."""
from __future__ import annotations
import argparse, csv, pathlib, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / 'workloads' / 'pattern_workload.py'

def timed(cmd):
    t = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return time.perf_counter()-t, p.returncode
    except FileNotFoundError:
        return None, 127

def main():
    p = argparse.ArgumentParser(); p.add_argument('--repeats', type=int, default=3); p.add_argument('--seconds', type=float, default=3); p.add_argument('--out', default='results/overhead.csv'); a=p.parse_args()
    rows=[]
    for mode, prefix in [('direct', []), ('cachegrind', ['valgrind','--tool=cachegrind','--cache-sim=yes','--cachegrind-out-file=/tmp/overhead-cachegrind.out'])]:
        for i in range(a.repeats):
            cmd = prefix + [sys.executable, str(WORKLOAD), '--pattern','sequential','--seconds',str(a.seconds),'--size-kb','1024','--seed',str(i+1)]
        elapsed, code = timed(cmd); rows.append({'mode':mode,'repeat':i+1,'elapsed_seconds':elapsed,'returncode':code})
    out=pathlib.Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(f'saved={out}')

if __name__ == '__main__': main()
