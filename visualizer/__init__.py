"""
Tkinter visualizer package for the Graph Algorithms Final Project.

This package provides an interactive UI on top of the algorithm backend in
``graph_algorithms_project.py``. It lets the user incrementally build a graph,
choose an algorithm (Dijkstra or Prim) and a fringe (binary heap or linked
list), run it, and step through every major iteration. It can also export each
iteration as a PNG frame (and a combined GIF) for the report animations.

Run it with:

    python -m visualizer
"""

from . import algorithm_bridge  # noqa: F401

__all__ = ["algorithm_bridge"]
