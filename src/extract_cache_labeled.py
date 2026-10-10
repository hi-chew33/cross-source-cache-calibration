#!/usr/bin/env python3

import csv
import json
import pathlib
import re

FIELDS = [
    "Ir", "I1mr", "ILmr",
    "Dr", "D1mr", "DLmr",
    "Dw", "D1mw", "DLmw"
]

def parse_annotation(path):
    text = path.read_text(errors="replace")

    totals_line = None

    for line in text.splitlines():
        if "PROGRAM TOTALS" in line:
            totals_line = line
            break

    if totals_line is None:
        raise ValueError("PROGRAM TOTALS not found in annotation file")

    # Extract integer counters from the already-generated annotation line.
    numbers = re.findall(r"\d[\d,]*", totals_line)
    numbers = [int(x.replace(",", "")) for x in numbers]

    if len(numbers) < 9:
        raise ValueError(
            f"Only {len(numbers)} numeric values found in PROGRAM TOTALS"
        )

    values = dict(zip(FIELDS, numbers[-9:]))

    def ratio(numerator, denominator):
        denominator_value = values.get(denominator, 0)
        if denominator_value == 0:
            return 0.0
        return values.get(numerator, 0) / denominator_value

    values["I_miss_rate"] = ratio("I1mr", "Ir")
    values["IL_miss_rate"] = ratio("ILmr", "Ir")
    values["D_read_miss_rate"] = ratio("D1mr", "Dr")
    values["DL_read_miss_rate"] = ratio("DLmr", "Dr")
    values["D_write_miss_rate"] = ratio("D1mw", "Dw")
    values["DL_write_miss_rate"] = ratio("DLmw", "Dw")

    return values

def main():
    files = sorted(
        pathlib.Path("runs").glob("**/cachegrind.annotate.txt")
    )

    if not files:
        raise SystemExit("No Cachegrind annotation files found")

    rows = []

    for annotation in files:
        run_dir = annotation.parent
        metadata_path = run_dir / "metadata.json"

        try:
            metadata = json.loads(metadata_path.read_text())
            values = parse_annotation(annotation)

            row = {
                "run_id": metadata.get("run_id", run_dir.name),
                "label": metadata.get("label", ""),
                "mode": metadata.get("mode", ""),
                "counter_source": metadata.get("counter_source", ""),
                "annotation_file": str(annotation),
            }

            row.update(values)
            rows.append(row)

        except Exception as error:
            print(f"SKIP {annotation}: {error}")

    if not rows:
        raise SystemExit("No labeled cache records were extracted")

    output = pathlib.Path("results/cache_features_labeled.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted records: {len(rows)}")
    print(f"Saved file: {output}")

if __name__ == "__main__":
    main()
