"""
Canvas widget that draws the graph and highlights the current algorithm state.

The view is intentionally "dumb": it stores vertex positions and a copy of the
graph model, and renders whatever highlight state (visited set, current vertex,
selected edge, tree edges, distances, fringe) the app hands it for the step
being shown. The same geometry/styling constants are reused by
``frame_renderer.py`` so exported PNG frames match the live view.
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Any, Dict, List, Optional, Set, Tuple

Edge = Tuple[str, str, float]

# Shared geometry/styling so live canvas and exported PNG frames look identical.
NODE_RADIUS = 22
DEFAULT_W = 700
DEFAULT_H = 560

COLOR_BG = "#ffffff"
COLOR_EDGE = "#9aa0a6"
COLOR_TREE = "#1a73e8"      # shortest-path tree / MST edges
COLOR_SELECTED = "#ea4335"  # edge being relaxed/considered this step
COLOR_NODE = "#ffffff"
COLOR_NODE_VISITED = "#34a853"
COLOR_NODE_FRINGE = "#fbbc04"
COLOR_NODE_CURRENT_OUTLINE = "#ea4335"
COLOR_NODE_OUTLINE = "#5f6368"
COLOR_TEXT = "#202124"
COLOR_TEXT_LIGHT = "#ffffff"


def edge_key(directed: bool, a: str, b: str):
    """Identity for an edge so step edges can be matched against model edges."""
    return (a, b) if directed else frozenset((a, b))


def edge_key_set(directed: bool, edges) -> Set:
    keys = set()
    for e in edges or []:
        keys.add(edge_key(directed, e["from"], e["to"]))
    return keys


class GraphView(tk.Canvas):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, bg=COLOR_BG, width=DEFAULT_W, height=DEFAULT_H,
                         highlightthickness=1, highlightbackground="#dadce0", **kwargs)
        self.positions: Dict[str, Tuple[float, float]] = {}
        self.vertices: List[str] = []
        self.edges: List[Edge] = []
        self.directed: bool = False

        self._drag_vertex: Optional[str] = None
        self._last_highlight: Dict[str, Any] = {}

        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda _e: self._redraw_last())

    # ------------------------------------------------------------------ model
    def set_model(self, vertices: List[str], edges: List[Edge], directed: bool) -> None:
        self.vertices = list(vertices)
        self.edges = list(edges)
        self.directed = directed
        self._ensure_positions()

    def reset_layout(self) -> None:
        self.positions = {}
        self._ensure_positions()
        self._redraw_last()

    def _size(self) -> Tuple[int, int]:
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = DEFAULT_W
        if h <= 1:
            h = DEFAULT_H
        return w, h

    def _ensure_positions(self) -> None:
        # Drop positions for removed vertices.
        self.positions = {v: p for v, p in self.positions.items() if v in self.vertices}
        missing = [v for v in self.vertices if v not in self.positions]
        if not missing:
            return
        if not self.positions:
            self._layout_circular(self.vertices)
        else:
            # Place only the new vertices on the circle without disturbing the rest.
            self._layout_circular(missing, only=True)

    def _layout_circular(self, vertices: List[str], only: bool = False) -> None:
        w, h = self._size()
        cx, cy = w / 2, h / 2
        radius = max(90, min(cx, cy) - NODE_RADIUS - 30)
        count = len(vertices)
        offset = len(self.positions) if only else 0
        total = (len(self.positions) + count) if only else count
        for i, v in enumerate(vertices):
            angle = 2 * math.pi * (offset + i) / max(1, total) - math.pi / 2
            self.positions[v] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    # ----------------------------------------------------------------- drawing
    def draw(
        self,
        visited: Optional[Set[str]] = None,
        current: Optional[str] = None,
        selected_edge: Optional[Dict[str, Any]] = None,
        tree_edges: Optional[List[Dict[str, Any]]] = None,
        distances: Optional[Dict[str, Any]] = None,
        fringe: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._last_highlight = {
            "visited": visited,
            "current": current,
            "selected_edge": selected_edge,
            "tree_edges": tree_edges,
            "distances": distances,
            "fringe": fringe,
        }
        self._ensure_positions()
        self.delete("all")

        visited_set: Set[str] = set(visited or [])
        tree_keys = edge_key_set(self.directed, tree_edges)
        selected_key = (
            edge_key(self.directed, selected_edge["from"], selected_edge["to"])
            if selected_edge else None
        )
        fringe_vertices = {item["vertex"]: item for item in (fringe or [])}

        self._draw_edges(tree_keys, selected_key)
        self._draw_nodes(visited_set, current, fringe_vertices, distances)

    def _draw_edges(self, tree_keys: Set, selected_key) -> None:
        for u, v, w in self.edges:
            if u not in self.positions or v not in self.positions:
                continue
            x1, y1 = self.positions[u]
            x2, y2 = self.positions[v]
            key = edge_key(self.directed, u, v)

            if selected_key is not None and key == selected_key:
                color, width = COLOR_SELECTED, 4
            elif key in tree_keys:
                color, width = COLOR_TREE, 4
            else:
                color, width = COLOR_EDGE, 2

            # Shorten the line so it touches node borders, not centers.
            sx, sy, ex, ey = self._trim_segment(x1, y1, x2, y2)
            if self.directed:
                self.create_line(sx, sy, ex, ey, fill=color, width=width, arrow=tk.LAST,
                                 arrowshape=(14, 16, 6))
            else:
                self.create_line(sx, sy, ex, ey, fill=color, width=width)

            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            label = w if not isinstance(w, float) or not w.is_integer() else int(w)
            self.create_text(mx, my, text=str(label), fill=COLOR_TEXT,
                             font=("Helvetica", 11, "bold"))
            self.create_rectangle(mx - 11, my - 9, mx + 11, my + 9, outline="", fill="")

    def _draw_nodes(self, visited_set, current, fringe_vertices, distances) -> None:
        for v in self.vertices:
            if v not in self.positions:
                continue
            x, y = self.positions[v]
            if v in visited_set:
                fill = COLOR_NODE_VISITED
                text_color = COLOR_TEXT_LIGHT
            elif v in fringe_vertices:
                fill = COLOR_NODE_FRINGE
                text_color = COLOR_TEXT
            else:
                fill = COLOR_NODE
                text_color = COLOR_TEXT

            outline = COLOR_NODE_CURRENT_OUTLINE if v == current else COLOR_NODE_OUTLINE
            width = 4 if v == current else 2

            self.create_oval(x - NODE_RADIUS, y - NODE_RADIUS, x + NODE_RADIUS, y + NODE_RADIUS,
                             fill=fill, outline=outline, width=width)
            self.create_text(x, y, text=str(v), fill=text_color, font=("Helvetica", 13, "bold"))

            if distances is not None and v in distances:
                d = distances[v]
                self.create_text(x, y + NODE_RADIUS + 11, text=f"d={d}", fill=COLOR_TEXT,
                                 font=("Helvetica", 10))

    @staticmethod
    def _trim_segment(x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        return (x1 + ux * NODE_RADIUS, y1 + uy * NODE_RADIUS,
                x2 - ux * NODE_RADIUS, y2 - uy * NODE_RADIUS)

    def _redraw_last(self) -> None:
        if self._last_highlight:
            self.draw(**self._last_highlight)
        else:
            self.draw()

    # -------------------------------------------------------------- dragging
    def _hit(self, x: float, y: float) -> Optional[str]:
        for v, (vx, vy) in self.positions.items():
            if math.hypot(x - vx, y - vy) <= NODE_RADIUS:
                return v
        return None

    def _on_press(self, event) -> None:
        self._drag_vertex = self._hit(event.x, event.y)

    def _on_drag(self, event) -> None:
        if self._drag_vertex is not None:
            self.positions[self._drag_vertex] = (event.x, event.y)
            self._redraw_last()

    def _on_release(self, _event) -> None:
        self._drag_vertex = None
