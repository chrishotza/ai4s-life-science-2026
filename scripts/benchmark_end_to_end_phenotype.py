from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_core import runtime_metadata

from ai4s_phenotype import analyze, discover_phenotypes
from ai4s_tracking import TrackingConfig, track_detections

N_FRAMES = 36
METHODS = ("mutual_nn", "gap_hungarian")
GROUPS = {
    "persistent_slow": {"speed": 0.45, "turn": 0.02},
    "persistent_fast": {"speed": 1.05, "turn": 0.02},
    "exploratory": {"speed": 0.75, "turn": 0.35},
}


def make_detections(seed: int = 29, tracks_per_group: int = 10) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    truth_track = 0

    for group_name, cfg in GROUPS.items():
        for _ in range(tracks_per_group):
            position = rng.uniform(10.0, 50.0, size=3)
            direction = rng.normal(size=3)
            direction /= np.linalg.norm(direction)

            for t in range(N_FRAMES):
                if group_name == "exploratory" and t > 0:
                    direction += rng.normal(0.0, cfg["turn"], size=3)
                    direction /= np.linalg.norm(direction)
                position = position + cfg["speed"] * direction
                rows.append(
                    (
                        t,
                        position[0],
                        position[1],
                        position[2],
                        truth_track,
                        group_name,
                    )
                )

            truth_track += 1

    return pd.DataFrame(
        rows,
        columns=["t", "z", "y", "x", "truth_track", "truth_group"],
    )


def perturb(
    detections: pd.DataFrame,
    noise_um: float,
    drop_rate: float,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = detections.copy()
    xyz = out[["z", "y", "x"]].to_numpy(float)
    xyz += rng.normal(0.0, noise_um, size=xyz.shape)
    out[["z", "y", "x"]] = xyz

    if drop_rate:
        keep = rng.random(len(out)) >= drop_rate
        out = out.loc[keep].copy()

    return out.sort_values(["t", "truth_track"]).reset_index(drop=True)


def track_purity(nodes: pd.DataFrame) -> tuple[float, float, int]:
    if nodes.empty:
        return 0.0, 0.0, 0

    rows = []
    for predicted_track, group in nodes.groupby("track_id"):
        counts = group["truth_track"].value_counts()
        majority = int(counts.iloc[0])
        rows.append(
            {
                "predicted_track": int(predicted_track),
                "truth_track": int(counts.index[0]),
                "purity": majority / max(1, len(group)),
                "observations": len(group),
            }
        )

    frame = pd.DataFrame(rows)
    dominant = frame[frame["purity"] >= 0.80]
    return (
        float(frame["purity"].mean()),
        float(dominant["purity"].mean()) if len(dominant) else 0.0,
        int(len(dominant)),
    )


def run_case(noise_um: float, drop_rate: float, seed: int, method: str) -> dict[str, float | int | str]:
    raw = perturb(
        make_detections(),
        noise_um=noise_um,
        drop_rate=drop_rate,
        seed=seed,
    )
    nodes, edges = track_detections(
        raw[["t", "z", "y", "x"]],
        TrackingConfig(
            max_distance_um=2.5,
            method=method,
            voxel_size_um=(1.0, 1.0, 1.0),
            max_frame_gap=2 if method == "gap_hungarian" else 1,
        ),
    )
    raw_sorted = raw.sort_values(["t", "z", "y", "x"]).reset_index(drop=True)
    nodes["truth_track"] = raw_sorted["truth_track"].to_numpy()
    truth_groups = raw.drop_duplicates("truth_track").set_index("truth_track")["truth_group"].to_dict()
    phenotypes = analyze(nodes, edges)
    discovered = (
        discover_phenotypes(
            phenotypes,
            n_clusters=3,
            random_state=17,
        )
        if len(phenotypes) >= 3
        else phenotypes.assign(
            phenotype_cluster=-1,
            phenotype_cluster_name="insufficient_cells",
        )
    )

    purity_mean, purity_stable, stable_tracks = track_purity(nodes)

    label_frame = nodes.groupby("track_id")["truth_track"].agg(
        lambda series: int(series.value_counts().index[0])
    )
    predicted_groups = [
        truth_groups[int(truth_track)]
        for truth_track in label_frame.to_numpy()
        if int(truth_track) in truth_groups
    ]
    cluster_frame = discovered.merge(
        pd.Series(
            [truth_groups[int(v)] for v in label_frame.to_numpy()],
            name="truth_group",
            index=label_frame.index,
        ),
        left_on="track_id",
        right_index=True,
        how="inner",
    )

    phenotype_ari = (
        adjusted_rand_score(
            cluster_frame["truth_group"],
            cluster_frame["phenotype_cluster"],
        )
        if len(cluster_frame) >= 3
        else 0.0
    )

    return {
        "method": method,
        "noise_um": noise_um,
        "drop_rate": drop_rate,
        "tracks_predicted": int(nodes["track_id"].nunique()),
        "mean_track_purity": purity_mean,
        "stable_track_purity": purity_stable,
        "stable_tracks": stable_tracks,
        "phenotype_group_ARI": float(phenotype_ari),
    }


def main() -> None:
    cases = [
        (0.00, 0.00),
        (0.10, 0.05),
        (0.20, 0.10),
        (0.35, 0.15),
    ]
    rows = [
        run_case(noise, drop, 500 + index, method)
        for method in METHODS
        for index, (noise, drop) in enumerate(cases)
    ]
    frame = pd.DataFrame(rows)

    print(frame.to_string(index=False))

    output = {
        "runtime": runtime_metadata(),
        "benchmark": "end-to-end tracking to phenotype robustness",
        "purpose": "evaluate temporal phenotype discovery after re-tracking perturbed synthetic detections",
        "synthetic_groups": list(GROUPS),
        "cases": rows,
    }
    (ROOT / "end_to_end_phenotype_results.json").write_text(
        json.dumps(output, indent=2)
    )


if __name__ == "__main__":
    main()
