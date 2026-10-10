#!/usr/bin/env python3
"""Score a sequence of residual scores with persistence and hysteresis.

No process control is performed. Input is a CSV with timestamp/window and score.
"""
from __future__ import annotations
import argparse, csv, json, pathlib


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--score-column', default='calibrated_residual_score')
    p.add_argument('--alert-threshold', type=float, default=6.0)
    p.add_argument('--recovery-threshold', type=float, default=3.0)
    p.add_argument('--confirm-windows', type=int, default=3)
    p.add_argument('--out', default='results/state-events.jsonl')
    a = p.parse_args()
    if a.recovery_threshold >= a.alert_threshold or a.confirm_windows < 1:
        raise SystemExit('recovery threshold must be below alert threshold')
    rows = list(csv.DictReader(open(a.input, newline='')))
    state, high_count = 'BASELINE', 0
    events = []
    for row in rows:
        score = float(row[a.score_column])
        previous = state
        if state in ('BASELINE', 'RECOVERY'):
            if score >= a.alert_threshold:
                high_count += 1
                state = 'SUSPECTED_CHANGE' if high_count < a.confirm_windows else 'CONFIRMED_CHANGE'
            else:
                high_count = 0
                state = 'STABLE'
        elif state == 'STABLE':
            if score >= a.alert_threshold:
                high_count = 1
                state = 'SUSPECTED_CHANGE'
        elif state == 'SUSPECTED_CHANGE':
            if score >= a.alert_threshold:
                high_count += 1
                if high_count >= a.confirm_windows:
                    state = 'CONFIRMED_CHANGE'
            else:
                high_count = 0
                state = 'STABLE'
        elif state == 'CONFIRMED_CHANGE':
            if score < a.recovery_threshold:
                state = 'RECOVERY'
                high_count = 0
        event = dict(row)
        event.update({'previous_state': previous, 'state': state,
                      'score': score, 'high_count': high_count,
                      'observation_only': True})
        if state != previous:
            events.append(event)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w') as f:
        for event in events:
            f.write(json.dumps(event) + '\n')
    print(json.dumps({'input_rows': len(rows), 'state_changes': len(events), 'output': str(out)}, indent=2))

if __name__ == '__main__':
    main()
