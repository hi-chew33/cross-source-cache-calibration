#!/usr/bin/env python3
"""Concurrent-safe, observation-only collector for controlled benign workloads."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, pathlib, signal, subprocess, sys, time, uuid
from datetime import datetime, timezone
import psutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / "workloads" / "benign_workload.py"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--mode", choices=["steady", "phase-change"], default="steady")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--interval", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "runs"))
    ap.add_argument("--cachegrind", action="store_true",
                    help="run the controlled workload under isolated Cachegrind")
    args = ap.parse_args()
    if args.seconds <= 0 or args.interval <= 0:
        raise SystemExit("seconds and interval must be positive")
    run_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex}"
    run_dir = pathlib.Path(args.out).resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "run_id": run_id, "label": args.label, "mode": args.mode,
        "seconds_requested": args.seconds, "interval": args.interval,
        "seed": args.seed, "started_utc": utc_now(),
        "collector_pid": os.getpid(), "workload_sha256": sha256_file(WORKLOAD),
        "counter_source": "cachegrind_and_process_telemetry" if args.cachegrind else "process_and_system_telemetry_only",
        "safety_mode": "observation_only", "run_directory": str(run_dir),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    samples = run_dir / "telemetry.csv"
    workload_cmd = [sys.executable, str(WORKLOAD), "--mode", args.mode,
                    "--seconds", str(args.seconds), "--seed", str(args.seed)]
    cache_file = run_dir / "cachegrind.out"
    if args.cachegrind:
        cmd = ["valgrind", "--tool=cachegrind", "--cache-sim=yes",
               f"--cachegrind-out-file={cache_file}"] + workload_cmd
    else:
        cmd = workload_cmd
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    ps = psutil.Process(proc.pid)
    ps.cpu_percent(None)
    fields = ["t_monotonic", "elapsed", "pid", "cpu_percent", "rss_bytes",
              "read_bytes", "write_bytes", "num_threads", "ctx_switches",
              "system_cpu_percent", "system_load_1m", "available_memory"]
    start = time.monotonic()
    with samples.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        while proc.poll() is None:
            now = time.monotonic()
            try:
                io = ps.io_counters()
                ctx = ps.num_ctx_switches()
                mem = ps.memory_info()
                row = {
                    "t_monotonic": now, "elapsed": now - start, "pid": proc.pid,
                    "cpu_percent": ps.cpu_percent(None), "rss_bytes": mem.rss,
                    "read_bytes": io.read_bytes, "write_bytes": io.write_bytes,
                    "num_threads": ps.num_threads(),
                    "ctx_switches": ctx.voluntary + ctx.involuntary,
                    "system_cpu_percent": psutil.cpu_percent(None),
                    "system_load_1m": os.getloadavg()[0],
                    "available_memory": psutil.virtual_memory().available,
                }
                writer.writerow(row); f.flush()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(args.interval)
    try:
        stdout, stderr = proc.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=2)
    (run_dir / "stdout.txt").write_text(stdout or "")
    (run_dir / "stderr.txt").write_text(stderr or "")
    if args.cachegrind and cache_file.exists():
        annotation = subprocess.run(["cg_annotate", str(cache_file)],
                                    capture_output=True, text=True, check=False)
        (run_dir / "cachegrind.annotate.txt").write_text(annotation.stdout)
    metadata.update({"finished_utc": utc_now(), "returncode": proc.returncode,
                     "sample_file": str(samples)})
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    main()
