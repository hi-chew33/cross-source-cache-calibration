#!/usr/bin/env python3

import csv
import pathlib
import re
import subprocess
import sys

FIELDS = [
    "Ir", "I1mr", "ILmr",
    "Dr", "D1mr", "DLmr",
    "Dw", "D1mw", "DLmw"
]

def extract_one(annotation_file):
    text = pathlib.Path(annotation_file).read_text(errors="replace")

    header = None
    for line in text.splitlines():
        if "Ir" in line and "I1mr" in line and "Dr" in line:
            header = line
            break

    totals = None
    for line in text.splitlines():
        if "PROGRAM TOTALS" in line:
            totals = line
            break

    if totals is None:
        raise ValueError("PROGRAM TOTALS not found")

    # Cachegrind's summary uses integer counts in this order.
    numbers = re.findall(r"\d[\d,]*", totals)
    numbers = [int(x.replace(",", "")) for x in numbers]

    if len(numbers) < 9:
        raise ValueError(f"Expected at least 9 cache values, found {len(numbers)}")

    values = dict(zip(FIELDS, numbers[-9:]))

    def rate(a, b):
        denominator = values.get(b, 0)
        return values.get(a, 0) / denominator if denominator else 0.0

    values["I_miss_rate"] = rate("I1mr", "Ir")
    values["IL_miss_rate"] = rate("ILmr", "Ir")
    values["D_read_miss_rate"] = rate("D1mr", "Dr")
    values["DL_read_miss_rate"] = rate("DLmr", "Dr")
    values["D_write_miss_rate"] = rate("D1mw", "Dw")
    values["DL_write_miss_rate"] = rate("DLmw", "Dw")

    values["annotation_file"] = str(annotation_file)
    return values

def main():
    files = sorted(pathlib.Path("runs").glob("**/cachegrind.annotate.txt"))

    if not files:
        print("No Cachegrind annotation files found.")
        sys.exit(1)

    rows = []
    for path in files:
        try:
            rows.append(extract_one(path))
        except Exception as exc:
            print(f"SKIP {path}: {exc}")

    if not rows:
        print("No cache records could be extracted.")
        sys.exit(1)

    output = pathlib.Path("results/cache_features.csv")
    output.parent.mkdir(exist_ok=True)

    fields = list(rows[0].keys())
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(rows)} Cachegrind records")
    print(f"Saved: {output}")

    for row in rows:
        print(
            row["annotation_file"],
            "D_read_miss_rate=",
            f'{row["D_read_miss_rate"]:.6f}',
            "D_write_miss_rate=",
            f'{row["D_write_miss_rate"]:.6f}'
        )

if __name__ == "__main__":
    main()
