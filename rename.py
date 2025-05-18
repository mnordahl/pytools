#!/usr/bin/env python

import argparse
import glob
from glob import has_magic
import re
from pathlib import Path


def simple_replace(name: str, old: str, new: str) -> str:
    return name.replace(old, new)


def regex_replace(name: str, pattern: str, replacement: str) -> str:
    return re.sub(pattern, replacement, name)


def add_counter(
    files: list[Path],
    regex: bool,
    match_expr: str,
    full: bool,
    ignore_case: bool,
    delimiter: str,
    pad: int,
) -> list[tuple[Path, Path]]:
    renamed = []
    counters = {}

    # if regex, assume that the match_expr is a regex pattern
    if regex:
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(match_expr, flags)

        for file in sorted(files):
            stem = file.stem

            match = pattern.search(stem)
            key = match.group(0) if match else None

            if not key:
                renamed.append((file, file))
                continue

            counters.setdefault(key, 0)
            counters[key] += 1

            number = str(counters[key]).zfill(pad) if pad > 0 else str(counters[key])
            new_stem = (
                f"{key}{delimiter}{number}"
                if full
                else stem.replace(key, f"{key}{delimiter}{number}")
            )
            new_file = file.with_name(f"{new_stem}{file.suffix}")
            renamed.append((file, new_file))

    # if not regex, handle some simple patterns
    else:
        if ignore_case:
            # if ignore_case is set, convert match_expr to lowercase
            match_expr = match_expr.lower()

        if match_expr == "@sprites":
            # if match_expr is "@sprites", use a predefined list of sprite names
            match_list = (
                "admiration|confusion|embarrassment|love|relief|"
                "amusement|curiosity|excitement|nervousness|remorse|"
                "anger|desire|fear|neutral|sadness|annoyance|"
                "disappointment|gratitude|optimism|surprise|approval|"
                "disapproval|grief|pride|caring|disgust|joy|realization"
            ).split("|")
        elif "|" in match_expr:
            # if the match_expr is a list of words separated by "|"
            match_list = match_expr.split("|")
        else:
            # if the match_expr is a single word
            match_list = [match_expr]

        for file in sorted(files):
            stem = file.stem

            # if any of the words in match_set are in the filename
            for word in match_list:
                if ignore_case:
                    # if ignore_case is set, convert stem to lowercase
                    stem = stem.lower()
                if word in stem:
                    key = word
                    break
            else:
                key = None

            if not key:
                renamed.append((file, file))
                continue

            counters.setdefault(key, 0)
            counters[key] += 1

            number = str(counters[key]).zfill(pad) if pad > 0 else str(counters[key])
            new_stem = (
                f"{key}{delimiter}{number}"
                if full
                else stem.replace(key, f"{key}{delimiter}{number}")
            )
            new_file = file.with_name(f"{new_stem}{file.suffix}")
            renamed.append((file, new_file))

    return renamed


def parse_args():
    parser = argparse.ArgumentParser(description="Batch rename files.")
    parser.add_argument("files", nargs="+", help="Files to rename (e.g. path/*.png)")

    parser.add_argument(
        "-r",
        "--replace",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="Simple string replace.",
    )

    parser.add_argument(
        "--regex",
        action="store_true",
        default=False,
        help="Use regex for replacements instead of exact string matching.",
    )
    parser.add_argument(
        "-c",
        "--counter",
        metavar="MATCH",
        help=(
            "Add counter for files matching string. Provide multiple "
            "strings by separating with '|'. Specify exactly '@sprites' "
            "to automatically use a predefined list of sprite names."
        ),
    )
    parser.add_argument(
        "-f",
        "--full",
        action="store_true",
        help="Replace the full filename (excluding extension).",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without renaming.",
    )
    parser.add_argument(
        "-l",
        "--literal",
        action="store_true",
        help="Use literal path names (no globbing). Prevents *, ? and [] from being expanded.",
        default=False,
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Ignore case when matching words for counters.",
    )
    parser.add_argument(
        "--delimiter",
        default="-",
        help="Delimiter between match word and counter (default: '-')",
    )
    parser.add_argument(
        "--pad",
        type=int,
        default=0,
        help="Pad counter with leading zeros to this width.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    files = []
    for pattern in args.files:
        if has_magic(pattern) and not args.literal:
            files.extend(glob.glob(pattern))
        else:
            files.append(pattern)
    files = [Path(f) for f in files if Path(f).is_file()]

    if not files:
        print("No matching files.")
        return

    rename_pairs = []

    if args.counter:
        rename_pairs = add_counter(
            files,
            args.regex,
            args.counter,
            args.full,
            args.ignore_case,
            args.delimiter,
            args.pad,
        )
    else:
        for file in files:
            stem = file.stem
            if args.full:
                stem = (
                    args.counter or args.replace[1]
                    if args.replace
                    else args.regex[1] if args.regex else stem
                )

            if args.replace:
                stem = simple_replace(stem, *args.replace)
            if args.regex:
                stem = regex_replace(stem, *args.regex)

            new_file = file.with_name(f"{stem}{file.suffix}")
            rename_pairs.append((file, new_file))

    for src, dst in rename_pairs:
        if src == dst:
            continue
        if dst.exists():
            print(f"Error: {dst} already exists. Skipping {src}")
            continue
        print(f"{src} -> {dst}")
        if not args.dry_run:
            src.rename(dst)


if __name__ == "__main__":
    main()
