"""Deterministic synthetic contract checks (NOT real biological validation)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from scripts.run_gide_terminal_cells import (
    manifest, segment_nuclei, measure_annexin_near_nuclei, summarize,
)


def test_manifest_pairs_all_thirty_wells():
    items = manifest()
    assert len(items) == len({i["filename"] for i in items}) == 60
    assert len({i["well"] for i in items}) == 30
    for i in range(0, len(items), 2):
        assert items[i]["well"] == items[i+1]["well"]
        assert items[i]["channel"] == "Hoechst_terminal"
        assert items[i+1]["channel"] == "AnnexinV_terminal"


def test_known_synthetic_nuclei_and_local_annexin():
    yy, xx = np.mgrid[:320, :320]
    centers = [(35+i*48, 35+j*48) for i in range(6) for j in range(6)]
    rng = np.random.default_rng(123)
    h = 90 + rng.normal(0, 5, (320, 320)).astype("float32")
    a = np.ones_like(h)*30
    for cy, cx in centers:
        d2 = (yy-cy)**2 + (xx-cx)**2
        h[d2 < 64] += 200
        a[(d2 >= 64) & (d2 < 289)] += 300
    masks, qc = segment_nuclei(gaussian_filter(h, .8), min_area=25, max_area=500)
    assert 24 <= qc["n_nuclei"] <= 50
    cells = measure_annexin_near_nuclei(masks, a, ring_radius=9)
    assert len(cells) >= 20
    assert np.median([c["ann_ring_p90"] for c in cells]) > 100


def test_constant_image_refused():
    with pytest.raises(ValueError):
        segment_nuclei(np.ones((100, 100)))


def test_permutation_uses_thirty_wells_not_individual_cells():
    wells = []
    for col, dose in ((2, 0), (3, .61), (4, 1.22), (5, 2.44), (6, 4.88),
                      (7, 9.77), (8, 19.53), (9, 39.06), (10, 78.13), (11, 156.25)):
        for row in "CDE":
            wells.append(dict(well=f"{row}-{col:02d}", dose_nm=dose,
                              median_ann_ring_p90=float(col*10),
                              n_valid_nuclei=100, qc_pass=True))
    result = summarize(wells, permutations=199)
    assert result["n_wells_total"] == 30
    assert result["primary_dose_vs_median_ann_ring_p90"]["rho"] > .9
    assert result["primary_dose_vs_median_ann_ring_p90"]["permutation_p"] <= .05
