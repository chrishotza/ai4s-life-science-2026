from scripts.ab_experiment import BASELINE, compare


def test_baseline_is_not_rejected():
    assert compare(BASELINE)["decision"] == "KEEP-UNDER-REVIEW"


def test_material_regression_is_rejected():
    candidate = dict(BASELINE)
    candidate["f1"] -= 0.01
    candidate["coverage"] -= 0.05
    assert compare(candidate)["decision"] == "REJECT"


def test_multi_metric_gain_is_accepted():
    candidate = dict(BASELINE)
    candidate["f1"] += 0.004
    candidate["recall"] += 0.004
    candidate["coverage"] += 0.03
    candidate["persistence_mae"] -= 0.01
    result = compare(candidate)
    assert result["decision"] == "ACCEPT"
    assert result["improved_dimensions"] >= 2
