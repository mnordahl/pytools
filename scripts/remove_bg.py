#!/usr/bin/env python

import argparse
import os
import glob
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from tqdm import tqdm

# Define shorthand model names
MODEL_MAP = {
    "u2": "u2net",
    "u2p": "u2netp",
    "human": "u2net_human_seg",
    "silu": "silueta",
    "isnet": "isnet-general-use",
}


def process_image(
    input_path, output_path, model_name, alpha_matting, overwrite=False, dry_run=False
):
    if output_path.exists() and not overwrite:
        return "skipped"

    if dry_run:
        return "dry-run"

    with open(input_path, "rb") as f:
        input_data = f.read()

    session = new_session(model_name=model_name)
    output_data = remove(input_data, session=session, alpha_matting=alpha_matting)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as out:
        out.write(output_data)

    return "done"


def main():
    parser = argparse.ArgumentParser(
        description="Batch remove backgrounds from images using rembg with optional model selection and alpha matting."
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="+",
        help="Input file(s) or glob patterns (e.g. 'images/*.png')",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save output images (default: output)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in the output directory",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="List actions without modifying files",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="u2",
        help="Model to use: u2, u2p, human, silu, isnet, or 'all' to run all models (default: u2)",
    )
    parser.add_argument(
        "--alpha-matting",
        action="store_true",
        help="Enable alpha matting for better hair/edge quality",
    )
    args = parser.parse_args()

    all_input_files = []
    for pattern in args.input:
        expanded = glob.glob(os.path.expanduser(pattern))
        all_input_files.extend(Path(f) for f in expanded if Path(f).is_file())

    if not all_input_files:
        print("No matching files found.")
        return

    output_base = Path(args.output_dir).expanduser()

    if args.model == "all":
        models_to_use = list(MODEL_MAP.values())
    else:
        model_key = args.model.lower()
        if model_key not in MODEL_MAP:
            print(f"Unknown model: {args.model}")
            return
        models_to_use = [MODEL_MAP[model_key]]

    print(
        f"Processing {len(all_input_files)} file(s) with model(s): {', '.join(models_to_use)}\n"
    )

    stats = {model: {"done": 0, "skipped": 0, "dry-run": 0} for model in models_to_use}

    for input_file in tqdm(all_input_files, desc="Removing backgrounds", unit="file"):
        for model in models_to_use:
            suffix = f"_{model.replace('-', '')}" if len(models_to_use) > 1 else ""
            output_file = output_base / (input_file.stem + suffix + input_file.suffix)
            result = process_image(
                input_file,
                output_file,
                model_name=model,
                alpha_matting=args.alpha_matting,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            )
            stats[model][result] += 1

    print("\nSummary:")
    for model, model_stats in stats.items():
        print(f"Model: {model}")
        for key, count in model_stats.items():
            print(f"  {key}: {count}")


if __name__ == "__main__":
    main()
