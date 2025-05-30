#!/usr/bin/env python

import re
import argparse
from pathlib import Path


def split_chapters(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    base_name = Path(input_file).stem
    output_dir = Path(input_file).parent

    chapter_pattern = re.compile(r"^(Prologue|Chapter \d+|Epilogue)\b", re.IGNORECASE)
    chapter_indices = []
    chapter_titles = []

    for i, line in enumerate(lines):
        if chapter_pattern.match(line.strip()):
            chapter_indices.append(i)
            chapter_titles.append(line.strip())

    # Add final line index to handle last chapter
    chapter_indices.append(len(lines))

    chapter_count = 1
    for idx in range(len(chapter_indices) - 1):
        start = chapter_indices[idx]
        end = chapter_indices[idx + 1]
        title = chapter_titles[idx].lower()

        if "prologue" in title:
            suffix = "ch00_prologue"
        elif "epilogue" in title:
            suffix = f"ch{chapter_count:02d}_epilogue"
        else:
            suffix = f"ch{chapter_count:02d}"
            chapter_count += 1

        output_file = output_dir / f"{base_name}_{suffix}.txt"
        with open(output_file, "w", encoding="utf-8") as f_out:
            f_out.writelines(lines[start:end])

        print(f"Wrote: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split a story text file into chapter files."
    )
    parser.add_argument("input_file", help="Path to the story text file")
    args = parser.parse_args()
    split_chapters(args.input_file)
