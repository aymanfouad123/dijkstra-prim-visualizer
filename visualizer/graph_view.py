"""Canvas renderer for graph state and algorithm steps."""

from __future__ import annotations

import math
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from . import algorithm_bridge as bridge

Edge = Tuple[str, str, float]

NODE_RADIUS = 22
MIN_WIDTH = 680
MIN_HEIGHT = 420

EDGE_COLOR = "#8a949e"
TREE_COLOR = "#2563eb"
SELECTED_COLOR = "#dc2626"
PENDING_COLOR = "#7c3aed"
VISITED_COLOR = "#16a34a"
FRINGE_COLOR = "#facc15"
NODE_COLOR = "#ffffff"
TEXT_COLOR = "#111827"


def _edge_key(u: str, v: str, directed: bool):
    return (u, v) if directed else frozenset((u, v))


class GraphView(tk.Canvas):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(
            parent,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d1d5db",
            **kwargs,
        )
        self.vertices: List[str] = []
        self.edges: List[Edge] = []
        self.directed = False
        self.positions: Dict[str, Tuple[float, float]] = {}
        self._last: Dict[str, Any] = {}
        self._dragging: Optional[str] = None
        self._press_at: Optional[Tuple[float, float]] = None
        self._layout_size: Optional[Tuple[int, int]] = None
        self._redraw_pending = False
        self.manual_enabled = False
        self.pending_vertex: Optional[str] = None
        self.on_blank_double_click: Optional[Callable[[float, float], None]] = None
        self.on_vertex_click: Optional[Callable[[str], None]] = None
        self.bind("<Configure>", self._on_configure)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_double_click)

    def set_graph(self, vertices: List[str], edges: List[Edge], directed: bool) -> None:
        self.vertices = list(vertices)
        self.edges = list(edges)
        self.directed = directed
        self.positions = {v: p for v, p in self.positions.items() if v in self.vertices}
        self._ensure_layout()

    def reset_layout(self) -> None:
        self.positions = {}
        self._layout_size = None
        self._ensure_layout()
        self.draw(**self._last)

    def clear(self) -> None:
        self.vertices = []
        self.edges = []
        self.positions = {}
        self._last = {}
        self._dragging = None
        self._press_at = None
        self._layout_size = None
        self.pending_vertex = None
        self.delete("all")

    def set_manual_mode(self, enabled: bool) -> None:
        self.manual_enabled = enabled
        if not enabled:
            self.pending_vertex = None
        self.draw(**self._last)

    def set_pending_vertex(self, vertex: Optional[str]) -> None:
        self.pending_vertex = vertex if vertex in self.vertices else None
        self.draw(**self._last)

    def draw(
        self,
        visited: Optional[Set[str]] = None,
        current: Optional[str] = None,
        fringe: Optional[List[Dict[str, Any]]] = None,
        tree_edges: Optional[List[Dict[str, Any]]] = None,
        selected_edge: Optional[Dict[str, Any]] = None,
        distances: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Record the latest desired state and coalesce repeated calls into a
        # single render on the next idle cycle. Without this, fast event
        # streams (drag motion, window resize) trigger one full canvas rebuild
        # per event and starve the event loop, which makes clicks feel dropped.
        self._last = {
            "visited": visited,
            "current": current,
            "fringe": fringe,
            "tree_edges": tree_edges,
            "selected_edge": selected_edge,
            "distances": distances,
        }
        self._schedule_redraw()

    def draw_now(self) -> None:
        """Force a synchronous render of the most recent state."""
        self._redraw_pending = False
        self._render(**self._last)

    def _schedule_redraw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after_idle(self._flush_redraw)

    def _flush_redraw(self) -> None:
        if not self._redraw_pending:
            return
        self._redraw_pending = False
        try:
            self._render(**self._last)
        except tk.TclError:
            pass

    def _render(
        self,
        visited: Optional[Set[str]] = None,
        current: Optional[str] = None,
        fringe: Optional[List[Dict[str, Any]]] = None,
        tree_edges: Optional[List[Dict[str, Any]]] = None,
        selected_edge: Optional[Dict[str, Any]] = None,
        distances: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._ensure_layout()
        self.delete("all")

        visited_set = set(visited or [])
        fringe_vertices = {item.get("vertex") for item in (fringe or [])}
        tree_keys = {
            _edge_key(edge["from"], edge["to"], self.directed) for edge in (tree_edges or [])
        }
        selected_key = (
            _edge_key(selected_edge["from"], selected_edge["to"], self.directed)
            if selected_edge
            else None
        )

        for u, v, weight in self.edges:
            self._draw_edge(u, v, weight, tree_keys, selected_key)
        for vertex in self.vertices:
            self._draw_vertex(vertex, visited_set, fringe_vertices, current, distances)

    def _canvas_size(self) -> Tuple[int, int]:
        return max(self.winfo_width(), MIN_WIDTH), max(self.winfo_height(), MIN_HEIGHT)

    def _ensure_layout(self) -> None:
        missing = [v for v in self.vertices if v not in self.positions]
        if not missing:
            return

        width, height = self._canvas_size()
        self._layout_size = (width, height)
        cx, cy = width / 2, height / 2
        radius = max(90, min(width, height) / 2 - 56)
        total = len(self.vertices)

        for index, vertex in enumerate(self.vertices):
            if vertex in self.positions:
                continue
            angle = 2 * math.pi * index / max(total, 1) - math.pi / 2
            self.positions[vertex] = (
                cx + radius * math.cos(angle),
                cy + radius * math.sin(angle),
            )

    def _on_configure(self, event) -> None:
        new_size = (max(event.width, 1), max(event.height, 1))
        old_size = self._layout_size
        if self.positions and old_size and old_size[0] > 1 and old_size[1] > 1:
            sx = new_size[0] / old_size[0]
            sy = new_size[1] / old_size[1]
            self.positions = {
                vertex: (x * sx, y * sy)
                for vertex, (x, y) in self.positions.items()
            }
        self._layout_size = new_size
        self.draw(**self._last)

    def _draw_edge(self, u: str, v: str, weight: float, tree_keys: Set, selected_key) -> None:
        if u not in self.positions or v not in self.positions:
            return

        x1, y1 = self.positions[u]
        x2, y2 = self.positions[v]
        key = _edge_key(u, v, self.directed)
        color = EDGE_COLOR
        width = 2
        if key in tree_keys:
            color = TREE_COLOR
            width = 4
        if selected_key == key:
            color = SELECTED_COLOR
            width = 4

        sx, sy, ex, ey = self._trim(x1, y1, x2, y2)
        arrow = tk.LAST if self.directed else tk.NONE
        self.create_line(
            sx,
            sy,
            ex,
            ey,
            fill=color,
            width=width,
            arrow=arrow,
            arrowshape=(14, 16, 6),
        )

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label = bridge.format_weight(weight)
        pad_x = max(14, len(label) * 4 + 8)
        self.create_rectangle(mx - pad_x, my - 10, mx + pad_x, my + 10, fill="#ffffff", outline="")
        self.create_text(mx, my, text=label, fill=TEXT_COLOR, font=("Helvetica", 10, "bold"))

    def _draw_vertex(
        self,
        vertex: str,
        visited: Set[str],
        fringe_vertices: Set[str],
        current: Optional[str],
        distances: Optional[Dict[str, Any]],
    ) -> None:
        x, y = self.positions[vertex]
        fill = NODE_COLOR
        text_color = TEXT_COLOR
        if vertex in visited:
            fill = VISITED_COLOR
            text_color = "#ffffff"
        elif vertex in fringe_vertices:
            fill = FRINGE_COLOR

        outline = SELECTED_COLOR if vertex == current else "#4b5563"
        width = 4 if vertex == current else 2
        if vertex == self.pending_vertex:
            outline = PENDING_COLOR
            width = 4

        self.create_oval(
            x - NODE_RADIUS,
            y - NODE_RADIUS,
            x + NODE_RADIUS,
            y + NODE_RADIUS,
            fill=fill,
            outline=outline,
            width=width,
        )
        self.create_text(x, y, text=vertex, fill=text_color, font=("Helvetica", 12, "bold"))
        if distances is not None and vertex in distances:
            self.create_text(
                x,
                y + NODE_RADIUS + 12,
                text=f"d={bridge.format_distance(distances[vertex])}",
                fill=TEXT_COLOR,
                font=("Helvetica", 10),
            )

    @staticmethod
    def _trim(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float, float, float]:
        dx, dy = x2 - x1, y2 - y1
        distance = math.hypot(dx, dy) or 1
        ux, uy = dx / distance, dy / distance
        return (
            x1 + ux * NODE_RADIUS,
            y1 + uy * NODE_RADIUS,
            x2 - ux * NODE_RADIUS,
            y2 - uy * NODE_RADIUS,
        )

    def _hit(self, x: float, y: float) -> Optional[str]:
        for vertex, (vx, vy) in self.positions.items():
            if math.hypot(x - vx, y - vy) <= NODE_RADIUS:
                return vertex
        return None

    def _on_press(self, event) -> None:
        self._dragging = self._hit(event.x, event.y)
        self._press_at = (event.x, event.y)

    def _on_drag(self, event) -> None:
        if self._dragging:
            self.positions[self._dragging] = (event.x, event.y)
            self.draw(**self._last)

    def _on_release(self, event) -> None:
        clicked_vertex = self._dragging
        was_click = True
        if self._press_at is not None:
            was_click = math.hypot(event.x - self._press_at[0], event.y - self._press_at[1]) < 5
        if self.manual_enabled and was_click and clicked_vertex and self.on_vertex_click:
            self.on_vertex_click(clicked_vertex)
        self._dragging = None
        self._press_at = None

    def _on_double_click(self, event) -> None:
        if not self.manual_enabled or self._hit(event.x, event.y):
            return
        if self.on_blank_double_click:
            self.on_blank_double_click(event.x, event.y)
