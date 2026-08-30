
import os
import sys

import cv2 as cv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

from spectral import load_gray, hann_window, fft2d, radius_map, radial_profile, hf_residual, slope_of

FIT_LO, FIT_HI = 10, 200   
HF_CUT = 128               


def variants(gray_u8):
    def jpeg(q):
        ok, buf = cv.imencode(".jpg", gray_u8, [int(cv.IMWRITE_JPEG_QUALITY), q])
        assert ok, "jpeg encode failed"
        return cv.imdecode(buf, cv.IMREAD_GRAYSCALE)

    def roundtrip(interp):
        small = cv.resize(gray_u8, (256, 256), interpolation=interp)
        return cv.resize(small, (512, 512), interpolation=interp)

    return {
        "original":    gray_u8,
        "JPEG q95":    jpeg(95),
        "JPEG q75":    jpeg(75),
        "JPEG q40":    jpeg(40),
        "bilinear x2": roundtrip(cv.INTER_LINEAR),
        "nearest x2":  roundtrip(cv.INTER_NEAREST),
    }


def profile_of(gray_u8):
    img = torch.from_numpy(gray_u8).float() / 255.0
    power = fft2d(hann_window(img)) ** 2
    return radial_profile(radius_map(power), power)


def main(path):
    img_t, was_resized = load_gray(path)
    if was_resized:
        print("note: this image was resampled to reach 512px, so every curve "
              "below already carries that signature")
    gray_u8 = (img_t * 255).round().byte().numpy()

    profiles = {name: profile_of(v) for name, v in variants(gray_u8).items()}
    base_s = slope_of(profiles["original"])
    base_h = hf_residual(profiles["original"])

    print(f"\n{'variant':<13}{'slope':>9}{'d slope':>9}{'hf_residual':>11}{'d hf':>9}")
    print("-" * 51)
    for name, p in profiles.items():
        s, h = slope_of(p), hf_residual(p)
        print(f"{name:<13}{s:9.3f}{s - base_s:9.3f}{h:11.5f}"
              f"{(h / base_h - 1) * 100:8.1f}%")

    os.makedirs("docs", exist_ok=True)
    plt.figure(figsize=(7.5, 5))
    r = torch.arange(len(profiles["original"]))
    for name, p in profiles.items():
        extra = dict(color="black", lw=2.2, zorder=5) if name == "original" else dict(lw=1.2)
        plt.loglog(r[1:].numpy(), p[1:].numpy(), label=name, **extra)
    plt.axvspan(FIT_LO, FIT_HI, color="grey", alpha=.08, zorder=0)
    plt.xlabel("Spatial frequency (radius, bins)")
    plt.ylabel("Average power")
    plt.title(f"Ordinary handling moves the spectrum — {os.path.basename(path)}")
    plt.legend(fontsize=8)
    plt.grid(True, which="both", alpha=.3)
    plt.savefig("docs/confounds.png", dpi=150, bbox_inches="tight")
    print("\nwrote docs/confounds.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "samples/photo.png")