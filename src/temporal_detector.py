import argparse
import csv
import json
import pathlib
import statistics

FEATURES = [
    "cpu_percent",
    "rss_bytes",
    "read_bytes",
    "write_bytes",
    "num_threads",
    "ctx_switches",
    "system_cpu_percent",
    "system_load_1m",
    "available_memory",
]

def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def feature_vector(rows):
    result = {}

    for feature in FEATURES:
        values = [float(row[feature]) for row in rows]
        result[feature + "_median"] = statistics.median(values)
        result[feature + "_mean"] = statistics.mean(values)
        result[feature + "_std"] = (
            statistics.pstdev(values) if len(values) > 1 else 0.0
        )

    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default="runs")
    parser.add_argument("--window", type=int, default=10)
    parser.add_argument("--out", default="results/temporal_scores.jsonl")
    args = parser.parse_args()

    output = pathlib.Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    records = []

    for telemetry_path in sorted(
        pathlib.Path(args.runs).glob("**/telemetry.csv")
    ):
        metadata_path = telemetry_path.parent / "metadata.json"

        if not metadata_path.exists():
            continue

        metadata = json.loads(metadata_path.read_text())
        rows = read_rows(telemetry_path)

        if len(rows) < args.window:
            continue

        for index in range(0, len(rows) - args.window + 1, args.window):
            window_rows = rows[index:index + args.window]
            features = feature_vector(window_rows)

            record = {
                "run_id": metadata.get("run_id", telemetry_path.parent.name),
                "label": metadata.get("label", ""),
                "mode": metadata.get("mode", ""),
                "window_start": index,
                "window_end": index + args.window,
            }

            record.update(features)
            records.append(record)

    with output.open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print("windows=", len(records))
    print("saved=", output)

if __name__ == "__main__":
    main()
