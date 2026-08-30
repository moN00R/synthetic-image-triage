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
 
 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", help="directory containing images")
    parser.add_argument("--out", required=True, help="output CSV path")
    parser.add_argument("--panels", help="optional directory for panel PNGs")
    args = parser.parse_args()
 
    dir_path = Path(args.input_dir)
    image_paths = sorted(
        p for p in dir_path.glob("*.*") if p.suffix.lower() in IMAGE_EXTS
    )
    if not image_paths:
        raise SystemExit(f"no images found in {dir_path}")
 
    panel_dir = Path(args.panels) if args.panels else None
    if panel_dir:
        panel_dir.mkdir(parents=True, exist_ok=True)
 
    rows = []
    for path in image_paths:
        try:
            result = triage(path)
        except Exception as exc:
            print(f"skip {path.name}: {type(exc).__name__}: {exc}")
            continue
        rows.append(result)
        if panel_dir:
            save_panel(result, panel_dir / f"{path.stem}.png")
        print(f"{path.name:22s} {result['provenance']:17s} slope={result['slope']:+.3f}")
 
    save_csv(rows, args.out)
    print(f"\nwrote {len(rows)} rows to {args.out}")
 
 
if __name__ == "__main__":
    main()