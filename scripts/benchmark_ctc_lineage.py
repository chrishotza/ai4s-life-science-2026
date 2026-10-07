from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai4s_io import ensure_ctc_dataset, load_ctc_tracking
from ai4s_phenotype import analyze

DATA_URL = "https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip"


def metadata_lineage(metadata: pd.DataFrame) -> set[tuple[int, int]]:
    return {
        (int(row.parent_id), int(row.track_id))
        for row in metadata.itertuples(index=False)
        if int(row.parent_id) > 0
    }


def expected_descendants(parent_map: dict[int, list[int]], root: int) -> set[int]:
    seen: set[int] = set()
    queue = deque(parent_map.get(root, []))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(parent_map.get(node, []))
    return seen


def evaluate(sequence_root: Path, sequence: str) -> dict[str, float | int | str]:
    nodes, edges, metadata = load_ctc_tracking(sequence_root / f"{sequence}_GT" / "TRA")
    phenotypes = analyze(nodes, edges)

    truth_relations = metadata_lineage(metadata)
    expected_children: dict[int, list[int]] = defaultdict(list)
    for parent, child in truth_relations:
        expected_children[parent].append(child)

    phenotype_map = phenotypes.set_index("track_id")
    expected_division_parents = {p for p in expected_children if len(expected_children[p]) >= 2}
    predicted_division_parents = {
        int(track_id)
        for track_id, row in phenotype_map.iterrows()
        if bool(row["division_event"])
    }

    division_tp = len(expected_division_parents & predicted_division_parents)
    division_fp = len(predicted_division_parents - expected_division_parents)
    division_fn = len(expected_division_parents - predicted_division_parents)

    child_count_exact = 0
    descendant_count_exact = 0
    checked_tracks = 0
    for track_id, row in phenotype_map.iterrows():
        tid = int(track_id)
        expected_children_count = len(expected_children.get(tid, []))
        expected_desc = len(expected_descendants(expected_children, tid))
        if int(row["child_count"]) == expected_children_count:
            child_count_exact += 1
        if int(row["descendant_count"]) == expected_desc:
            descendant_count_exact += 1
        checked_tracks += 1

    precision = division_tp / max(1, division_tp + division_fp)
    recall = division_tp / max(1, division_tp + division_fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)

    return {
        "dataset": "DIC-C2DH-HeLa",
        "sequence": sequence,
        "tracks": int(len(phenotype_map)),
        "annotated_lineage_edges": int(len(truth_relations)),
        "division_parents": int(len(expected_division_parents)),
        "division_parents_recovered": int(division_tp),
        "division_precision": float(precision),
        "division_recall": float(recall),
        "division_f1": float(f1),
        "child_count_exact_rate": float(child_count_exact / max(1, checked_tracks)),
        "descendant_count_exact_rate": float(descendant_count_exact / max(1, checked_tracks)),
    }


def main() -> None:
    dataset_root = ensure_ctc_dataset(ROOT / ".benchmark_cache")

    results = [evaluate(dataset_root, sequence) for sequence in ("01", "02")]
    frame = pd.DataFrame(results)
    aggregate = {
        column: float(frame[column].mean())
        for column in (
            "division_precision",
            "division_recall",
            "division_f1",
            "child_count_exact_rate",
            "descendant_count_exact_rate",
        )
    }

    output = {
        "benchmark": {
            "dataset": "DIC-C2DH-HeLa",
            "sequences": ["01", "02"],
            "input": "CTC reference track annotations",
            "purpose": "validate lineage/division feature extraction from annotated lineage edges",
        },
        "results": results,
        "aggregate": aggregate,
    }
    (ROOT / "ctc_lineage_results.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
