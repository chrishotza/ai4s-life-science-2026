from __future__ import annotations

import numpy as np


def moving_blobs(
    frames: int = 12,
    height: int = 96,
    width: int = 96,
    cells: int = 8,
    radius: float = 3.0,
    amplitude: float = 1.0,
    noise: float = 0.03,
    seed: int = 19,
) -> np.ndarray:
    """Create a deterministic microscopy-like stack of moving bright cells."""
    if min(frames, height, width, cells) < 1:
        raise ValueError("dimensions must be positive")

    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    start = rng.uniform(12, min(height, width) - 12, size=(cells, 2))
    velocity = rng.normal(0, 0.8, size=(cells, 2))

    stack = np.zeros((frames, height, width), dtype=np.float32)
    for t in range(frames):
        frame = rng.normal(0, noise, size=(height, width))
        for cell in range(cells):
            cy, cx = start[cell] + velocity[cell] * t
            blob = np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * radius**2))
            frame += amplitude * blob
        stack[t] = frame

    return stack
