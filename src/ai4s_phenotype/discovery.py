from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler, StandardScaler

FEATURES = [
    "duration",
    "observations",
    "displacement",
    "path_length",
    "mean_speed",
    "directional_persistence",
    "parent_count",
    "child_count",
    "descendant_count",
]


def discover_phenotypes(
    phenotypes: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 17,
    scaler: str = "standard",
    log_transform: bool = False,
) -> pd.DataFrame:
    missing = [c for c in FEATURES if c not in phenotypes.columns]
    if missing:
        raise ValueError(f"phenotypes missing columns: {missing}")
    if n_clusters < 2 or len(phenotypes) < n_clusters:
        raise ValueError("invalid n_clusters for phenotype table")

    out = phenotypes.copy()
    x = out[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if log_transform:
        positive = [c for c in FEATURES if (x[c] >= 0).all()]
        x[positive] = np.log1p(x[positive])
    if scaler == "standard":
        transformer = StandardScaler()
    elif scaler == "robust":
        transformer = RobustScaler()
    else:
        raise ValueError("scaler must be standard or robust")
    scaled = transformer.fit_transform(x)

    model = KMeans(n_clusters=n_clusters, n_init=30, random_state=random_state)
    out["phenotype_cluster"] = model.fit_predict(scaled).astype(int)

    centers = pd.DataFrame(model.cluster_centers_, columns=FEATURES)
    speed_rank = centers["mean_speed"].rank(method="first", ascending=False)
    persistence_rank = centers["directional_persistence"].rank(method="first")

    names = {}
    fastest = int(speed_rank.idxmin())
    least_persistent = int(persistence_rank.idxmin())
    for cluster in range(n_clusters):
        if cluster == fastest:
            names[cluster] = "high_motility"
        elif cluster == least_persistent:
            names[cluster] = "exploratory_motion"
        else:
            names[cluster] = "persistent_or_stable"

    out["phenotype_cluster_name"] = out["phenotype_cluster"].map(names)
    return out
