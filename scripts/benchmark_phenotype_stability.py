from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_phenotype import analyze, discover_phenotypes

N_FRAMES = 24
GROUPS = {
    "persistent_slow": {"speed": 0.35, "turn": 0.04},
    "persistent_fast": {"speed": 0.90, "turn": 0.03},
    "exploratory": {"speed": 0.70, "turn": 0.45},
}


def make_tracks(seed: int = 17, tracks_per_group: int = 12) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, str]]:
    rng = np.random.default_rng(seed)
    rows = []
    edges = []
    labels: dict[int, str] = {}
    node_id = 0
    track_id = 0

    for group_name, cfg in GROUPS.items():
        for _ in range(tracks_per_group):
            position = rng.uniform(10.0, 40.0, size=3)
            direction = rng.normal(size=3)
            direction /= np.linalg.norm(direction)
            previous = None

            for t in range(N_FRAMES):
                if group_name == "exploratory" and t > 0:
                    direction = direction + rng.normal(0, cfg["turn"], size=3)
                    direction /= np.linalg.norm(direction)
                position = position + direction * cfg["speed"]
                rows.append((node_id, track_id, t, *position))
                if previous is not None:
                    edges.append((previous, node_id))
                previous = node_id
                node_id += 1

            labels[track_id] = group_name
            track_id += 1

    nodes = pd.DataFrame(rows, columns=["node_id", "track_id", "t", "z", "y", "x"])
    edge_df = pd.DataFrame(edges, columns=["source_id", "target_id"])
    return nodes, edge_df, labels


def perturb(nodes: pd.DataFrame, noise_um: float, drop_rate: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = nodes.copy()
    xyz = out[["z", "y", "x"]].to_numpy(float)
    xyz += rng.normal(0.0, noise_um, size=xyz.shape)
    out[["z", "y", "x"]] = xyz
    if drop_rate:
        keep = rng.random(len(out)) >= drop_rate
        out = out.loc[keep].copy()
    return out.sort_values(["track_id", "t", "node_id"]).reset_index(drop=True)


def recompute_edges(nodes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, group in nodes.groupby("track_id", sort=False):
        ordered = group.sort_values("t")
        ids = ordered["node_id"].astype(int).to_list()
        for a, b in zip(ids, ids[1:]):
            rows.append((a, b))
    return pd.DataFrame(rows, columns=["source_id", "target_id"])


def main() -> None:
    nodes, edges, labels = make_tracks()
    baseline = discover_phenotypes(analyze(nodes, edges), n_clusters=3, random_state=17)

    name_to_expected = {
        "persistent_slow": "persistent_or_stable",
        "persistent_fast": "high_motility",
        "exploratory": "exploratory_motion",
    }

    baseline_expected = baseline["track_id"].map(labels).map(name_to_expected)
    baseline_cluster = baseline["phenotype_cluster"].to_numpy(int)

    rows = []
    for noise_um, drop_rate in ((0.00, 0.00), (0.10, 0.05), (0.20, 0.10), (0.35, 0.15)):
        perturbed = perturb(nodes, noise_um, drop_rate, seed=100 + int(noise_um * 1000) + int(drop_rate * 100))
        p_edges = recompute_edges(perturbed)
        phenotype = analyze(perturbed, p_edges)
        discovered = discover_phenotypes(phenotype, n_clusters=3, random_state=17)

        common = baseline[["track_id", "phenotype_cluster"]].merge(
            discovered[["track_id", "phenotype_cluster"]],
            on="track_id",
            suffixes=("_baseline", "_perturbed"),
        )
        ari = adjusted_rand_score(
            common["phenotype_cluster_baseline"],
            common["phenotype_cluster_perturbed"],
        ) if len(common) else 0.0

        expected_matches = float(
            (baseline_expected.iloc[: len(baseline)].to_numpy() == baseline["phenotype_cluster_name"].map(name_to_expected).to_numpy()).mean()
        )

        rows.append({
            "noise_um": noise_um,
            "drop_rate": drop_rate,
            "tracks_remaining": int(perturbed["track_id"].nunique()),
            "matched_tracks": int(len(common)),
            "cluster_ARI_vs_baseline": float(ari),
            "baseline_semantic_agreement": expected_matches,
        })

    frame = pd.DataFrame(rows)
    print(frame.to_string(index=False))
    output = {
        "benchmark": "controlled phenotype-discovery stability",
        "synthetic_groups": list(GROUPS),
        "rows": rows,
        "mean_ARI_nonzero_perturbations": float(frame.iloc[1:]["cluster_ARI_vs_baseline"].mean()),
    }
    (ROOT / "phenotype_stability_results.json").write_text(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
