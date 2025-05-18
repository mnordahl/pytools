#!/usr/bin/env python

import argparse
import glob
import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm


def apply_mask(
    image_path: Path, mask_path: Path, output_path: Path, overwrite=False, dry_run=False
):
    if output_path.resolve() == image_path.resolve():
        print(f"[ERROR] Output path is the same as input path: {output_path}")
        return "error"

    if output_path.exists() and not overwrite:
        print(f"[SKIP] Output exists: {output_path}")
        return "skipped"

    if dry_run:
        print(
            f"[DRY-RUN] Would apply mask: {mask_path} to {image_path} → {output_path}"
        )
        return "dry-run"

    with Image.open(image_path).convert("RGBA") as img, Image.open(mask_path).convert(
        "L"
    ) as mask:
        img.putalpha(mask)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        print(f"[OK] Saved masked image to {output_path}")
        return "done"


def main():
    parser = argparse.ArgumentParser(
        description="Apply alpha masks to a batch of images."
    )
    parser.add_argument(
        "images", type=str, nargs="+", help="Input image file(s) (supports globbing)"
    )
    parser.add_argument(
        "-m",
        "--mask-dir",
        type=str,
        required=True,
        help="Directory where corresponding *_mask.png files are stored",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save output images",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Allow overwriting output files"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Preview actions without writing files",
    )
    args = parser.parse_args()

    mask_dir = Path(os.path.expanduser(args.mask_dir)).resolve()
    output_dir = Path(os.path.expanduser(args.output_dir)).resolve()

    all_input_files = []
    for pattern in args.images:
        expanded = glob.glob(os.path.expanduser(pattern))
        all_input_files.extend(Path(f).resolve() for f in expanded if Path(f).is_file())

    if not all_input_files:
        print("No matching input files found.")
        return

    if any(f.parent.resolve() == output_dir for f in all_input_files):
        print("[ERROR] Input and output directories must not be the same.")
        return

    stats = {"done": 0, "skipped": 0, "dry-run": 0, "error": 0}

    for input_file in tqdm(all_input_files, desc="Reapplying masks", unit="file"):
        mask_file = mask_dir / (input_file.stem + "_mask.png")
        output_file = output_dir / input_file.name

        if not mask_file.exists():
            print(f"[SKIP] Mask not found: {mask_file}")
            stats["skipped"] += 1
            continue

        result = apply_mask(
            input_file,
            mask_file,
            output_file,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        if result in stats:
            stats[result] += 1
        else:
            stats["error"] += 1

    print("\nSummary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
