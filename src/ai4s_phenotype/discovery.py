from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler, StandardScaler

FEATURE_SCHEMA_VERSION = "trajectory-lineage-v1"
MOTION_ONLY_SCHEMA_VERSION = "motility-only-v1"

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

# The optional motility readout intentionally excludes track age and path totals.
# Requiring >=3 observations for FIT prevents singleton frames from defining
# a visually compelling but scientifically meaningless "behavioral" cluster.
MOTION_ONLY_FEATURES = ("mean_speed", "directional_persistence")
FEATURE_SETS = {
    "trajectory_lineage": tuple(FEATURES),
    "motion_only": MOTION_ONLY_FEATURES,
}


def _feature_matrix(
    phenotypes: pd.DataFrame,
    *,
    features: tuple[str, ...] | list[str] = FEATURES,
    log_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    missing = [column for column in features if column not in phenotypes.columns]
    if missing:
        raise ValueError(f"phenotypes missing columns: {missing}")

    x = phenotypes[list(features)].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
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


def _cluster_names(model: KMeans, features: tuple[str, ...]) -> dict[int, str]:
    centers = pd.DataFrame(model.cluster_centers_, columns=features)
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
    feature_set: str = "trajectory_lineage"

    @classmethod
    def fit(
        cls,
        phenotypes: pd.DataFrame,
        *,
        n_clusters: int = 3,
        random_state: int = 17,
        scaler: str = "standard",
        log_transform: bool = False,
        feature_set: str = "trajectory_lineage",
    ) -> "PhenotypeDiscoveryModel":
        if n_clusters < 2 or len(phenotypes) < n_clusters:
            raise ValueError("invalid n_clusters for phenotype table")
        if feature_set not in FEATURE_SETS:
            raise ValueError("feature_set must be trajectory_lineage or motion_only")
        if feature_set == "motion_only":
            if "observations" not in phenotypes:
                raise ValueError("motion_only requires observations for its evidence gate")
            n_obs = phenotypes["observations"].to_numpy(dtype=float)
            if not np.isfinite(n_obs).all() or (n_obs < 3).any():
                raise ValueError("motion_only requires >=3 observations per fitting track")
        features = FEATURE_SETS[feature_set]
        raw_x = _feature_matrix(phenotypes, features=features)
        log_columns = (
            tuple(column for column in features if (raw_x[column] >= 0).all())
            if log_transform
            else ()
        )
        x = _feature_matrix(phenotypes, features=features, log_columns=log_columns)
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
            feature_names=features,
            log_transform=log_transform,
            log_columns=log_columns,
            cluster_names=_cluster_names(model, features),
            assignment_distance_scale=assignment_distance_scale,
            feature_schema_version=(
                MOTION_ONLY_SCHEMA_VERSION if feature_set == "motion_only"
                else FEATURE_SCHEMA_VERSION
            ),
            feature_set=feature_set,
        )

    def transform(self, phenotypes: pd.DataFrame) -> pd.DataFrame:
        x = _feature_matrix(
            phenotypes, features=self.feature_names, log_columns=self.log_columns,
        )
        if tuple(x.columns) != self.feature_names:
            raise ValueError("phenotype feature schema does not match fitted model")
        expected = (
            MOTION_ONLY_SCHEMA_VERSION if self.feature_set == "motion_only"
            else FEATURE_SCHEMA_VERSION
        )
        if self.feature_schema_version != expected:
            raise ValueError(
                f"unsupported phenotype feature schema: {self.feature_schema_version}"
            )
        if self.feature_names != FEATURE_SETS.get(self.feature_set):
            raise ValueError("fitted phenotype feature schema mismatch")

        out = phenotypes.copy()
        scaled = self.scaler.transform(x)
        distances = self.model.transform(scaled)
        labels = np.argmin(distances, axis=1).astype(int)
        ordered = np.sort(distances, axis=1)
        out["phenotype_cluster"] = labels
        if self.feature_set == "motion_only":
            out["phenotype_feature_set"] = "motion_only"
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
    feature_set: str = "trajectory_lineage",
) -> pd.DataFrame:
    model = PhenotypeDiscoveryModel.fit(
        phenotypes,
        n_clusters=n_clusters,
        random_state=random_state,
        scaler=scaler,
        log_transform=log_transform,
        feature_set=feature_set,
    )
    return model.transform(phenotypes)
