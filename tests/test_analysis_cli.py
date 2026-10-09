from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

from ai4s_imaging.synthetic import moving_blobs


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_microscopy.py"


def test_cli_runs_a_tiff_directory_and_writes_machine_readable_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "microscopy"
    output_dir = tmp_path / "analysis"
    input_dir.mkdir()

    frames = moving_blobs(frames=8, height=64, width=64, cells=4, seed=7)
    for index, frame in enumerate(frames):
        tifffile.imwrite(input_dir / f"frame_{index:03d}.tif", frame.astype(np.float32))

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(input_dir),
            "--output",
            str(output_dir),
            "--threshold",
            "0.45",
            "--min-area",
            "4",
            "--max-distance-um",
            "4.0",
            "--clusters",
            "2",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    expected = {
        "nodes.csv",
        "temporal_edges.csv",
        "lineage_candidates.csv",
        "phenotypes.csv",
        "discovered_phenotypes.csv",
        "summary.json",
        "overview.png",
        "report.md",
    }
    assert expected.issubset({path.name for path in output_dir.iterdir()})

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["frames"] == 8
    assert summary["pipeline"]["detections"] > 0
    assert summary["pipeline"]["tracks"] > 0
    assert (output_dir / "report.md").read_text(encoding="utf-8").find(
        "not validated biological states"
    ) >= 0


def test_cli_rejects_missing_input(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(missing),
            "--output",
            str(tmp_path / "output"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "Input path does not exist" in completed.stderr


def test_cli_supervised_mode_exports_predicted_instance_masks(tmp_path: Path) -> None:
    rng = np.random.default_rng(31)
    height = width = 64
    yy, xx = np.mgrid[:height, :width]
    train_images = tmp_path / "train_images"
    train_masks = tmp_path / "train_masks"
    target_images = tmp_path / "target_images"
    output_dir = tmp_path / "supervised_analysis"
    train_images.mkdir()
    train_masks.mkdir()
    target_images.mkdir()

    frames = []
    masks = []
    for t in range(8):
        image = rng.normal(0.08, 0.015, size=(height, width)).astype(np.float32)
        instance_mask = np.zeros((height, width), dtype=np.uint16)
        for label_id, (cy, cx) in enumerate(((17 + t // 2, 20 + t), (43 - t // 3, 42 - t)), start=1):
            cell = (yy - cy) ** 2 + (xx - cx) ** 2 <= 6**2
            instance_mask[cell] = label_id
            image[cell] += 0.65
        frames.append(image)
        masks.append(instance_mask)

    for t in range(6):
        tifffile.imwrite(train_images / f"t{t:03d}.tif", frames[t])
        tifffile.imwrite(train_masks / f"man_track{t:03d}.tif", masks[t])
    for t in range(6, 8):
        tifffile.imwrite(target_images / f"t{t:03d}.tif", frames[t])

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(target_images),
            "--output",
            str(output_dir),
            "--training-images",
            str(train_images),
            "--training-masks",
            str(train_masks),
            "--max-training-frames",
            "6",
            "--samples-per-class",
            "200",
            "--min-area",
            "8",
            "--max-distance-um",
            "5",
            "--clusters",
            "2",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + "\\n" + completed.stderr
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["detector"]["method"] == "supervised_random_forest_interior_boundary"
    assert summary["detector"]["training_frames_matched"] == 6
    predicted_masks = tifffile.imread(output_dir / "predicted_instances.tif")
    assert predicted_masks.shape == (2, height, width)
    assert np.count_nonzero(np.unique(predicted_masks) > 0) >= 1
