import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_demo_video import physical_coordinates_for_phenotype


def test_demo_phenotype_coordinates_are_converted_to_micrometers_without_mutating_pixels():
    pixels = pd.DataFrame(
        [
            {"node_id": 0, "track_id": 3, "t": 0, "z": 0.0, "y": 10.0, "x": 20.0},
            {"node_id": 1, "track_id": 3, "t": 1, "z": 0.0, "y": 15.0, "x": 30.0},
        ]
    )

    physical = physical_coordinates_for_phenotype(pixels)

    assert physical[["z", "y", "x"]].to_numpy() == pytest.approx(
        np.array([[0.0, 1.9, 3.8], [0.0, 2.85, 5.7]])
    )
    assert pixels.loc[0, "y"] == 10.0
    assert pixels.loc[0, "x"] == 20.0
