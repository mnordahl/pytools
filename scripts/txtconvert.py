#!/usr/bin/env python

import argparse
import os
import json
import csv
import glob
from pathlib import Path
from typing import Literal


def read_csv(file_path, delimiter):
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def write_csv(data, file_path, delimiter):
    with open(file_path, mode="w", encoding="utf-8", newline="\n") as f:
        if not data:
            return
        writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)


def read_json(file_path):
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def write_json(data, file_path, pretty):
    with open(file_path, mode="w", encoding="utf-8", newline="\n") as f:
        json.dump(
            data,
            f,
            indent=2 if pretty else None,
            separators=(",", ":") if not pretty else None,
            ensure_ascii=False,
        )


def infer_format(path: Path) -> Literal["json", "csv", None]:
    ext = path.suffix.lower()
    if ext == ".json":
        return "json"
    elif ext == ".csv":
        return "csv"
    else:
        return None


def main():
    parser = argparse.ArgumentParser(description="Convert between JSON and CSV formats")
    parser.add_argument(
        "files", nargs="+", help="Input file(s), supports globbing like *.csv"
    )
    parser.add_argument(
        "-f", "--format", required=True, choices=["json", "csv"], help="Output format"
    )
    parser.add_argument(
        "-o", "--output-dir", help="Optional directory for output files"
    )
    parser.add_argument(
        "--input-format",
        choices=["json", "csv"],
        help="Force input format if no extension",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ',')")
    parser.add_argument(
        "--overwrite", action="store_true", help="Allow overwriting files"
    )

    args = parser.parse_args()

    # Expand input paths
    files = []
    for pattern in args.files:
        files.extend(glob.glob(os.path.expanduser(pattern)))

    if not files:
        print("No files matched.")
        return

    for file_path in files:
        path = Path(file_path)
        input_format = args.input_format or infer_format(path)

        if not input_format:
            print(f"Skipping {path.name}: unknown input format.")
            continue

        try:
            if input_format == "csv":
                data = read_csv(path, args.delimiter)
            else:
                data = read_json(path)

            output_dir = Path(args.output_dir) if args.output_dir else path.parent
            os.makedirs(output_dir, exist_ok=True)
            output_filename = path.stem + "." + args.format
            output_path = output_dir / output_filename

            if output_path.exists() and not args.overwrite:
                print(f"Skipping {output_path.name}: already exists.")
                continue

            if args.format == "json":
                write_json(data, output_path, args.pretty)
            else:
                write_csv(data, output_path, args.delimiter)

            print(f"✓ Converted: {path.name} → {output_path}")

        except Exception as e:
            print(f"✗ Failed to convert {path.name}: {e}")


if __name__ == "__main__":
    main()
