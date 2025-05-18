#!/usr/bin/env python

import argparse
import os
import shutil
from datetime import datetime, date
from pathlib import Path
import re
import glob

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_valid_date_directory(name):
    return DATE_DIR_RE.match(name) is not None


def is_past_date(name):
    try:
        dir_date = datetime.strptime(name, "%Y-%m-%d").date()
        return dir_date < date.today()
    except ValueError:
        return False


def organize_directories(paths, dry_run=False, verbose=False):
    for pattern in paths:
        for path in glob.glob(os.path.expanduser(pattern)):
            p = Path(path)
            if not p.is_dir():
                if verbose:
                    print(f"Skipping (not a dir): {p}")
                continue
            if not is_valid_date_directory(p.name):
                if verbose:
                    print(f"Skipping (not a valid date): {p}")
                continue
            if not is_past_date(p.name):
                if verbose:
                    print(f"Skipping (current or future date): {p}")
                continue

            year, month, _ = p.name.split("-")
            target_dir = p.parent / year / month
            dest = target_dir / p.name

            if dest.exists():
                print(f"Skipping (target exists): {dest}")
                continue

            print(f"{'Would move' if dry_run else 'Moving'} {p} -> {dest}")
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(dest))


def main():
    parser = argparse.ArgumentParser(
        description="Organize Forge image directories by year/month."
    )
    parser.add_argument(
        "paths", nargs="+", help="Paths to directories (supporting glob patterns)"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show what would happen without moving",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print all directory checks"
    )
    parser.add_argument(
        "-y",
        "--confirm",
        action="store_true",
        help="Skip confirmation prompts (not used yet)",
    )

    args = parser.parse_args()
    organize_directories(args.paths, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
