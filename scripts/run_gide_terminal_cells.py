#!/usr/bin/env python3
"""Image-registered terminal nuclear-proximal Annexin V (GIDE S-BIAD2515).

Terminal T14 Hoechst C01 is segmented and same-FOV T14 AnnexinV C05 sampled in
per-nucleus nearby rings. Not a cell-fate label, tracking, or phenotyping claim.
Dose and plate column are fully confounded; statistics use WELLS, not cells.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage as ndi
from scipy.stats import rankdata
from skimage.filters import gaussian, threshold_otsu
from skimage.measure import label, regionprops
from skimage.morphology import closing, opening, disk, remove_small_objects
from skimage.segmentation import clear_border, find_boundaries

from scripts.run_gide_tiff_pilot import BASE, download_one

DOSES = {2: 0., 3: .61, 4: 1.22, 5: 2.44, 6: 4.88,
         7: 9.77, 8: 19.53, 9: 39.06, 10: 78.13, 11: 156.25}


def manifest():
    out = []
    for col, dose in DOSES.items():
        for row in "CDE":
            well = f"{row}-{col:02d}"
            for code, channel in (("C01", "Hoechst_terminal"),
                                  ("C05", "AnnexinV_terminal")):
                filename = f"{well}_F0001_T0014_Z0001_{code}.tif"
                out.append(dict(well=well, dose_nm=dose, channel=channel,
                                filename=filename, url=f"{BASE}/{filename}"))
    return out


def write_csv(rows, path):
    if not rows:
        raise ValueError("No records to save")
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def segment_nuclei(hoechst, min_area=110, max_area=7000):
    data = np.squeeze(hoechst).astype("float32")
    if data.ndim != 2 or not np.isfinite(data).all() or float(data.std()) < 1e-5:
        raise ValueError("Invalid Hoechst image")
    corrected = gaussian(data, sigma=1.2, preserve_range=True)
    corrected -= gaussian(data, sigma=26, preserve_range=True)
    threshold = max(float(threshold_otsu(corrected)),
                    float(np.percentile(corrected, 76)))
    foreground = corrected > threshold
    foreground = opening(foreground, footprint=disk(2))
    foreground = closing(foreground, footprint=disk(2))
    foreground = remove_small_objects(foreground, min_size=min_area)
    foreground = clear_border(foreground)
    # QC review of original C-02 and D-02 images found watershed broke each
    # nucleus into many fragments. Connected components preserve intact nuclei.
    # Touching cells may merge; this limitation is recorded, not overfitted.
    masks = label(foreground)
    counts = np.bincount(masks.ravel())
    valid = (counts >= min_area) & (counts <= max_area)
    valid[0] = False
    masks = np.where(valid[masks], masks, 0).astype("int32")
    ids = np.unique(masks)
    ids = ids[ids != 0]
    mapping = np.zeros(int(masks.max()) + 1, dtype="int32")
    mapping[ids] = np.arange(1, len(ids) + 1)
    masks = mapping[masks]
    areas = np.bincount(masks.ravel())[1:]
    n = len(ids)
    fraction = float(np.mean(masks > 0))
    qc = dict(n_nuclei=n, foreground_fraction=fraction,
              median_nucleus_area=float(np.median(areas)) if n else None,
              qc_pass=bool(10 <= n <= 3000 and 0.0003 < fraction < 0.55))
    return masks, qc


def measure_annexin_near_nuclei(nuclei, annexin, ring_radius=12):
    if annexin.shape != nuclei.shape:
        raise ValueError("Unaligned channel image shapes")
    img = np.asarray(annexin, dtype="float32")
    img = np.maximum(img - float(np.percentile(img, 10)), 0)
    cells = []
    for region in regionprops(nuclei):
        min_y, min_x, max_y, max_x = region.bbox
        y0, x0 = max(0, min_y-ring_radius), max(0, min_x-ring_radius)
        y1 = min(nuclei.shape[0], max_y+ring_radius)
        x1 = min(nuclei.shape[1], max_x+ring_radius)
        local_mask = nuclei[y0:y1, x0:x1]
        nucleus = local_mask == region.label
        # Exclude ALL segmented nuclei; adjacent cytoplasm can still overlap.
        ring = ndi.binary_dilation(nucleus, structure=disk(ring_radius)) & (local_mask == 0)
        if int(ring.sum()) < 30:
            continue
        values = img[y0:y1, x0:x1][ring]
        cells.append(dict(nucleus_id=int(region.label), nucleus_area=int(region.area),
                          centroid_y=float(region.centroid[0]),
                          centroid_x=float(region.centroid[1]),
                          ann_ring_mean=float(np.mean(values)),
                          ann_ring_p90=float(np.percentile(values, 90)),
                          ann_ring_p99=float(np.percentile(values, 99)),
                          ring_pixels=len(values)))
    return cells


def rank_permutation(x, y, rng, count):
    xa, ya = rankdata(np.asarray(x)), rankdata(np.asarray(y))
    xa, ya = xa-xa.mean(), ya-ya.mean()
    denominator = float(np.linalg.norm(xa)*np.linalg.norm(ya))
    if denominator <= 0:
        return dict(rho=None, permutation_p=None, n_perm=count)
    rho = float(xa@ya/denominator)
    extreme = 0
    for _ in range(count):
        extreme += abs(float(xa@rng.permutation(ya)/denominator)) >= abs(rho)-1e-12
    return dict(rho=rho, permutation_p=(1+extreme)/(1+count), n_perm=count)


def summarize(wells, permutations=9999):
    if len(wells) != 30 or len({w["well"] for w in wells}) != 30:
        raise ValueError("Expected 30 unique well records including rejected samples")
    valid = [w for w in wells if w["qc_pass"] and w["median_ann_ring_p90"] is not None]
    groups = {dose: [w for w in valid if w["dose_nm"] == dose] for dose in DOSES.values()}
    accepted = len(valid) >= 24 and all(len(group) >= 2 for group in groups.values())
    details = [
        dict(dose_nm=dose, accepted_wells=len(group),
             ann_ring_p90_mean=(float(np.mean([w["median_ann_ring_p90"] for w in group]))
                                if group else None),
             nuclei_mean=(float(np.mean([w["n_valid_nuclei"] for w in group]))
                          if group else None))
        for dose, group in groups.items()
    ]
    primary = secondary = None
    if accepted:
        rng = np.random.default_rng(20261009)
        dose = [w["dose_nm"] for w in valid]
        primary = rank_permutation(dose, [w["median_ann_ring_p90"] for w in valid],
                                   rng, permutations)
        secondary = rank_permutation(dose, [w["n_valid_nuclei"] for w in valid],
                                     rng, permutations)
    return dict(
        status=("EXPLORATORY_TERMINAL_NUCLEAR_PROXIMAL_SIGNAL"
                if accepted else "NO_GO_INSUFFICIENT_QC_COVERAGE"),
        n_wells_total=len(wells), n_wells_accepted=len(valid),
        n_wells_rejected=len(wells)-len(valid),
        n_cells_accepted=sum(w["n_valid_nuclei"] for w in valid),
        coverage_gate_pass=accepted,
        primary_dose_vs_median_ann_ring_p90=primary,
        secondary_dose_vs_nucleus_count=secondary,
        dose_means=details,
        claim_boundary=(
            "Terminal Hoechst connected-component nuclei with AnnexinV "
            "nearby pixel rings; not validated cell apoptosis or cell tracks. "
            "Image QC failures are excluded and listed; missingness by dose "
            "may bias association. Dose and plate column are confounded. "
            "Cells in the same well are not independent experimental units."
        ))


def save_overlay(image, masks, path):
    data = np.asarray(image, dtype="float32")
    a, b = np.percentile(data, (2, 99.5))
    gray = np.uint8(np.clip((data-a)/max(float(b-a), 1), 0, 1)*255)
    rgb = np.repeat(gray[:, :, None], 3, axis=2)
    rgb[find_boundaries(masks, mode="outer")] = [255, 70, 30]
    canvas = Image.fromarray(rgb)
    canvas.thumbnail((950, 950))
    canvas.save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="external_biology/gide_cell_terminal")
    p.add_argument("--permutations", type=int, default=9999)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sources = manifest()
    (out/"manifest.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    if args.dry_run:
        print(json.dumps(dict(n_files=len(sources), n_wells=30, first=sources[0])))
        return
    cache = out/"tiffs"
    cache.mkdir(exist_ok=True)
    cells_out, wells_out, failures = [], [], []
    for i in range(0, len(sources), 2):
        t_h, t_a = sources[i:i+2]
        if t_h["well"] != t_a["well"]:
            raise ValueError("Channel pairing mismatch")
        well, dose = t_h["well"], t_h["dose_nm"]
        qc = None
        cells = []
        try:
            p_h, hash_h = download_one(t_h, cache)
            p_a, hash_a = download_one(t_a, cache)
            h, a = tifffile.imread(p_h), tifffile.imread(p_a)
            masks, qc = segment_nuclei(h)
            cells = measure_annexin_near_nuclei(masks, a)
            if not cells:
                raise ValueError("No measurable nuclei or local Annexin ROI")
            if well in ("C-02", "D-02", "C-03", "C-04", "D-04", "E-04",
                        "C-05", "E-05", "C-09", "C-11", "D-11", "E-11"):
                save_overlay(h, masks, out/f"{well}_segmentation_qc.png")
            cells_out.extend(dict(well=well, dose_nm=dose, **rec) for rec in cells)
            wells_out.append(dict(
                well=well, dose_nm=dose, qc_pass=qc["qc_pass"],
                n_segmented_nuclei=qc["n_nuclei"], n_valid_nuclei=len(cells),
                median_nucleus_area=qc["median_nucleus_area"],
                foreground_fraction=qc["foreground_fraction"],
                median_ann_ring_mean=float(np.median([v["ann_ring_mean"] for v in cells])),
                median_ann_ring_p90=float(np.median([v["ann_ring_p90"] for v in cells])),
                terminal_hoechst_sha256=hash_h,
                terminal_annexinv_sha256=hash_a))
            print(f"[{i//2+1}/30] {well}: {qc['n_nuclei']} connected components, "
                  f"QC={qc['qc_pass']}", flush=True)
        except (OSError, ValueError, RuntimeError) as exc:
            failures.append(dict(well=well, dose_nm=dose, error=str(exc)[:400]))
            wells_out.append(dict(
                well=well, dose_nm=dose, qc_pass=False,
                n_segmented_nuclei=None, n_valid_nuclei=0,
                median_nucleus_area=None, foreground_fraction=None,
                median_ann_ring_mean=None, median_ann_ring_p90=None,
                terminal_hoechst_sha256=None, terminal_annexinv_sha256=None))
            print(f"[{i//2+1}/30] REJECTED {well}: {type(exc).__name__}: {exc}",flush=True)
        # Checkpoint every well: a corrupt original must never erase all prior evidence.
        write_csv(wells_out, out/"well_features.csv")
        if cells_out:
            write_csv(cells_out, out/"nucleus_annexin_proxy.csv")
        if failures:
            write_csv(failures, out/"failed_wells.csv")
    summary = summarize(wells_out, args.permutations)
    summary["failures"] = failures
    (out/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
