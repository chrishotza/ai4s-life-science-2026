#!/usr/bin/env python3
"""Bounded GIDE TIFF pilot: exploratory image-level data, NOT validated cell phenotypes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import tifffile
from scipy.stats import spearmanr

BASE = "https://ftp.ebi.ac.uk/biostudies/fire/S-BIAD/515/S-BIAD2515/Files"
WELLS = {"C-02": 0.0, "D-02": 0.0, "E-02": 0.0,
         "C-11": 156.25, "D-11": 156.25, "E-11": 156.25}
TIMES = (1, 7, 13)


def manifest() -> list[dict]:
    items = []
    for well, dose in sorted(WELLS.items()):
        for t in TIMES:
            name = f"{well}_F0001_T{t:04d}_Z0001_C01.tif"
            items.append(dict(well=well, dose_nm=dose, timepoint=t, channel="Hoechst",
                              filename=name, url=f"{BASE}/{name}"))
        name = f"{well}_F0001_T0014_Z0001_C05.tif"
        items.append(dict(well=well, dose_nm=dose, timepoint=14,
                          channel="AnnexinV_terminal", filename=name, url=f"{BASE}/{name}"))
    return items


def download_one(item: dict, directory: Path) -> tuple[Path, str]:
    target = directory / item["filename"]
    if target.exists() and target.stat().st_size > 1000:
        with target.open("rb") as f:
            good = f.read(2) in (b"II", b"MM")
        if good:
            return target, hashlib.sha256(target.read_bytes()).hexdigest()
        target.unlink()
    err = None
    for attempt in range(3):
        tmp = target.with_suffix(".partial")
        try:
            req = Request(item["url"], headers={"User-Agent": "AI4S-GIDE-pilot/1.0"})
            with urlopen(req, timeout=55) as response, tmp.open("wb") as dest:
                count = 0
                while chunk := response.read(524288):
                    count += len(chunk)
                    if count > 15_000_000:
                        raise ValueError("Unexpectedly large download")
                    dest.write(chunk)
            with tmp.open("rb") as f:
                if f.read(2) not in (b"II", b"MM"):
                    raise ValueError("Not a TIFF download")
            tmp.replace(target)
            return target, hashlib.sha256(target.read_bytes()).hexdigest()
        except (OSError, ValueError) as exc:
            err = exc
            tmp.unlink(missing_ok=True)
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Cannot download {item['url']}: {err}")


def image_stats(image: np.ndarray) -> dict:
    image = np.squeeze(np.asarray(image))
    if image.ndim != 2 or image.size < 100:
        raise ValueError(f"Expected one 2D plane, got {image.shape}")
    arr = image.astype(np.float32)
    if not np.isfinite(arr).all():
        raise ValueError("Non-finite image pixel values")
    q10, q50, q90, q99 = np.percentile(arr, (10, 50, 90, 99))
    corrected = np.maximum(arr - q10, 0)
    return dict(mean=float(arr.mean()), std=float(arr.std()),
                p10=float(q10), p50=float(q50), p90=float(q90), p99=float(q99),
                corrected_mean=float(corrected.mean()),
                corrected_p99=float(q99 - q10), pixels=int(arr.size))


def summarize(records: list[dict]) -> dict:
    lookup = {(r["well"], r["timepoint"]): r for r in records}
    well_rows = []
    for well, dose in sorted(WELLS.items()):
        early, mid, late, end = (lookup[(well, t)] for t in (1, 7, 13, 14))
        well_rows.append(dict(
            well=well, dose_nm=dose,
            delta_hoechst_corrected_mean=late["corrected_mean"]-early["corrected_mean"],
            delta_hoechst_p99=late["corrected_p99"]-early["corrected_p99"],
            hoechst_mean_early=early["corrected_mean"],
            hoechst_mean_mid=mid["corrected_mean"],
            hoechst_mean_late=late["corrected_mean"],
            annexinv_terminal_corrected_mean=end["corrected_mean"],
            annexinv_terminal_corrected_p99=end["corrected_p99"]))
    comparisons = {}
    for key in ("delta_hoechst_corrected_mean", "delta_hoechst_p99",
                "annexinv_terminal_corrected_mean", "annexinv_terminal_corrected_p99"):
        control = [r[key] for r in well_rows if r["dose_nm"] == 0]
        treated = [r[key] for r in well_rows if r["dose_nm"] > 0]
        comparisons[key] = dict(
            control_mean=float(np.mean(control)), treated_mean=float(np.mean(treated)),
            treated_minus_control=float(np.mean(treated) - np.mean(control)))
    endpoint = [r["annexinv_terminal_corrected_mean"] for r in well_rows]
    associations = {}
    for key in ("delta_hoechst_corrected_mean", "delta_hoechst_p99"):
        result = spearmanr([r[key] for r in well_rows], endpoint)
        associations[key] = dict(spearman_r=float(result.statistic),
                                 nominal_p=float(result.pvalue))
    return dict(status="EXPLORATORY_IMAGE_LEVEL_ONLY",
                source="EMBL-EBI S-BIAD2515", n_wells=6, n_images=len(records),
                well_level=well_rows, group_descriptives=comparisons,
                exploratory_correlations=associations,
                scientific_limits=(
                    "Three wells per group; one FOV; Hoechst time-series and "
                    "terminal Annexin V images. Annexin image fluorescence is an "
                    "UNSEGMENTED PROXY, not single-cell apoptosis ground truth. "
                    "Correlations are descriptive, not multiple-testing adjusted. "
                    "This is NOT a validation of AI4S temporal phenotypes, a clinical "
                    "endpoint, a competitive benchmark or an official Kaggle score."
                ))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default="external_biology/gide_tiff_pilot")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reuse-local", action="store_true")
    args = p.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    items = manifest()
    (root / "manifest.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    if args.dry_run:
        print(json.dumps({"n_images": len(items), "first": items[0]}, indent=2))
        return
    d = root / "tiffs"
    d.mkdir(exist_ok=True)
    records = []
    for i, item in enumerate(items, 1):
        if args.reuse_local:
            path = d / item["filename"]
            if not path.is_file():
                raise FileNotFoundError(path)
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            path, sha = download_one(item, d)
        record = dict(
            well=item["well"], dose_nm=item["dose_nm"],
            timepoint=item["timepoint"], channel=item["channel"],
            filename=item["filename"], sha256=sha,
            **image_stats(tifffile.imread(path)))
        records.append(record)
        print(f"[{i}/{len(items)}] {item['filename']} measured", flush=True)
    with (root / "image_features.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    report = summarize(records)
    (root / "summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
