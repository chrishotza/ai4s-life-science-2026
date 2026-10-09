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
