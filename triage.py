import argparse
import csv
from pathlib import Path
 
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
 
from spectral import (
    load_gray, hann_window, fft2d, radius_map, radial_profile,
    hf_residual, slope_of, nyquist_peak,
)
from provenance import provenance_check

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}



def triage(path):
    prov = provenance_check(path)

    gray_img, was_resized = load_gray(str(path))
    img_window = hann_window(gray_img)
    magnitude = fft2d(img_window)
    power = magnitude ** 2

    rmap = radius_map(power)
    profile = radial_profile(rmap, power)

    return {
        "path": str(path),
        "provenance": prov["status"],
        "evidence": prov["evidence"],
        "was_resized": was_resized,
        "slope": slope_of(profile),
        "hf_residual": hf_residual(profile),
        "nyquist_peak": nyquist_peak(profile),
        "gray_img": gray_img,
        "log_spectrum": torch.log(magnitude + 1e-8),
        "profile": profile,
    }


def save_csv(rows, output_path):
    fieldnames = ["path", "provenance", "evidence", "was_resized", "slope", "hf_residual", "nyquist_peak"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "path": row["path"],
                "provenance": row["provenance"],
                "evidence": row["evidence"],
                "was_resized": row["was_resized"],
                "slope": f"{row['slope']:.10f}",
                "hf_residual": f"{row['hf_residual']:.10f}",
                "nyquist_peak": f"{row['nyquist_peak']:.10f}",
            })
 
 
def save_panel(result, output_path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
 
    axes[0].imshow(result["gray_img"].numpy(), cmap="gray")
    axes[0].set_title("Original")
    axes[0].axis("off")
 
    axes[1].imshow(result["log_spectrum"].numpy(), cmap="gray")
    axes[1].set_title("Log spectrum")
    axes[1].axis("off")
 
    profile = result["profile"]
    r = torch.arange(len(profile))
    axes[2].plot(r[1:].numpy(), profile[1:].numpy())
    axes[2].set_xscale("log")
    axes[2].set_yscale("log")
    axes[2].set_title("Radial profile")
    axes[2].set_xlabel("Radius")
    axes[2].set_ylabel("Power")
 
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
 
 
def collect_images(inputs, recursive=False):
    """Resolve CLI arguments -- each a file or a directory -- into image paths."""
    paths = []
    for raw in inputs:
        p = Path(raw)
        if p.is_file():
            if p.suffix.lower() not in IMAGE_EXTS:
                raise SystemExit(f"not a supported image type: {p}")
            paths.append(p)
        elif p.is_dir():
            entries = p.rglob("*") if recursive else p.glob("*")
            found = sorted(
                q for q in entries
                if q.is_file() and q.suffix.lower() in IMAGE_EXTS
            )
            if not found:
                hint = "" if recursive else " (try --recursive)"
                raise SystemExit(f"no images found in {p}{hint}")
            paths.extend(found)
        else:
            raise SystemExit(f"no such file or directory: {p}")

    # A file can arrive twice -- named directly and again via its directory.
    seen, unique = set(), []
    for p in paths:
        key = p.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def print_report(result):
    """Readable block for a single image, where a one-line table row is too thin."""
    print(f"\n{result['path']}")
    print(f"  provenance    {result['provenance']}")
    if result["evidence"]:
        print(f"  evidence      {result['evidence']}")
    if result["was_resized"]:
        print("  note          upsampled before crop; spectral features are unreliable")
    print(f"  slope         {result['slope']:+.4f}")
    print(f"  hf_residual   {result['hf_residual']:+.4f}")
    print(f"  nyquist_peak  {result['nyquist_peak']:+.4f}")
    print("\n  Feature values are not a verdict. See README, 'What this is not'.")


def main():
    parser = argparse.ArgumentParser(
        description="Frequency-domain triage for images with missing or stripped "
                    "AI-provenance marking.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        metavar="PATH",
        help="image file(s) and/or directory(ies) of images",
    )
    parser.add_argument("--out", help="write results to this CSV")
    parser.add_argument(
        "--panels",
        help="write the three-panel figure here: a directory, or a single "
             "image filename when exactly one input image is given",
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="descend into subdirectories",
    )
    args = parser.parse_args()

    image_paths = collect_images(args.inputs, args.recursive)
    single = len(image_paths) == 1

    panel_dir = panel_file = None
    if args.panels:
        target = Path(args.panels)
        if single and target.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".svg"}:
            panel_file = target
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            panel_dir = target
            panel_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in image_paths:
        try:
            result = triage(path)
        except Exception as exc:
            print(f"skip {path.name}: {type(exc).__name__}: {exc}")
            continue
        rows.append(result)

        if panel_file:
            save_panel(result, panel_file)
        elif panel_dir:
            save_panel(result, panel_dir / f"{path.stem}.png")

        if not single:
            print(f"{path.name:22s} {result['provenance']:17s} slope={result['slope']:+.3f}")

    if not rows:
        raise SystemExit("no images could be read")

    if single:
        print_report(rows[0])
    if panel_file:
        print(f"\n  panel         {panel_file}")
    elif panel_dir:
        print(f"\nwrote {len(rows)} panel(s) to {panel_dir}")

    if args.out:
        save_csv(rows, args.out)
        print(f"wrote {len(rows)} row(s) to {args.out}")
    elif not single:
        print("(no --out given, so no CSV was written)")


if __name__ == "__main__":
    main()