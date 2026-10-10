#!/usr/bin/env python3
"""Safety-gated response helper. Default and only supported action is log-only."""
import argparse, json, os, pathlib, time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pid', type=int, required=True)
    p.add_argument('--action', choices=['log-only'], default='log-only')
    p.add_argument('--out', default='results/response-events.jsonl')
    a = p.parse_args()
    if a.pid <= 1 or a.pid == os.getpid() or a.pid == os.getppid():
        raise SystemExit('refusing PID 1, self, or parent process')
    event = {
        'timestamp': time.time(), 'pid': a.pid, 'action': a.action,
        'effect': 'no process control performed',
        'safety_mode': 'observation_only'
    }
    path = pathlib.Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(event) + '\n')
    print(json.dumps(event, indent=2))

if __name__ == '__main__':
    main()
