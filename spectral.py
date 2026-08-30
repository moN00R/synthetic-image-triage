import torch
import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
from functools import lru_cache

FIT_LO,  FIT_HI  = 10, 200
HF_LO,   HF_HI   = 180, 250
PEAK_LO, PEAK_HI = 110, 145
HF_CUT = 180   # was 128


@lru_cache(maxsize=4)
def radial_counts(size=512, nbins=256):
    """Pixels per radius bin. Depends only on image size, so cache it."""
    rmap = radius_map(torch.zeros(size, size))
    return torch.bincount(rmap.flatten())[:nbins].float()

# task 1
def center_crop(image, croped_width, croped_height):
    h, w = image.shape[:2]
    if h < croped_height or w < croped_width:
        raise ValueError(f"cannot crop {croped_width}x{croped_height} from {w}x{h}")

    start_x = w//2 - (croped_width//2)
    start_y = h//2 - (croped_height//2)

    return image[start_y:start_y+croped_height, start_x:start_x+croped_width]

def load_gray(path: str, size: int = 512) -> tuple[torch.Tensor, bool]:
    img = cv.imread(path, cv.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"could not decode image: {path}")
 
    h, w = img.shape
    was_resized = False
    if h < size or w < size:
        scale = size / min(h, w)
        img = cv.resize(img, (round(w * scale), round(h * scale)), interpolation=cv.INTER_CUBIC)
        was_resized = True
        print(f"warning: {path} is {w}x{h}, smaller than {size}; resampled before crop")
 
    img = center_crop(img, size, size)
    return torch.from_numpy(img).float() / 255.0, was_resized

# task 2

def hann_window(image):
    h, w = image.shape
    hann1d_h = torch.hann_window(h)
    hann1d_w = torch.hann_window(w)

    hann2d = torch.outer(hann1d_h, hann1d_w)

    hann_image = hann2d * image

    return hann_image

def fft2d(image):
    fft = torch.fft.fft2(image)

    fft_shifted = torch.fft.fftshift(fft)

    magnitude = torch.abs(fft_shifted)

    return magnitude

def cross_contrast(s):
    c = s.shape[0] // 2
    bg_row = (s[c-6, :].mean() + s[c+6, :].mean()) / 2
    bg_col = (s[:, c-6].mean() + s[:, c+6].mean()) / 2
    return (s[c, :].mean() - bg_row).item(), (s[:, c].mean() - bg_col).item()

def seam_control(n=512, seed=0):
    """1/f field cropped from a larger one: guaranteed seam, no scene structure."""
    rng = np.random.default_rng(seed)
    N = 2 * n
    f = np.fft.fftfreq(N); fx, fy = np.meshgrid(f, f)
    r = np.sqrt(fx**2 + fy**2); r[0, 0] = 1
    fld = np.real(np.fft.ifft2((1 / r**1.5) * np.exp(1j * rng.uniform(0, 2*np.pi, (N, N)))))
    fld = (fld - fld.min()) / (fld.max() - fld.min())
    return torch.from_numpy(fld[n//2:n//2+n, n//2:n//2+n]).float()

def to_uint8(*spectra: torch.Tensor, lo_pct: float = 2.0, hi_pct: float = 99.5):
    flat = torch.stack(spectra).flatten()
    lo = torch.quantile(flat, lo_pct / 100)
    hi = torch.quantile(flat, hi_pct / 100)
    return [
        ((s - lo) / (hi - lo) * 255).clamp(0, 255).to(torch.uint8).numpy()
        for s in spectra
    ]


# task 3
def radius_map(power):
    assert power.ndim == 2, f"expected a 2D spectrum, got shape {tuple(power.shape)}"
    h, w = power.shape

    yy, xx = torch.meshgrid(torch.arange(h), torch.arange(w), indexing='ij')

    center_y = h//2
    center_x = w//2

    dx = (xx - center_x) ** 2
    dy = (yy - center_y) ** 2

    radius = torch.sqrt(dx.float() + dy.float())
    radius = radius.round().long()
    return radius

def radial_profile(rmap, power):
    radius_flat = torch.flatten(rmap)
    power_flat = torch.flatten(power)

    power_sum = torch.bincount(radius_flat, weights=power_flat)

    count = torch.bincount(radius_flat)

    prof = power_sum / count
    profile = prof[:256]

    return profile

# task 4 
def _fit_power_law(profile, lo=FIT_LO, hi=FIT_HI):
    """Least-squares line through the log-log radial profile.
    Returns (slope, intercept), both in log space."""
    r = torch.arange(len(profile))
    lr = torch.log(r[lo:hi].float())
    lp = torch.log(profile[lo:hi])
    slope = (((lr - lr.mean()) * (lp - lp.mean())).sum()
             / ((lr - lr.mean()) ** 2).sum())
    intercept = lp.mean() - slope * lr.mean()
    return slope, intercept


def _residual(profile, lo, hi):
    """How far the profile sits above/below its OWN fitted power law,
    in log units, over bins [lo:hi]. Scale-free: the image's overall
    texture level cancels out."""
    slope, intercept = _fit_power_law(profile)
    r = torch.arange(len(profile))
    fitted = slope * torch.log(r[lo:hi].float()) + intercept
    return torch.log(profile[lo:hi]) - fitted


def slope_of(profile, lo=FIT_LO, hi=FIT_HI):
    return _fit_power_law(profile, lo, hi)[0].item()


def hf_residual(profile, lo=HF_LO, hi=HF_HI):
    return _residual(profile, lo, hi).mean().item()


def nyquist_peak(profile, lo=PEAK_LO, hi=PEAK_HI):
    return _residual(profile, lo, hi).max().item()


if __name__ == "__main__":
    img = seam_control(n=512, seed=0)
    # print(img.shape)

    # # # WITHOUT Hann window
    # spectrum_magnitude = fft2d(img)
    # spectrum_without = torch.log(spectrum_magnitude + 1e-8)
    # print('Cross contrast without Hann window:', cross_contrast(spectrum_without))

    # # # WITH Hann window
    # windowed_img = hann_window(img)
    # spectrum_magnitude = fft2d(windowed_img)
    # spectrum_with = torch.log(spectrum_magnitude + 1e-8)

    # print('Cross contrast with Hann window:', cross_contrast(spectrum_with))

    # img = load_gray(
    #     "samples/kodim01.png"
    # )

    windowed_img = hann_window(img)

    fft = fft2d(windowed_img)
    power = fft ** 2

    rmap = radius_map(
        power
    )

    profile = radial_profile(
        rmap,
        power
    )

    r = torch.arange(
        len(profile)
    )

    plt.loglog(
        r[1:].numpy(),
        profile[1:].numpy()
    )

    plt.xlabel("Spatial Frequency")
    plt.ylabel("Average Power")
    plt.title("Azimuthal Average Power Spectrum")

    plt.grid(True)

    plt.savefig(
        "radial_profile.png",
        dpi=150,
        bbox_inches="tight"
    )

    # plt.show()

    r = torch.arange(len(profile))
    lr, lp = torch.log(r[10:200].float()), torch.log(profile[10:200])

    slope = slope_of(profile)
    hf = hf_residual(profile, )
    peak = nyquist_peak(profile)

    print("slope:", slope)
    print("hf_residual:", hf)
    print("nyquist_peak:", peak)