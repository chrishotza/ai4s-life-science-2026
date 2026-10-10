"""Randomized exact oracle for deterministic physical-gate assignment."""
from __future__ import annotations

import numpy as np

from ai4s_tracking.tracker import _gated_assignment_indices


def _oracle(valid: np.ndarray, cost: np.ndarray) -> tuple[int, float]:
    n, m = valid.shape
    best_count, best_cost = 0, float("inf")

    def search(row: int, used: set[int], total: float, count: int) -> None:
        nonlocal best_count, best_cost
        if row == n:
            if count > best_count or (count == best_count and total < best_cost):
                best_count, best_cost = count, total
            return
        search(row + 1, used, total, count)
        for column in range(m):
            if valid[row, column] and column not in used:
                search(row + 1, used | {column},
                       total + float(cost[row, column]), count + 1)

    search(0, set(), 0.0, 0)


def test_gated_assignment_maximizes_cardinality_then_minimizes_cost():
    rng = np.random.default_rng(20261010)
    for n in range(1, 5):
        for m in range(1, 5):
            for _ in range(60):
                valid = rng.random((n, m)) < 0.35
                costs = rng.random((n, m))
                actual = _gated_assignment_indices(costs, valid)
                expected_count, expected_cost = _oracle(valid, costs)
                assert len(actual) == expected_count
                assert len({i for i, _ in actual}) == len(actual)
                assert len({j for _, j in actual}) == len(actual)
                assert all(valid[i, j] for i, j in actual)
                assert abs(sum(costs[i, j] for i, j in actual) - expected_cost) < 1e-9
