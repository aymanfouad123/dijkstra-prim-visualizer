# Graph Algorithms Final Project - Option 1

This project implements and compares:

1. Dijkstra's shortest-path algorithm using a binary heap fringe
2. Dijkstra's shortest-path algorithm using a linked-list fringe
3. Prim's minimum-spanning-tree algorithm using a binary heap fringe
4. Prim's minimum-spanning-tree algorithm using a linked-list fringe

The graph is represented using adjacency lists, matching the project requirement.

## Requirements

Python 3.9+ is recommended. The program uses only Python standard library modules.
No external packages are required.

## Main File

```bash
python graph_algorithms_project.py --mode demo
python graph_algorithms_project.py --mode test
python graph_algorithms_project.py --mode benchmark
python graph_algorithms_project.py --mode export-steps
python graph_algorithms_project.py --mode all
```

## Modes

### Demo

Runs all four algorithms on a small built-in six-vertex graph with known expected results.

```bash
python graph_algorithms_project.py --mode demo
```

### Test

Runs correctness tests and edge-case tests:

- Dijkstra heap/list shortest distances on known graph
- Prim heap/list MST total weight on known graph
- Single-vertex graph
- Disconnected graph rejected by Prim
- Negative edge rejected
- Equal-weight graph tie behavior
- Random graph agreement between heap/list versions

```bash
python graph_algorithms_project.py --mode test
```

### Benchmark

Generates sparse and dense connected graphs and compares runtime for all four algorithm versions.

```bash
python graph_algorithms_project.py --mode benchmark --sizes 10,25,50,100 --runs 3 --csv benchmark_results.csv
```

The CSV can be used for report tables and charts.

### Export Steps

Exports JSON files containing major algorithm iteration states. These can be used by a UI to create screenshots, PNG frames, or animations.

```bash
python graph_algorithms_project.py --mode export-steps --steps-dir sample_steps
```

## Interactive Visualizer (Tkinter UI)

A Tkinter user interface lives in the `visualizer/` folder. It reuses the exact
same algorithm functions from `graph_algorithms_project.py` (no logic is
duplicated) and satisfies the assignment's UI and animation requirements.

Run it from the project root:

```bash
python -m visualizer
```

### What the UI does

1. **Build a graph** — add vertices, add weighted edges (with a directed toggle
   for Dijkstra), load the built-in sample graph, re-layout, or clear. Edges can
   be added incrementally and existing edge weights are updated in place. Nodes
   can be dragged to reposition them.
2. **Configure the algorithm** — choose Dijkstra or Prim, choose the Binary Heap
   or Linked List fringe, and pick the source/start vertex.
3. **Run** — validation errors (negative weights, missing source, Prim on a
   disconnected/directed graph) are reported in a dialog.
4. **Step through iterations** — first / previous / next / last and an auto Play
   button walk through every recorded major step. The canvas highlights visited
   vertices (green), the current vertex (red outline), fringe vertices (yellow),
   the current tree/MST edges (blue), and the edge being relaxed/considered (red).
5. **Read the state** — panels show the fringe contents, visited set, per-step
   distances (Dijkstra) or running MST weight (Prim), the final result, and the
   measured runtime.
6. **Export animation frames** — save the current frame as a PNG, or export every
   step as numbered PNG frames plus an animated GIF for the report.

### Visualizer file layout

```
visualizer/
  __init__.py          # package marker
  __main__.py          # enables: python -m visualizer
  algorithm_bridge.py  # connects the UI to graph_algorithms_project
  graph_view.py        # Tk canvas: draws nodes/edges and highlights state
  frame_renderer.py    # Pillow renderer for PNG frames + GIF export
  app.py               # main application window, controls, playback, export
```

The PNG/GIF export uses Pillow (`pip install pillow`). The core algorithms and
all CLI modes still require only the Python standard library.

## Algorithm Restrictions

- Dijkstra requires non-negative edge weights.
- Prim requires an undirected connected graph.
- Disconnected graphs are rejected for Prim because there is no single minimum spanning tree.

## Complexity Summary

| Algorithm | Fringe | Time Complexity | Space Complexity |
|---|---|---:|---:|
| Dijkstra | Binary Heap | O((V + E) log V) | O(V + E) |
| Dijkstra | Linked List | O(V^2 + E) | O(V + E) |
| Prim | Binary Heap | O(E log V) | O(V + E) |
| Prim | Linked List | O(V^2 + E) | O(V + E) |

## Report Evidence Produced

- `sample_demo_output.txt`: sample graph output and expected results
- `benchmark_results.csv`: runtime data for charts/tables
- `sample_steps/*.json`: major iteration traces for animation/screenshot support

