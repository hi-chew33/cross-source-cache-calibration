#!/usr/bin/env python3
"""Run bounded benign patterns sequentially and write one isolated manifest per run."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, platform, subprocess, sys, time, uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / 'workloads' / 'pattern_workload.py'

def sha256(path):
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', default=str(ROOT / 'pattern-runs'))
    p.add_argument('--seconds', type=float, default=5)
    p.add_argument('--size-kb', type=int, default=1024)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--patterns', nargs='+', default=['sequential','strided','random','hash','transition'])
    a = p.parse_args()
    root = pathlib.Path(a.out).resolve(); root.mkdir(parents=True, exist_ok=True)
    for pattern in a.patterns:
        run = root / f'{time.strftime("%Y%m%dT%H%M%S")}-{pattern}-{uuid.uuid4().hex}'
        run.mkdir()
        cmd = [sys.executable, str(WORKLOAD), '--pattern', pattern,
               '--seconds', str(a.seconds), '--size-kb', str(a.size_kb), '--seed', str(a.seed)]
        started = time.time()
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=a.seconds + 10)
        meta = {'run_id': run.name, 'pattern': pattern, 'command': cmd,
                'started_epoch': started, 'duration_seconds': time.time() - started,
                'returncode': completed.returncode, 'stdout': completed.stdout,
                'stderr': completed.stderr, 'workload_sha256': sha256(WORKLOAD),
                'python': sys.version, 'platform': platform.platform(),
                'safety_mode': 'benign_private_memory_only'}
        (run / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(f'completed={len(a.patterns)} output={root}')

if __name__ == '__main__':
    main()
