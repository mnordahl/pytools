#!/usr/bin/env python

import argparse
import glob
from glob import has_magic
import re
from pathlib import Path
import platform
import uuid


def simple_replace(name: str, old: str, new: str) -> str:
    return name.replace(old, new)


def regex_replace(name: str, pattern: str, replacement: str) -> str:
    return re.sub(pattern, replacement, name)


def split_words(text: str, case: str) -> list[str]:
    if case == "snake":
        return text.split("_")
    elif case == "kebab":
        return text.split("-")
    elif case in {"lower", "upper"}:
        return [text]
    elif case == "title":
        return text.split(" ")
    elif case in {"camel", "pascal"}:
        return re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", text)
    else:
        return re.split(r"[\s_\-]+", text)


def transform_case(text: str, from_case: str, to_case: str) -> str:
    words = split_words(text, from_case)

    if to_case == "lower":
        return "".join(w.lower() for w in words)
    elif to_case == "upper":
        return "".join(w.upper() for w in words)
    elif to_case == "title":
        return " ".join(w.capitalize() for w in words)
    elif to_case == "snake":
        return "_".join(w.lower() for w in words)
    elif to_case == "kebab":
        return "-".join(w.lower() for w in words)
    elif to_case == "camel":
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])
    elif to_case == "pascal":
        return "".join(w.capitalize() for w in words)
    else:
        return text


def guess_case(text: str) -> str:
    if "_" in text:
        return "snake"
    elif "-" in text:
        return "kebab"
    elif re.match(r"^[a-z]+(?:[A-Z][a-z0-9]*)+$", text):
        return "camel"
    elif re.match(r"^(?:[A-Z][a-z0-9]*)+$", text):
        return "pascal"
    elif text.isupper():
        return "upper"
    elif text.islower():
        return "lower"
    elif " " in text:
        return "title"
    else:
        return "fallback"


def add_counter(
    files: list[Path],
    regex: bool,
    match_expr: str,
    full: bool,
    ignore_case: bool,
    delimiter: str,
    pad: int,
    case_style: str | None = None,
) -> list[tuple[Path, Path]]:
    renamed = []
    counters = {}

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
            if case_style:
                new_stem = transform_case(new_stem, guess_case(new_stem), case_style)
            new_file = file.with_name(f"{new_stem}{file.suffix}")
            renamed.append((file, new_file))
    else:
        if ignore_case:
            match_expr = match_expr.lower()

        if match_expr == "@sprites":
            match_list = (
                "admiration|confusion|embarrassment|love|relief|"
                "amusement|curiosity|excitement|nervousness|remorse|"
                "anger|desire|fear|neutral|sadness|annoyance|"
                "disappointment|gratitude|optimism|surprise|approval|"
                "disapproval|grief|pride|caring|disgust|joy|realization"
            ).split("|")
        elif "|" in match_expr:
            match_list = match_expr.split("|")
        else:
            match_list = [match_expr]

        for file in sorted(files):
            stem = file.stem
            for word in match_list:
                stem_cmp = stem.lower() if ignore_case else stem
                if word in stem_cmp:
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
            if case_style:
                new_stem = transform_case(new_stem, guess_case(new_stem), case_style)
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
        help="Use regex for replacements.",
    )
    parser.add_argument(
        "-c",
        "--counter",
        metavar="MATCH",
        help="Add counter with optional match keywords.",
    )
    parser.add_argument("-f", "--full", action="store_true", help="Replace full stem.")
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Show changes only."
    )
    parser.add_argument(
        "-l", "--literal", action="store_true", default=False, help="Disable globbing."
    )
    parser.add_argument(
        "--ignore-case", action="store_true", help="Ignore case in matching."
    )
    parser.add_argument("--delimiter", default="-", help="Delimiter for counters.")
    parser.add_argument(
        "--pad", type=int, default=0, help="Pad counter with leading zeros."
    )

    parser.add_argument(
        "--from-case",
        choices=["lower", "upper", "title", "snake", "kebab", "camel", "pascal"],
        help="Original case style of filenames.",
    )
    parser.add_argument(
        "--to-case",
        choices=["lower", "upper", "title", "snake", "kebab", "camel", "pascal"],
        help="Target case style.",
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
            args.to_case,
        )
    else:
        for file in files:
            stem = file.stem

            if args.replace:
                stem = (
                    regex_replace(stem, *args.replace)
                    if args.regex
                    else simple_replace(stem, *args.replace)
                )

            if args.to_case:
                from_case = args.from_case or guess_case(stem)
                stem = transform_case(stem, from_case, args.to_case)

            new_file = file.with_name(f"{stem}{file.suffix}")
            rename_pairs.append((file, new_file))

    for src, dst in rename_pairs:
        if src.resolve() == dst.resolve():
            if src.name == dst.name:
                print(f"Skipping unchanged: {src} -> {dst}")
                continue
            print(f"Renaming (case change): {src} -> {dst}")
        elif dst.exists():
            print(f"Error: {dst} already exists. Skipping {src}")
            continue
        else:
            print(f"{src} -> {dst}")

        if not args.dry_run:
            src.rename(dst)


if __name__ == "__main__":
    main()
