"""Contract tests for GIDE 30-well pilot (synthetic smoke data ONLY)."""
from collections import Counter

import numpy as np

from scripts.run_gide_30well_dose_pilot import analyze, manifest


def fake_data(with_signal=True):
    rng = np.random.default_rng(42)
    rows = []
    for item in manifest():
        dose, well, t = item["dose_nm"], item["well"], item["timepoint"]
        increase = 12 * np.log1p(dose) if with_signal else 0
        early = 100 + (ord(well[0]) - 67) * 0.2
        level = early if t == 1 else early + increase if t == 13 else 100 + increase
        rows.append(dict(
            well=well, dose_nm=dose, timepoint=t,
            corrected_mean=float(level * 0.1 + rng.normal(0, 0.1)),
            corrected_p99=float(level + rng.normal(0, 0.05)),
        ))
    return rows


def test_manifest_has_30_wells_10_doses_and_90_unique_images():
    entries = manifest()
    assert len(entries) == len({e["filename"] for e in entries}) == 90
    assert len({e["well"] for e in entries}) == 30
    assert Counter(e["timepoint"] for e in entries) == {1: 30, 13: 30, 14: 30}
    assert set(Counter(e["dose_nm"] for e in entries).values()) == {9}
    assert all(e["url"].startswith("https://ftp.ebi.ac.uk/") for e in entries)


def test_synthetic_signal_recovered_without_leakage():
    report, wells = analyze(fake_data(), n_perm=499)
    assert len(wells) == 30
    assert report["primary_predeclared_terminal_annexinv_p99_vs_dose"]["rho"] > 0.5
    assert report["primary_predeclared_terminal_annexinv_p99_vs_dose"][
        "permutation_p_two_sided"] < 0.05
    assert report["secondary_predeclared_hoechst_delta_p99_vs_dose"][
        "holm_p_two_tests"] < 0.05
    assert len(report["heldout_well_cv"]["baseline_t1_only"]["predictions"]) == 30
    assert report["heldout_well_cv"]["dose_is_not_a_predictor"]


def test_noise_only_does_not_break_analysis():
    report, wells = analyze(fake_data(False), n_perm=29)
    assert len(wells) == 30
    assert report["n_images"] == 90
    assert report["n_doses"] == 10
