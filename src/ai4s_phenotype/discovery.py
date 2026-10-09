from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler, StandardScaler

FEATURE_SCHEMA_VERSION = "trajectory-lineage-v1"

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


def _feature_matrix(
    phenotypes: pd.DataFrame,
    *,
    log_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    missing = [column for column in FEATURES if column not in phenotypes.columns]
    if missing:
        raise ValueError(f"phenotypes missing columns: {missing}")

    x = phenotypes[FEATURES].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    for column in log_columns:
        if (x[column] < 0).any():
            raise ValueError(f"feature {column} contains negative values but the fitted discovery model requires log1p")
        x[column] = np.log1p(x[column])
    return x


def _make_scaler(name: str):
    if name == "standard":
        return StandardScaler()
    if name == "robust":
        return RobustScaler()
    raise ValueError("scaler must be standard or robust")


def _cluster_names(model: KMeans) -> dict[int, str]:
    centers = pd.DataFrame(model.cluster_centers_, columns=FEATURES)
    speed_rank = centers["mean_speed"].rank(method="first", ascending=False)
    persistence_rank = centers["directional_persistence"].rank(method="first")

    fastest = int(speed_rank.idxmin())
    least_persistent = int(persistence_rank.idxmin())
    names: dict[int, str] = {}
    for cluster in range(model.n_clusters):
        if cluster == fastest:
            names[cluster] = "high_motility"
        elif cluster == least_persistent:
            names[cluster] = "exploratory_motion"
        else:
            names[cluster] = "persistent_or_stable"
    return names


@dataclass
class PhenotypeDiscoveryModel:
    scaler: StandardScaler | RobustScaler
    model: KMeans
    feature_names: tuple[str, ...]
    log_transform: bool
    log_columns: tuple[str, ...]
    cluster_names: dict[int, str]
    assignment_distance_scale: float
    feature_schema_version: str = FEATURE_SCHEMA_VERSION

    @classmethod
    def fit(
        cls,
        phenotypes: pd.DataFrame,
        *,
        n_clusters: int = 3,
        random_state: int = 17,
        scaler: str = "standard",
        log_transform: bool = False,
    ) -> "PhenotypeDiscoveryModel":
        if n_clusters < 2 or len(phenotypes) < n_clusters:
            raise ValueError("invalid n_clusters for phenotype table")

        raw_x = _feature_matrix(phenotypes)
        log_columns = (
            tuple(column for column in FEATURES if (raw_x[column] >= 0).all())
            if log_transform
            else ()
        )
        x = _feature_matrix(phenotypes, log_columns=log_columns)
        transformer = _make_scaler(scaler)
        scaled = transformer.fit_transform(x)
        model = KMeans(
            n_clusters=n_clusters,
            n_init=30,
            random_state=random_state,
        )
        model.fit(scaled)
        train_distances = model.transform(scaled)
        assigned_distances = train_distances[
            np.arange(len(train_distances)),
            np.argmin(train_distances, axis=1),
        ]
        assignment_distance_scale = float(np.median(assigned_distances))
        if not np.isfinite(assignment_distance_scale) or assignment_distance_scale <= 1e-9:
            assignment_distance_scale = 1.0

        return cls(
            scaler=transformer,
            model=model,
            feature_names=tuple(FEATURES),
            log_transform=log_transform,
            log_columns=log_columns,
            cluster_names=_cluster_names(model),
            assignment_distance_scale=assignment_distance_scale,
        )

    def transform(self, phenotypes: pd.DataFrame) -> pd.DataFrame:
        x = _feature_matrix(phenotypes, log_columns=self.log_columns)
        if tuple(x.columns) != self.feature_names:
            raise ValueError("phenotype feature schema does not match fitted model")
        if self.feature_schema_version != FEATURE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported phenotype feature schema: {self.feature_schema_version}"
            )

        out = phenotypes.copy()
        scaled = self.scaler.transform(x)
        distances = self.model.transform(scaled)
        labels = np.argmin(distances, axis=1).astype(int)
        ordered = np.sort(distances, axis=1)
        out["phenotype_cluster"] = labels
        out["phenotype_cluster_name"] = out["phenotype_cluster"].map(self.cluster_names)
        # A one/two-frame track cannot support an interpretable motion pattern.
        # Keep its raw K-Means cluster ID for reproducible stability audits,
        # but prevent the descriptive cluster name being mistaken for biology.
        if "observations" in out.columns:
            sufficient = out["observations"].astype(float) >= 3
            out["phenotype_temporal_evidence_sufficient"] = sufficient
            out.loc[~sufficient, "phenotype_cluster_name"] = (
                "insufficient_temporal_evidence"
            )
        out["phenotype_cluster_distance"] = distances[np.arange(len(out)), labels]
        out["phenotype_cluster_margin"] = (
            ordered[:, 1] - ordered[:, 0]
            if distances.shape[1] > 1
            else np.zeros(len(out))
        )
        distance_quality = np.exp(
            -distances[np.arange(len(out)), labels]
            / max(self.assignment_distance_scale, 1e-9)
        )
        if distances.shape[1] > 1:
            separation_quality = (
                out["phenotype_cluster_margin"].to_numpy(float)
                / (
                    out["phenotype_cluster_margin"].to_numpy(float)
                    + distances[np.arange(len(out)), labels]
                    + 1e-9
                )
            )
        else:
            separation_quality = np.ones(len(out), dtype=float)
        out["phenotype_assignment_quality"] = np.clip(
            np.sqrt(distance_quality * np.clip(separation_quality, 0.0, 1.0)),
            0.0,
            1.0,
        )
        if "track_integrity_score" in out.columns:
            out["phenotype_reliability_score"] = np.clip(
                np.sqrt(
                    np.clip(out["track_integrity_score"].to_numpy(float), 0.0, 1.0)
                    * out["phenotype_assignment_quality"].to_numpy(float)
                ),
                0.0,
                1.0,
            )
        return out


def fit_phenotype_model(
    phenotypes: pd.DataFrame,
    **kwargs,
) -> PhenotypeDiscoveryModel:
    return PhenotypeDiscoveryModel.fit(phenotypes, **kwargs)


def discover_phenotypes(
    phenotypes: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 17,
    scaler: str = "standard",
    log_transform: bool = False,
) -> pd.DataFrame:
    model = PhenotypeDiscoveryModel.fit(
        phenotypes,
        n_clusters=n_clusters,
        random_state=random_state,
        scaler=scaler,
        log_transform=log_transform,
    )
    return model.transform(phenotypes)
