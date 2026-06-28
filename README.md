# Interactive Graph Algorithm Visualizer

Compare **Dijkstra's shortest-path** and **Prim's minimum-spanning-tree** algorithms on weighted graphs represented with **adjacency lists**. Each algorithm is implemented with two fringe data structures—a **binary heap** and a **linked list**—so you can see how extract-min cost affects runtime on sparse and dense graphs.

Includes a desktop visualizer for step-by-step playback, built-in correctness tests, and a benchmark suite with CSV/Markdown summaries and charts.

## Features

- Four algorithm variants: Dijkstra/Prim × binary heap/linked list fringe
- Adjacency-list graph with validation (non-negative weights for Dijkstra, connected undirected graphs for Prim)
- Step recording for every major iteration (extract-min, relax edge, add MST edge, etc.)
- GUI to build graphs, run algorithms, step through results, and export GIF animations
- Built-in sample graphs with known correct answers
- Benchmark runner for sparse and dense random graphs
- Embedded correctness tests in `dijkstra.py` and `prim.py`

## Requirements

- **Python 3.10+**
- See [`requirements.txt`](requirements.txt) for third-party packages

| Package    | Used for                            |
| ---------- | ----------------------------------- |
| PySide6    | Desktop visualizer UI               |
| Pillow     | PNG frame rendering and GIF export  |
| matplotlib | Benchmark runtime charts (optional) |

## Installation

```bash
git clone <repository-url>
cd 3ac3

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Quick Start

### Launch the visualizer

```bash
python3 -m visualizer
```

### Run CLI demos and tests

```bash
python3 dijkstra.py    # sample graph, both fringe types, built-in tests
python3 prim.py        # sample graph, both fringe types, built-in tests
```

### Run benchmarks

```bash
python3 benchmark_runner.py
```

This writes:

- `benchmark_results_detailed.csv` — per-run timings
- `benchmark_summary.md` — averaged results table
- `benchmark_charts/*.png` — runtime vs. graph size (requires matplotlib)

Useful options:

```bash
python3 benchmark_runner.py --sizes 25,50,100,200 --runs 20
python3 benchmark_runner.py --no-charts
```

## Using the Visualizer

The UI is organized as a short guided workflow on the left panel.

1. **Choose algorithm** — Dijkstra (shortest paths) or Prim (MST).
2. **Choose graph source** — load a preset or build a graph manually.
3. **Configure the graph** — add vertices and weighted edges, or load a built-in sample.
4. **Set start vertex** — source for Dijkstra, root for Prim.
5. **Run** — pick a fringe type (Binary Heap or Linked List) and execute.
6. **Step through results** — use Prev/Next to walk major algorithm steps; the graph, fringe, and tree update on each step.
7. **Export** — save the full step sequence as an animated GIF.

### Built-in presets

| Preset                   | Algorithm | Notes                                    |
| ------------------------ | --------- | ---------------------------------------- |
| Dijkstra sample          | Dijkstra  | 6-vertex undirected graph, start at `A`  |
| Prim sample              | Prim      | Same graph, MST total weight **13**      |
| Disconnected Prim sample | Prim      | Demonstrates disconnected-graph handling |

### Manual graph entry

- **Dijkstra**: directed or undirected; edge weights must be **non-negative**.
- **Prim**: graph must be **undirected** and **connected** (unless partial/component mode is enabled).

## Project Structure

```text
3ac3/
├── dijkstra.py              # Dijkstra + binary heap / linked list fringe
├── prim.py                  # Prim + binary heap / linked list fringe
├── benchmark_runner.py      # Sparse/dense performance experiments
├── visualizer/
│   ├── app.py               # PySide6 main window
│   ├── graph_view.py        # Interactive graph canvas
│   ├── frame_renderer.py    # Pillow-based GIF export
│   └── algorithm_bridge.py  # UI algorithm adapter and presets
├── animations/              # Example exported GIFs
├── sample_steps/            # Example step JSON snapshots
├── benchmark_charts/        # Generated runtime charts
├── benchmark_results_detailed.csv
└── benchmark_summary.md
```

## Complexity

| Algorithm | Fringe      | Time (adjacency list) | Space    |
| --------- | ----------- | --------------------- | -------- |
| Dijkstra  | Binary heap | O((V + E) log V)      | O(V + E) |
| Dijkstra  | Linked list | O(V² + E)             | O(V + E) |
| Prim      | Binary heap | O(E log V)            | O(V + E) |
| Prim      | Linked list | O(V² + E)             | O(V + E) |

The heap fringe speeds up **extract-min**; the linked-list fringe scans the entire fringe each iteration. On larger sparse graphs, the heap versions typically pull ahead; on small graphs, fixed overhead can dominate.

## Algorithm API

Both modules expose a `Graph` class and two runner functions. Each returns a result dict with distances or MST edges, runtime, and a `steps` list when step recording is enabled.

```python
from dijkstra import Graph, dijkstra_binary_heap, dijkstra_linked_list

g = Graph(directed=False)
g.add_edge("A", "B", 4)
g.add_edge("A", "C", 2)

result = dijkstra_binary_heap(g, "A")
print(result["distances"])
print(result["runtime_ms"])
```

```python
from prim import Graph, prim_binary_heap, prim_linked_list

g = Graph()
# ... add edges ...

result = prim_linked_list(g, "A")
print(result["mst_edges"])
print(result["total_weight"])
```

## License

Academic project.
