import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_external_biology.py"
spec = importlib.util.spec_from_file_location("evaluate_external_biology", MODULE_PATH)
evaluate_external_biology = importlib.util.module_from_spec(spec)
sys.modules["evaluate_external_biology"] = evaluate_external_biology
assert spec.loader is not None
spec.loader.exec_module(evaluate_external_biology)
FeatureSet = evaluate_external_biology.FeatureSet
evaluate = evaluate_external_biology.evaluate


def test_external_biology_grouped_split_detects_signal():
    rng = np.random.default_rng(7)
    rows = []
    for well_idx in range(12):
        treated = well_idx >= 6
        dose = 39.06 if treated else 0.0
        for t in range(3):
            for _cell in range(8):
                rows.append(
                    {
                        "Metadata_Well": f"W{well_idx:02d}",
                        "Metadata_dose": str(dose),
                        "Metadata_Time": float(t),
                        "phenotype_signal": (2.5 if treated else -2.5) + rng.normal(0, 0.35),
                        "phenotype_noise": rng.normal(),
                    }
                )
    summary = evaluate(
        pd.DataFrame(rows),
        well_col="Metadata_Well",
        dose_col="Metadata_dose",
        time_col="Metadata_Time",
        control_dose=0.0,
        positive_min_dose=19.53,
        seed=4,
        test_size=0.34,
        feature_sets=[FeatureSet("all_numeric")],
    )
    result = summary["results"][0]
    assert summary["status"] == "measured_external_biology_smoke_test"
    assert result["status"] == "ok"
    assert result["metrics"]["auroc"] >= 0.95
    assert result["shuffle_control_status"] == "ok"
    assert result["delta_auroc_vs_shuffle"] is not None
    assert result["delta_auroc_vs_shuffle"] > 0.20
    assert summary["split"]["train_wells"] > 0
    assert summary["split"]["test_wells"] > 0
