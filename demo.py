from pathlib import Path

import pandas as pd

from ai4s_phenotype import analyze


def main() -> None:
    nodes_path = Path("examples/nodes.csv")
    edges_path = Path("examples/edges.csv")

    nodes = pd.read_csv(nodes_path)
    edges = pd.read_csv(edges_path)
    result = analyze(nodes, edges)

    out = Path("phenotype_report.csv")
    result.to_csv(out, index=False)
    print(result.to_string(index=False))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
