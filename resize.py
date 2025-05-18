#!/usr/bin/env python

import argparse
from pathlib import Path
from PIL import Image
import glob
import os
from tqdm import tqdm


def resize_image_keep_aspect(image_path: Path, target_height: int) -> Image.Image:
    with Image.open(image_path) as img:
        original_width, original_height = img.size
        scale_factor = target_height / original_height
        new_width = int(original_width * scale_factor)
        return img.resize((new_width, target_height), Image.LANCZOS)


def process_files(
    files, target_height, prefix, suffix, output_dir, resize_smaller, dry_run, overwrite
):
    supported_extensions = {".png", ".jpg", ".jpeg"}

    all_files = []
    for pattern in files:
        expanded_files = glob.glob(os.path.expanduser(pattern), recursive=True)
        all_files.extend(Path(f).resolve() for f in expanded_files if Path(f).is_file())

    print(f"Processing {len(all_files)} image(s)...\n")

    for path in tqdm(all_files, desc="Resizing", unit="file"):
        if path.suffix.lower() not in supported_extensions:
            tqdm.write(f"[SKIP] Unsupported extension: {path}")
            continue

        try:
            with Image.open(path) as img:
                original_height = img.height
        except Exception as e:
            tqdm.write(f"[SKIP] Failed to open: {path} ({e})")
            continue

        if original_height <= target_height:
            tqdm.write(
                f"[WARN] Image smaller than target height: {path.name} ({original_height}px < {target_height}px)"
            )
            if resize_smaller == "skip":
                tqdm.write("[SKIP] Skipping due to --resize-smaller=skip")
                continue
            elif resize_smaller == "false":
                tqdm.write(
                    "[NOTE] Copying without resizing due to --resize-smaller=false"
                )

        if not output_dir:
            tqdm.write("[ERROR] Output directory must be specified.")
            continue

        out_dir = Path(output_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        new_name = prefix + path.stem + suffix + path.suffix
        new_path = out_dir / new_name

        if new_path.exists() and not overwrite:
            tqdm.write(f"[SKIP] Output exists: {new_path.name}")
            continue

        tqdm.write(f"➡️  Resizing: {path.name} -> {new_path.name}")

        if dry_run:
            continue

        if original_height <= target_height and resize_smaller == "false":
            with Image.open(path) as img:
                img.save(new_path)
        else:
            resized = resize_image_keep_aspect(path, target_height)
            resized.save(new_path)


def main():
    parser = argparse.ArgumentParser(
        description="Resize image(s) to a target height, keeping aspect ratio."
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="One or more image files to process (supports globbing, e.g. '*.png')",
    )
    parser.add_argument(
        "-y",
        "--height",
        type=int,
        required=True,
        help="Target height for resized images",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Prefix to add to resized image filenames (default: '')",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="Suffix to append to resized image filenames (default: '')",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        required=True,
        help="Output directory (required)",
    )
    parser.add_argument(
        "-m",
        "--resize-smaller",
        choices=["true", "false", "skip"],
        default="false",
        help="Handle images smaller than target height: true = upscale, false = keep original, skip = skip (default: false)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting output files",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Only print actions without saving any files",
    )

    args = parser.parse_args()

    process_files(
        files=args.files,
        target_height=args.height,
        prefix=args.prefix,
        suffix=args.suffix,
        output_dir=args.output_dir,
        resize_smaller=args.resize_smaller,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
