# synthetic-image-triage

Frequency-domain triage for images whose AI-provenance marking is missing or stripped — reports spectral artifact features, not verdicts.

---

## The problem

Article 50 of the EU AI Act applies from 2 August 2026. It requires providers of generative AI systems to mark synthetic outputs in a machine-readable format, and deployers of deepfake systems to disclose that content is artificially generated. Systems already on the market before that date have until 2 December 2026 to comply.

Two gaps follow, and both are live right now:

1. A large volume of synthetic content is circulating legally with no marking at all.
2. Markings that *do* exist are routinely destroyed downstream. Screenshotting, re-encoding and platform recompression all strip C2PA manifests and EXIF fields.

A reviewer handling an unmarked image — a newsroom, an insurer processing claim photos, a trust and safety team — is left with no signal. This tool provides a fallback one.

## What it does

Checks for provenance markers first, because the machine-readable mark is the primary signal under Article 50. Only when none is found does it fall back to an intrinsic measurement: a Hann-windowed 2D FFT (`torch.fft`) collapsed into a 1D radial power spectrum, from which it extracts interpretable features.

```bash
python triage.py path/to/your/images/ --out results.csv --panels docs/panels/ # a folder
python triage.py path/to/one_image.png # a single image
```

Per image you get a CSV row and a three-panel figure (original | log spectrum | radial profile). Pass a single image with no --out to print its features to stdout instead.

## Provenance detection

Four rules, tried in order, first match wins:

| # | rule | source |
|---|---|---|
| 1 | EXIF `Software`, `ImageDescription`, `Artist`, `Copyright` | generator metadata |
| 2 | XMP packet | Adobe-family and C2PA-adjacent tooling |
| 3 | PNG text chunks matched against known generator signatures | Stable Diffusion WebUI, ComfyUI, and similar |
| 4 | raw byte scan for `c2pa` / `jumb` box markers | C2PA manifests Pillow does not surface |

Rule 3 matches against a signature list rather than accepting any text chunk. An earlier version flagged anything non-empty, which reported authentic Kodak scans as `marked` on the strength of a `source: Kodak PCD0992` chunk. A scanner name is not an AI disclosure.

Rule 4 is deliberately last and deliberately weak. It is a substring match against compressed bytes with no structure parsing, so it cannot distinguish a real manifest from a coincidental byte sequence. It speaks only when nothing above it does.

pytest runs eleven checks: the eight provenance fixtures covering all four rules plus three negatives, and three assertions on the shape of the returned result. Fixtures are generated into a temporary directory at test time, so the suite runs on a fresh clone. `make_fixtures.py` generates them from any image you have.

## Features

| feature | what it measures | stability across crops |
|---|---|---|
| `slope` | log-log slope of the radial power spectrum | 0.7% |
| `hf_residual` | high-frequency deviation from the image's own power law | 0.009 log-units |
| `nyquist_peak` | residual bump near half-Nyquist, where up-convolution leaves checkerboard structure | untested against a controlled generated/real pair |
| `provenance` / `evidence` | which rule fired, and on what | — |

## What this is not

**Not a classifier and not a compliance verdict.** No accuracy figure is claimed anywhere in this repo, because no validated dataset ships with it.

`no_marking_found` does not mean an image is human-made. It means these four rules found nothing. Absence of a mark is not evidence of authenticity.

The spectral features are confounded by ordinary image processing. This is measured, not assumed.

## Measured confounds

`docs/confounds.png` compares one source image against JPEG at quality 95/75/40 and against ×2 downsample-upsample with bilinear and nearest-neighbour interpolation.

The dominant effect is bilinear resampling: `slope` moves from −1.76 to −3.98 and `hf_residual` from −0.56 to −1.98, both far larger than any other manipulation tested. **An image that has been through a bilinear resize is spectrally unlike its own original.** A naive real-vs-generated comparison across differently-processed sources therefore measures the processing, not the source.

Two consequences shaped the design:

- **Format must be matched before comparison.** Comparing PNG "real" images against JPEG "generated" images produces a large, meaningless separation driven entirely by the container.
- **A feature is only usable if it survives a crop.** `hf_ratio`, an earlier attempt dividing tail energy by total energy, moved 80% between crops of the same image — against 0.7% for `slope` — and was replaced by `hf_residual`, which measures deviation from the image's own fitted power law and so cancels out how much texture a given crop happens to contain.

## The spectral cross has two sources

An unwindowed FFT shows a bright cross through the centre. Only part of it is an artifact.

The **boundary discontinuity** — the image does not tile, so its left edge clashes with its right — is a measurement artifact. A Hann window removes it: on a synthetic control with no oriented structure, cross contrast drops from ~2.3 to ~0.05 log-units.

**Axis-aligned scene content** — building edges, window frames, horizons — puts genuine energy on the frequency axes. Windowing does not remove this and should not. On an architectural photo a substantial cross survives windowing, and that is correct behaviour.

The window is therefore tested against a synthetic seam control (`seam_control()`) rather than a photograph. Testing it on a real image cannot distinguish "the window failed" from "the building has straight lines in it."

## Preliminary observation, n=1

One C2PA-marked generated image was caught by rule 4 and showed `nyquist_peak` of 0.895, against a range of 0.377–0.491 across seven non-generated images. Its `slope` was −3.29, close to the bilinear confound at −3.98.

This is **not** presented as a detection result. Sample size is one, and no real photograph in the set went through the same resampling pipeline, so the effect cannot be separated from a resize. Distinguishing the two requires a matched generated/real pair at identical format and resolution — the next step for this repo, and the reason no accuracy claim appears above.

## Install

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest                        # expect 11 passed
python triage.py path/to/your/images/ --out results.csv --panels docs/panels/ # a folder
```

## Built for

Analysts triaging media with no usable provenance layer, and as a reproducible frequency-analysis baseline for deepfake-detection research (cf. Durall et al., *Watch Your Up-Convolution*; Frank et al., *Leveraging Frequency Analysis for Deep Fake Image Recognition*).

## License

MIT