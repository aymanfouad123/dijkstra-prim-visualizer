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

A minimal Tkinter user interface lives in the `visualizer/` folder. It reuses
the algorithm functions from `dijkstra.py` and `prim.py` and keeps the flow
linear so each step unlocks only after the previous one has enough state.

Run it from the project root:

```bash
python -m visualizer
```

### What the UI does

1. **Choose an algorithm** — select Dijkstra or Prim.
2. **Create graph input** — load a matching preset or build a graph manually by
   adding vertices and weighted edges. Dijkstra supports a directed-edge toggle.
3. **Configure and run** — select Binary Heap or Linked List, choose the
   source/start vertex, and run. Prim also has an `Allow disconnected Prim`
   toggle that passes `allow_partial=True` to the backend.
4. **Step through iterations** — seek to beginning, back, next, and seek to end.
   The canvas highlights visited vertices, fringe vertices, current vertex,
   selected edge, and the current shortest-path tree or MST.
5. **Read the state** — panels show the current step details and final result.

### Visualizer file layout

```
visualizer/
  __init__.py          # package marker
  __main__.py          # enables: python -m visualizer
  algorithm_bridge.py  # connects the UI to dijkstra.py and prim.py
  graph_view.py        # Tk canvas: draws nodes/edges and highlights state
  app.py               # main staged application window, controls, playback
```

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
