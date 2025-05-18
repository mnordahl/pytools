#!/usr/bin/env python

import argparse
import glob
import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm


def crop_image(input_path, output_path, overwrite=False, dry_run=False):
    img = Image.open(input_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    bbox = img.getbbox()
    if not bbox:
        print(f"\rSkipping empty image: {input_path}")
        return "skipped"

    cropped = img.crop(bbox)

    if dry_run:
        print(f"\r[Dry-run] Would save cropped image: {output_path}")
        return "dry-run"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        print(f"\rSkipping (already exists): {output_path}")
        return "skipped"

    cropped.save(output_path)
    return "done"


def main():
    parser = argparse.ArgumentParser(
        description="Crop images to remove all excess transparent pixels."
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="+",
        help="Input file(s) or glob patterns (e.g. 'path/**/*.png')",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="cropped",
        help="Directory to save cropped images (default: 'cropped')",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Enable recursive directory matching with '**'",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing output files"
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="List actions without saving files"
    )
    args = parser.parse_args()

    # Expand input files
    input_files = []
    for pattern in args.input:
        expanded = glob.glob(os.path.expanduser(pattern), recursive=args.recursive)
        input_files.extend(Path(f) for f in expanded if Path(f).is_file())

    if not input_files:
        print("No matching files found.")
        return

    output_base = Path(args.output_dir).expanduser()
    stats = {"done": 0, "skipped": 0, "dry-run": 0}

    print(f"Cropping {len(input_files)} image(s)...\n")

    for input_file in tqdm(input_files, desc="Cropping", unit="file"):
        tqdm.write(f"Processing: {input_file}")

        # Compute relative path from the common root directory of the match
        try:
            rel_path = input_file.relative_to(
                input_file.parents[
                    len(input_file.parts) - len(Path(args.input[0]).parts)
                ]
            )
        except ValueError:
            rel_path = Path(input_file.name)

        output_file = output_base / rel_path
        result = crop_image(
            input_file, output_file, overwrite=args.overwrite, dry_run=args.dry_run
        )
        stats[result] += 1

    # Summary
    print("\nSummary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
