"""Fixture suite for the four provenance rules.

Self-contained: builds its own source image and regenerates every fixture into
a temporary directory, so it runs on a fresh clone with no `samples/` present.
"""

import numpy as np
import pytest
from PIL import Image

from make_fixtures import main as build_fixtures
from provenance import provenance_check

# name -> expected status, and which rule it is meant to exercise
EXPECTED = {
    "clean.jpg":            ("no_marking_found", "negative: no metadata at all"),
    "exif_software.jpg":    ("marked",           "rule 1: EXIF Software"),
    "exif_desc.jpg":        ("marked",           "rule 1: EXIF ImageDescription"),
    "xmp.jpg":              ("marked",           "rule 2: XMP packet"),
    "png_text.png":         ("marked",           "rule 3: PNG text, generator signature"),
    "benign_png_text.png":  ("no_marking_found", "rule 3 negative: scanner name is not a disclosure"),
    "c2pa_like.jpg":        ("marked",           "rule 4: c2pa/jumb byte marker"),
    "stripped.jpg":         ("no_marking_found", "negative: re-encoded, metadata destroyed"),
}


@pytest.fixture(scope="module")
def prov_dir(tmp_path_factory):
    """Generate all eight fixtures once, into a temp dir."""
    out = tmp_path_factory.mktemp("prov")
    src = out / "_source.png"

    # Deterministic low-frequency texture. Real content is not needed -- these
    # fixtures test metadata handling, not pixels -- but flat colour compresses
    # to almost nothing and makes the JPEG paths degenerate.
    rng = np.random.default_rng(0)
    coarse = rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
    arr = np.array(Image.fromarray(coarse).resize((512, 512), Image.BICUBIC))
    Image.fromarray(arr).save(src)

    build_fixtures(str(src), str(out))
    return out


def test_all_fixtures_were_generated(prov_dir):
    """Guard against a silent pass when generation failed and produced nothing."""
    missing = set(EXPECTED) - {p.name for p in prov_dir.iterdir()}
    assert not missing, f"fixtures never generated: {sorted(missing)}"


@pytest.mark.parametrize(
    "name,expected,rule",
    [(n, s, r) for n, (s, r) in sorted(EXPECTED.items())],
    ids=sorted(EXPECTED),
)
def test_provenance_status(prov_dir, name, expected, rule):
    result = provenance_check(prov_dir / name)
    assert result["status"] == expected, (
        f"{name} ({rule}): expected {expected}, got {result['status']} "
        f"-- evidence: {result['evidence']!r}"
    )


def test_marked_results_carry_evidence(prov_dir):
    """A 'marked' verdict with no evidence string is unreviewable."""
    for name, (status, _) in EXPECTED.items():
        if status != "marked":
            continue
        result = provenance_check(prov_dir / name)
        assert result["evidence"], f"{name} was marked but returned no evidence"


def test_no_marking_found_carries_no_evidence(prov_dir):
    result = provenance_check(prov_dir / "clean.jpg")
    assert result["evidence"] is None
