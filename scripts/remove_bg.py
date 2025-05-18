#!/usr/bin/env python

# Updated remove_bg.py with --save-mask and --mask options

import argparse
import os
import glob
import io
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from tqdm import tqdm

MODEL_MAP = {
    "u2": "u2net",
    "u2p": "u2netp",
    "human": "u2net_human_seg",
    "silu": "silueta",
    "isnet": "isnet-general-use",
}


def save_mask(image_data, output_path):
    with Image.open(io.BytesIO(image_data)) as img:
        alpha = img.getchannel("A")
        alpha.save(output_path)


def process_image(
    input_path,
    output_path,
    model_name,
    alpha_matting,
    save_mask_flag,
    overwrite=False,
    dry_run=False,
):
    if output_path.exists() and not overwrite:
        return "skipped"

    if dry_run:
        return "dry-run"

    with open(input_path, "rb") as f:
        input_data = f.read()

    session = new_session(model_name=model_name)
    output_data = remove(
        input_data,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=250,
        alpha_matting_background_threshold=200,
        alpha_matting_erode_size=2,
        alpha_matting_base_size=1200,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as out:
        out.write(output_data)

    if save_mask_flag:
        mask_subdir = output_path.parent / "masks"
        mask_subdir.mkdir(parents=True, exist_ok=True)
        mask_path = mask_subdir / (output_path.stem + "_mask.png")
        save_mask(output_data, mask_path)

    return "done"


def main():
    parser = argparse.ArgumentParser(
        description="Remove backgrounds with rembg, with support for mask export."
    )
    parser.add_argument(
        "input", type=str, nargs="+", help="Input image file(s) or glob patterns"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save output images",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing output files"
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="Print actions only"
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="u2",
        help="Model: u2, u2p, human, silu, isnet, or 'all'",
    )
    parser.add_argument(
        "--alpha-matting", action="store_true", help="Enable alpha matting"
    )
    parser.add_argument(
        "--save-mask", action="store_true", help="Save alpha mask as separate image"
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
                save_mask_flag=args.save_mask,
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
