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
    if radius <= 0:
        raise ValueError("radius must be positive")

    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    margin = min(12.0, max(1.0, min(height, width) / 4.0))
    low = margin
    high = min(height, width) - margin
    if high <= low:
        low = 0.5
        high = max(low + 1.0, min(height, width) - 0.5)
    start = rng.uniform(low, high, size=(cells, 2))
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
