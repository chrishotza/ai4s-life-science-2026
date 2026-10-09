#!/usr/bin/env python3
"""GIDE 30-well exploratory dose-response from official TIFFs, not a phenotype benchmark."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import tifffile
from scipy.stats import rankdata
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from scripts.run_gide_tiff_pilot import BASE, download_one, image_stats

DOSE_BY_COLUMN = {
    2: 0.0, 3: 0.61, 4: 1.22, 5: 2.44, 6: 4.88,
    7: 9.77, 8: 19.53, 9: 39.06, 10: 78.13, 11: 156.25,
}
ROWS = "CDE"


def manifest() -> list[dict]:
    out = []
    for col, dose in DOSE_BY_COLUMN.items():
        for row in ROWS:
            well = f"{row}-{col:02d}"
            for t, c, channel in (
                (1, "C01", "Hoechst"), (13, "C01", "Hoechst"),
                (14, "C05", "AnnexinV_terminal"),
            ):
                name = f"{well}_F0001_T{t:04d}_Z0001_{c}.tif"
                out.append(dict(well=well, dose_nm=dose, timepoint=t,
                                channel=channel, filename=name, url=f"{BASE}/{name}"))
    return out


def well_table(measurements: list[dict]) -> list[dict]:
    index = {(m["well"], m["timepoint"]): m for m in measurements}
    wells = []
    for col, dose in DOSE_BY_COLUMN.items():
        for row in ROWS:
            well = f"{row}-{col:02d}"
            first, last, terminal = (index[(well, t)] for t in (1, 13, 14))
            wells.append(dict(
                well=well, dose_nm=dose,
                t1_mean=first["corrected_mean"], t1_p99=first["corrected_p99"],
                t13_mean=last["corrected_mean"], t13_p99=last["corrected_p99"],
                delta_mean=last["corrected_mean"] - first["corrected_mean"],
                delta_p99=last["corrected_p99"] - first["corrected_p99"],
                terminal_annexinv_mean=terminal["corrected_mean"],
                terminal_annexinv_p99=terminal["corrected_p99"],
            ))
    return wells


def permutation_spearman(x: np.ndarray, y: np.ndarray, rng: np.random.Generator,
                         n_perm: int) -> dict:
    xr, yr = rankdata(x).astype(float), rankdata(y).astype(float)
    xr, yr = xr - xr.mean(), yr - yr.mean()
    denom = float(np.linalg.norm(xr) * np.linalg.norm(yr))
    if denom <= 0:
        return dict(rho=None, permutation_p_two_sided=None, n_perm=n_perm)
    observed = float(xr @ yr / denom)
    extreme = 0
    for _ in range(n_perm):
        shuffled = rng.permutation(yr)
        if abs(float(xr @ shuffled / denom)) >= abs(observed) - 1e-12:
            extreme += 1
    return dict(rho=observed, permutation_p_two_sided=(extreme + 1) / (n_perm + 1),
                n_perm=n_perm)


def well_cv(wells: list[dict], features: list[str], target: str) -> dict:
    X = np.array([[float(w[f]) for f in features] for w in wells])
    y = np.array([float(w[target]) for w in wells])
    predictions = np.zeros(len(wells))
    for train, test in LeaveOneOut().split(X):
        model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        model.fit(X[train], y[train])
        predictions[test] = model.predict(X[test])
    return dict(
        mae=float(mean_absolute_error(y, predictions)),
        r2=float(r2_score(y, predictions)),
        predictions=[dict(well=w["well"], observed=float(y[i]),
                          predicted=float(predictions[i])) for i, w in enumerate(wells)],
    )


def analyze(measurements: list[dict], *, n_perm: int = 9999) -> tuple[dict, list[dict]]:
    if len(measurements) != 90:
        raise ValueError(f"Expected 90 images, got {len(measurements)}")
    wells = well_table(measurements)
    if len(wells) != 30 or len({w["well"] for w in wells}) != 30:
        raise ValueError("Expected 30 distinct wells")
    dose = np.array([w["dose_nm"] for w in wells])
    rng = np.random.default_rng(20261009)
    primary = permutation_spearman(
        dose, np.array([w["terminal_annexinv_p99"] for w in wells]), rng, n_perm)
    secondary = permutation_spearman(
        dose, np.array([w["delta_p99"] for w in wells]), rng, n_perm)
    # Holm adjustment for the TWO declared dose-response hypotheses.
    pvals = [primary["permutation_p_two_sided"], secondary["permutation_p_two_sided"]]
    if all(p is not None for p in pvals):
        order = sorted(range(2), key=lambda i: pvals[i])
        adjusted = [0.0, 0.0]
        adjusted[order[0]] = min(1.0, 2 * pvals[order[0]])
        adjusted[order[1]] = min(1.0, max(adjusted[order[0]], pvals[order[1]]))
        primary["holm_p_two_tests"] = adjusted[0]
        secondary["holm_p_two_tests"] = adjusted[1]
    control = [w for w in wells if w["dose_nm"] == 0.0]
    high = [w for w in wells if w["dose_nm"] == 156.25]
    contrasts = {}
    for key in ("terminal_annexinv_p99", "terminal_annexinv_mean", "delta_p99",
                "delta_mean"):
        cm = float(np.mean([w[key] for w in control]))
        hm = float(np.mean([w[key] for w in high]))
        contrasts[key] = dict(control_mean=cm, high_dose_mean=hm, high_minus_control=hm-cm)
    baseline = well_cv(wells, ["t1_mean", "t1_p99"], "terminal_annexinv_p99")
    temporal = well_cv(wells, ["t1_mean", "t1_p99", "delta_mean", "delta_p99"],
                       "terminal_annexinv_p99")
    report = dict(
        study="S-BIAD2515",
        status="REAL_IMAGES_EXPLORATORY_NOT_CELL_PHENOTYPE_VALIDATION",
        n_wells=30, n_doses=10, wells_per_dose=3, n_images=90,
        primary_predeclared_terminal_annexinv_p99_vs_dose=primary,
        secondary_predeclared_hoechst_delta_p99_vs_dose=secondary,
        descriptive_high_dose_vs_control=contrasts,
        heldout_well_cv=dict(
            target="Terminal AnnexinV image-level corrected p99, NOT cell-level apoptosis",
            baseline_t1_only=baseline, temporal_t1_plus_t13_delta=temporal,
            mae_improvement_baseline_minus_temporal=baseline["mae"]-temporal["mae"],
            r2_improvement_temporal_minus_baseline=temporal["r2"]-baseline["r2"],
            method="Leave-one-well-out fixed Ridge alpha=10, per-fold standardization",
            dose_is_not_a_predictor=True),
        claim_boundary=(
            "30 independent wells from one plate; NOT single-cell apoptosis labels, "
            "tracking, or AI4S phenotype validation. Each dose occupies one plate column: "
            "spatial confounding cannot be ruled out. One field of view per well. Image "
            "intensity can be affected by density/acquisition/background. Correlation "
            "and held-out-well prediction cannot establish causal dose effects, clinical "
            "utility or competition ranking."),
    )
    return report, wells


def save_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="external_biology/gide_30well")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--permutations", type=int, default=9999)
    args = p.parse_args()
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    images = manifest()
    (root / "manifest.json").write_text(json.dumps(images, indent=2), encoding="utf-8")
    if args.dry_run:
        print(json.dumps(dict(n_images=len(images), n_wells=30,
                              first=images[0], last=images[-1])))
        return
    storage = root / "tiffs"
    storage.mkdir(exist_ok=True)
    measurements = []
    for i, image in enumerate(images, 1):
        path, sha = download_one(image, storage)
        measurements.append(dict(
            well=image["well"], dose_nm=image["dose_nm"],
            timepoint=image["timepoint"], channel=image["channel"],
            filename=image["filename"], sha256=sha,
            **image_stats(tifffile.imread(path))))
        print(f"[{i}/{len(images)}] {image['filename']}", flush=True)
    save_csv(measurements, root / "image_features.csv")
    report, wells = analyze(measurements, n_perm=args.permutations)
    save_csv(wells, root / "well_features.csv")
    (root / "summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    brief = {k: v for k, v in report.items() if k != "heldout_well_cv"}
    cv = report["heldout_well_cv"]
    brief["heldout_well_cv"] = {
        "baseline_t1_only": {k:v for k,v in cv["baseline_t1_only"].items()
                            if k != "predictions"},
        "temporal_t1_plus_t13_delta": {
            k:v for k,v in cv["temporal_t1_plus_t13_delta"].items()
            if k != "predictions"},
        "mae_improvement_baseline_minus_temporal":
            cv["mae_improvement_baseline_minus_temporal"],
        "r2_improvement_temporal_minus_baseline":
            cv["r2_improvement_temporal_minus_baseline"],
    }
    print(json.dumps(brief, indent=2, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
