from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CohortComparison:
    """Uncertainty-aware comparison of two phenotype cohorts."""

    group_a: str
    group_b: str
    features: tuple[str, ...]
    table: pd.DataFrame


def _bootstrap_mean_difference(
    a: np.ndarray,
    b: np.ndarray,
    *,
    rng: np.random.Generator,
    n_bootstrap: int,
) -> tuple[float, float]:
    if len(a) == 0 or len(b) == 0:
        return float("nan"), float("nan")
    draws_a = rng.choice(a, size=(n_bootstrap, len(a)), replace=True)
    draws_b = rng.choice(b, size=(n_bootstrap, len(b)), replace=True)
    differences = draws_a.mean(axis=1) - draws_b.mean(axis=1)
    return float(np.quantile(differences, 0.025)), float(np.quantile(differences, 0.975))


def compare_cohorts(
    phenotypes: pd.DataFrame,
    *,
    group_column: str,
    group_a: str,
    group_b: str,
    features: tuple[str, ...] = (
        "mean_speed",
        "directional_persistence",
        "displacement",
        "path_length",
        "observation_fraction",
    ),
    random_state: int = 17,
    n_bootstrap: int = 2000,
) -> CohortComparison:
    """Compare two cohorts with effect sizes and bootstrap confidence intervals.

    The comparison is descriptive/inferential at the cohort level; it does not
    assign biological meaning to a feature without external biological labels.
    """
    if group_column not in phenotypes.columns:
        raise ValueError(f"missing cohort column: {group_column}")
    if group_a == group_b:
        raise ValueError("group_a and group_b must differ")
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be >= 100")

    required = [*features]
    missing = [column for column in required if column not in phenotypes.columns]
    if missing:
        raise ValueError(f"phenotypes missing columns: {missing}")

    a_frame = phenotypes.loc[phenotypes[group_column].eq(group_a)]
    b_frame = phenotypes.loc[phenotypes[group_column].eq(group_b)]
    if a_frame.empty or b_frame.empty:
        raise ValueError("both cohorts must contain at least one trajectory")

    rng = np.random.default_rng(random_state)
    rows: list[dict[str, float | str | int]] = []

    for feature in features:
        a = a_frame[feature].to_numpy(float)
        b = b_frame[feature].to_numpy(float)
        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]
        if len(a) < 2 or len(b) < 2:
            raise ValueError(
                f"feature {feature} needs at least two finite observations in each cohort"
            )

        pooled = np.sqrt(
            ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1))
            / max(1, len(a) + len(b) - 2)
        )
        standardized = float((np.mean(a) - np.mean(b)) / pooled) if pooled > 0 else float("nan")
        ci_low, ci_high = _bootstrap_mean_difference(
            a,
            b,
            rng=rng,
            n_bootstrap=n_bootstrap,
        )
        rows.append(
            {
                "feature": feature,
                "group_a_n": int(len(a)),
                "group_b_n": int(len(b)),
                "group_a_mean": float(np.mean(a)),
                "group_b_mean": float(np.mean(b)),
                "mean_difference_a_minus_b": float(np.mean(a) - np.mean(b)),
                "standardized_mean_difference": standardized,
                "bootstrap_ci_low": ci_low,
                "bootstrap_ci_high": ci_high,
                "effect_confident_nonzero": bool(ci_low > 0 or ci_high < 0),
            }
        )

    return CohortComparison(
        group_a=group_a,
        group_b=group_b,
        features=tuple(features),
        table=pd.DataFrame(rows),
    )
