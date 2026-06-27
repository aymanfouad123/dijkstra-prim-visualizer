"""
benchmark_runner.py

Comprehensive benchmark runner for the Dijkstra + Prim visualizer project.

Place this file in the root of the repo, beside:
    dijkstra.py
    prim.py

Then run:
    python benchmark_runner.py

Optional examples:
    python benchmark_runner.py --sizes 25,50,100,200 --runs 20
    python benchmark_runner.py --sizes 25,50,100,200,400 --runs 10 --dense-ratio 0.50
    python benchmark_runner.py --no-charts

Outputs:
    benchmark_results_detailed.csv
    benchmark_summary.md
    benchmark_charts/*.png
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from dijkstra import Graph as DijkstraGraph
from dijkstra import dijkstra_binary_heap, dijkstra_linked_list
from prim import Graph as PrimGraph
from prim import prim_binary_heap, prim_linked_list


Edge = Tuple[str, str, int]


def max_undirected_edges(vertex_count: int) -> int:
    return vertex_count * (vertex_count - 1) // 2


def generate_connected_undirected_edges(
    vertex_count: int,
    edge_count: int,
    rng: random.Random,
    min_weight: int = 1,
    max_weight: int = 100,
) -> List[Edge]:
    """
    Generate a connected undirected simple weighted graph.

    First a random spanning tree is created so the graph is connected.
    Then random extra edges are added until the requested edge count is reached.
    """

    if vertex_count < 1:
        raise ValueError("vertex_count must be at least 1.")

    max_edges = max_undirected_edges(vertex_count)

    if edge_count > max_edges:
        raise ValueError(
            f"Cannot create {edge_count} edges with {vertex_count} vertices. "
            f"Maximum undirected simple edges is {max_edges}."
        )

    if vertex_count > 1 and edge_count < vertex_count - 1:
        raise ValueError(
            f"A connected graph with {vertex_count} vertices requires at least "
            f"{vertex_count - 1} edges."
        )

    vertices = [f"V{i}" for i in range(vertex_count)]
    edges: List[Edge] = []
    used_pairs = set()

    def add_edge(u: str, v: str) -> None:
        if u == v:
            return
        pair = tuple(sorted((u, v)))
        if pair in used_pairs:
            return
        used_pairs.add(pair)
        weight = rng.randint(min_weight, max_weight)
        edges.append((u, v, weight))

    for i in range(1, vertex_count):
        u = vertices[i]
        v = vertices[rng.randrange(0, i)]
        add_edge(u, v)

    while len(edges) < edge_count:
        u, v = rng.sample(vertices, 2)
        add_edge(u, v)

    return edges


def build_dijkstra_graph(edges: Sequence[Edge], vertex_count: int) -> DijkstraGraph:
    graph = DijkstraGraph(directed=False)
    for i in range(vertex_count):
        graph.add_vertex(f"V{i}")
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def build_prim_graph(edges: Sequence[Edge], vertex_count: int) -> PrimGraph:
    graph = PrimGraph(directed=False)
    for i in range(vertex_count):
        graph.add_vertex(f"V{i}")
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def summarize(values: Sequence[float]) -> Dict[str, float]:
    return {
        "avg_runtime_ms": statistics.mean(values),
        "median_runtime_ms": statistics.median(values),
        "min_runtime_ms": min(values),
        "max_runtime_ms": max(values),
    }


def run_one_configuration(
    graph_type: str,
    vertex_count: int,
    edge_count: int,
    runs: int,
    seed: int,
) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    edges = generate_connected_undirected_edges(vertex_count, edge_count, rng)

    source_or_start = "V0"

    d_graph = build_dijkstra_graph(edges, vertex_count)
    p_graph = build_prim_graph(edges, vertex_count)

    timings: Dict[Tuple[str, str], List[float]] = {
        ("Dijkstra", "Binary Heap"): [],
        ("Dijkstra", "Linked List"): [],
        ("Prim", "Binary Heap"): [],
        ("Prim", "Linked List"): [],
    }

    # Warm-up runs
    dijkstra_binary_heap(d_graph, source_or_start, record_steps=False)
    dijkstra_linked_list(d_graph, source_or_start, record_steps=False)
    prim_binary_heap(p_graph, source_or_start, record_steps=False)
    prim_linked_list(p_graph, source_or_start, record_steps=False)

    for _ in range(runs):
        d_heap = dijkstra_binary_heap(d_graph, source_or_start, record_steps=False)
        d_list = dijkstra_linked_list(d_graph, source_or_start, record_steps=False)

        if d_heap["distances"] != d_list["distances"]:
            raise AssertionError(
                f"Dijkstra heap/list mismatch for {graph_type}, V={vertex_count}, E={edge_count}"
            )

        timings[("Dijkstra", "Binary Heap")].append(d_heap["runtime_ms"])
        timings[("Dijkstra", "Linked List")].append(d_list["runtime_ms"])

        p_heap = prim_binary_heap(p_graph, source_or_start, record_steps=False)
        p_list = prim_linked_list(p_graph, source_or_start, record_steps=False)

        if p_heap["total_weight"] != p_list["total_weight"]:
            raise AssertionError(
                f"Prim heap/list MST mismatch for {graph_type}, V={vertex_count}, E={edge_count}"
            )

        expected_mst_edges = vertex_count - 1
        if len(p_heap["mst_edges"]) != expected_mst_edges:
            raise AssertionError("Prim heap result did not produce V-1 MST edges.")
        if len(p_list["mst_edges"]) != expected_mst_edges:
            raise AssertionError("Prim linked-list result did not produce V-1 MST edges.")

        timings[("Prim", "Binary Heap")].append(p_heap["runtime_ms"])
        timings[("Prim", "Linked List")].append(p_list["runtime_ms"])

    rows: List[Dict[str, object]] = []

    for (algorithm, fringe), values in timings.items():
        stats = summarize(values)
        rows.append(
            {
                "graph_type": graph_type,
                "vertices": vertex_count,
                "edges": edge_count,
                "algorithm": algorithm,
                "fringe": fringe,
                "runs": runs,
                "seed": seed,
                **stats,
            }
        )

    return rows


def run_benchmarks(
    sizes: Sequence[int],
    runs: int,
    sparse_multiplier: int,
    dense_ratio: float,
    seed: int,
) -> List[Dict[str, object]]:
    all_rows: List[Dict[str, object]] = []

    for vertex_count in sizes:
        max_edges = max_undirected_edges(vertex_count)

        sparse_edges = min(max_edges, max(vertex_count - 1, sparse_multiplier * vertex_count))
        dense_edges = min(max_edges, max(vertex_count - 1, int(max_edges * dense_ratio)))
        dense_edges = max(dense_edges, sparse_edges)

        configs = [
            ("Sparse", sparse_edges),
            ("Dense", dense_edges),
        ]

        for graph_type, edge_count in configs:
            config_seed = seed + vertex_count * 1000 + edge_count
            print(
                f"Running {graph_type:6s} V={vertex_count:4d}, E={edge_count:6d}, "
                f"runs={runs}"
            )
            rows = run_one_configuration(
                graph_type=graph_type,
                vertex_count=vertex_count,
                edge_count=edge_count,
                runs=runs,
                seed=config_seed,
            )
            all_rows.extend(rows)

    return all_rows


def write_csv(rows: Sequence[Dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "graph_type",
        "vertices",
        "edges",
        "algorithm",
        "fringe",
        "runs",
        "seed",
        "avg_runtime_ms",
        "median_runtime_ms",
        "min_runtime_ms",
        "max_runtime_ms",
    ]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_summary(rows: Sequence[Dict[str, object]]) -> None:
    print("\nBenchmark Summary")
    print("=" * 100)
    print(
        f"{'Graph':<8} {'V':>5} {'E':>7} {'Algorithm':<10} {'Fringe':<12} "
        f"{'Avg ms':>12} {'Median ms':>12}"
    )
    print("-" * 100)

    for row in rows:
        print(
            f"{row['graph_type']:<8} "
            f"{int(row['vertices']):>5} "
            f"{int(row['edges']):>7} "
            f"{str(row['algorithm']):<10} "
            f"{str(row['fringe']):<12} "
            f"{float(row['avg_runtime_ms']):>12.6f} "
            f"{float(row['median_runtime_ms']):>12.6f}"
        )


def write_markdown_summary(rows: Sequence[Dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Benchmark Summary",
        "",
        "Graphs were generated programmatically. Sparse graphs used approximately `3V` edges. Dense graphs used approximately half of all possible undirected edges.",
        "",
        "| Graph Type | V | E | Algorithm | Fringe | Runs | Avg Runtime (ms) | Median Runtime (ms) |",
        "|---|---:|---:|---|---|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            "| "
            f"{row['graph_type']} | "
            f"{row['vertices']} | "
            f"{row['edges']} | "
            f"{row['algorithm']} | "
            f"{row['fringe']} | "
            f"{row['runs']} | "
            f"{float(row['avg_runtime_ms']):.6f} | "
            f"{float(row['median_runtime_ms']):.6f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The same generated graph was used for binary heap and linked-list comparisons.",
            "- `record_steps=False` was used during benchmarks so visualization recording did not affect runtime.",
            "- The benchmark checks that heap and linked-list implementations produce identical outputs before recording timing results.",
            "- Small graphs may show only minor differences because fixed overhead dominates. Larger graphs better show the effect of the fringe data structure.",
        ]
    )

    output_path.write_text("\n".join(lines))


def make_charts(rows: Sequence[Dict[str, object]], output_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nmatplotlib is not installed, so charts were not generated.")
        print("Install it with: pip install matplotlib")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    algorithms = ["Dijkstra", "Prim"]
    graph_types = ["Sparse", "Dense"]

    for algorithm in algorithms:
        for graph_type in graph_types:
            filtered = [
                row for row in rows
                if row["algorithm"] == algorithm and row["graph_type"] == graph_type
            ]

            if not filtered:
                continue

            vertices = sorted({int(row["vertices"]) for row in filtered})
            fringe_names = ["Binary Heap", "Linked List"]

            plt.figure()

            for fringe in fringe_names:
                y_values = []
                for v in vertices:
                    matches = [
                        row for row in filtered
                        if int(row["vertices"]) == v and row["fringe"] == fringe
                    ]
                    if matches:
                        y_values.append(float(matches[0]["avg_runtime_ms"]))
                    else:
                        y_values.append(math.nan)

                plt.plot(vertices, y_values, marker="o", label=fringe)

            plt.xlabel("Number of vertices")
            plt.ylabel("Average runtime (ms)")
            plt.title(f"{algorithm} Runtime on {graph_type} Graphs")
            plt.legend()
            plt.grid(True, alpha=0.3)

            filename = f"{algorithm.lower()}_{graph_type.lower()}_runtime.png"
            plt.savefig(output_dir / filename, dpi=200, bbox_inches="tight")
            plt.close()

    print(f"Charts written to: {output_dir}")


def parse_sizes(value: str) -> List[int]:
    sizes = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not sizes:
        raise argparse.ArgumentTypeError("At least one size is required.")
    return sizes


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Dijkstra and Prim benchmarks.")
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=[25, 50, 100, 200],
        help="Comma-separated vertex counts. Default: 25,50,100,200",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of timing runs per configuration. Default: 20",
    )
    parser.add_argument(
        "--sparse-multiplier",
        type=int,
        default=3,
        help="Sparse graph edge count is approximately sparse_multiplier * V. Default: 3",
    )
    parser.add_argument(
        "--dense-ratio",
        type=float,
        default=0.50,
        help="Dense graph edge count as fraction of max undirected edges. Default: 0.50",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Base random seed for reproducible graphs. Default: 12345",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("benchmark_results_detailed.csv"),
        help="CSV output path.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("benchmark_summary.md"),
        help="Markdown summary output path.",
    )
    parser.add_argument(
        "--chart-dir",
        type=Path,
        default=Path("benchmark_charts"),
        help="Directory for benchmark chart PNG files.",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip chart generation.",
    )

    args = parser.parse_args()

    if args.runs < 1:
        raise ValueError("--runs must be at least 1.")

    if not (0 < args.dense_ratio <= 1):
        raise ValueError("--dense-ratio must be between 0 and 1.")

    rows = run_benchmarks(
        sizes=args.sizes,
        runs=args.runs,
        sparse_multiplier=args.sparse_multiplier,
        dense_ratio=args.dense_ratio,
        seed=args.seed,
    )

    write_csv(rows, args.csv)
    write_markdown_summary(rows, args.summary)
    print_summary(rows)

    print(f"\nCSV written to: {args.csv}")
    print(f"Markdown summary written to: {args.summary}")

    if not args.no_charts:
        make_charts(rows, args.chart_dir)


if __name__ == "__main__":
    main()
