from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SyntheticConfig:
    frames: int = 12
    cells: int = 8
    step_um: float = 1.0
    noise_um: float = 0.0
    seed: int = 7


def generate_synthetic(config: SyntheticConfig = SyntheticConfig()) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate deterministic 3-D trajectories and exact consecutive-frame links."""
    if config.frames < 2 or config.cells < 1:
        raise ValueError("frames must be >= 2 and cells must be >= 1")

    rng = np.random.default_rng(config.seed)
    rows = []
    node = 0

    starts = rng.uniform(0, 40, size=(config.cells, 3))
    velocities = rng.normal(0, config.step_um / 2, size=(config.cells, 3))

    for t in range(config.frames):
        for cell in range(config.cells):
            xyz = starts[cell] + velocities[cell] * t
            if config.noise_um:
                xyz = xyz + rng.normal(0, config.noise_um, size=3)
            rows.append((node, cell, t, xyz[0], xyz[1], xyz[2]))
            node += 1

    truth = pd.DataFrame(rows, columns=["node_id", "cell_id", "t", "z", "y", "x"])
    truth_edges = pd.DataFrame(
        [
            (a, b)
            for cell in range(config.cells)
            for t in range(config.frames - 1)
            for a, b in [
                (
                    int(truth.loc[(truth.cell_id == cell) & (truth.t == t), "node_id"].iloc[0]),
                    int(truth.loc[(truth.cell_id == cell) & (truth.t == t + 1), "node_id"].iloc[0]),
                )
            ]
        ],
        columns=["source_id", "target_id"],
    )
    return truth, truth_edges
