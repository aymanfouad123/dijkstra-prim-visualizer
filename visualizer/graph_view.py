"""QGraphicsView renderer for graph state and algorithm steps."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView

from . import algorithm_bridge as bridge

Edge = Tuple[str, str, float]

NODE_RADIUS = 22
MIN_WIDTH = 680
MIN_HEIGHT = 420
RESIZE_DEBOUNCE_MS = 150

EDGE_COLOR = "#8a949e"
TREE_COLOR = "#2563eb"
SELECTED_COLOR = "#dc2626"
VISITED_COLOR = "#16a34a"
FRINGE_COLOR = "#facc15"
NODE_COLOR = "#ffffff"
TEXT_COLOR = "#111827"


def _edge_key(u: str, v: str, directed: bool):
    return (u, v) if directed else frozenset((u, v))


class GraphView(QGraphicsView):
    """Visualization-only canvas. Graph editing is done through form controls."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.setFrameShape(QFrame.Shape.Box)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setInteractive(False)

        self.vertices: List[str] = []
        self.edges: List[Edge] = []
        self.directed = False
        self.positions: Dict[str, Tuple[float, float]] = {}
        self._last: Dict[str, Any] = {}
        self._layout_size: Optional[Tuple[int, int]] = None
        self._layout_frozen = False
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_resize)
        self._pending_resize: Optional[Tuple[int, int]] = None

    def set_graph(self, vertices: List[str], edges: List[Edge], directed: bool) -> None:
        self.vertices = list(vertices)
        self.edges = list(edges)
        self.directed = directed
        self.positions = {v: p for v, p in self.positions.items() if v in self.vertices}
        if not self._layout_frozen:
            self._ensure_layout()

    def reset_layout(self) -> None:
        if self._layout_frozen:
            return
        self.positions = {}
        self._layout_size = None
        self._ensure_layout()
        self.draw(**self._last)

    def freeze_layout(self) -> None:
        """Lock vertex positions after a successful algorithm run."""
        self._layout_frozen = True

    def unfreeze_layout(self) -> None:
        """Allow layout updates again when returning to editing mode."""
        self._layout_frozen = False

    def clear(self) -> None:
        self.vertices = []
        self.edges = []
        self.positions = {}
        self._last = {}
        self._layout_size = None
        self._layout_frozen = False
        self.scene().clear()

    def draw(
        self,
        visited: Optional[Set[str]] = None,
        current: Optional[str] = None,
        fringe: Optional[List[Dict[str, Any]]] = None,
        tree_edges: Optional[List[Dict[str, Any]]] = None,
        selected_edge: Optional[Dict[str, Any]] = None,
        distances: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._last = {
            "visited": visited,
            "current": current,
            "fringe": fringe,
            "tree_edges": tree_edges,
            "selected_edge": selected_edge,
            "distances": distances,
        }
        self._render(**self._last)

    def draw_now(self) -> None:
        """Force a synchronous render of the most recent state."""
        self._render(**self._last)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._layout_frozen:
            return
        self._pending_resize = (max(self.viewport().width(), 1), max(self.viewport().height(), 1))
        self._resize_timer.start(RESIZE_DEBOUNCE_MS)

    def _apply_resize(self) -> None:
        if self._layout_frozen:
            return
        new_size = self._pending_resize
        if new_size is None:
            return
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

    def _render(
        self,
        visited: Optional[Set[str]] = None,
        current: Optional[str] = None,
        fringe: Optional[List[Dict[str, Any]]] = None,
        tree_edges: Optional[List[Dict[str, Any]]] = None,
        selected_edge: Optional[Dict[str, Any]] = None,
        distances: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._layout_frozen:
            self._ensure_layout()

        scene = self.scene()
        scene.clear()

        width, height = self._canvas_size()
        scene.setSceneRect(0, 0, width, height)

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
            self._draw_edge(scene, u, v, weight, tree_keys, selected_key)
        for vertex in self.vertices:
            self._draw_vertex(scene, vertex, visited_set, fringe_vertices, current, distances)

    def _canvas_size(self) -> Tuple[int, int]:
        return max(self.viewport().width(), MIN_WIDTH), max(self.viewport().height(), MIN_HEIGHT)

    def export_canvas_size(self) -> Tuple[int, int]:
        """Canvas dimensions matching frozen layout coordinates for frame export."""
        if self._layout_size:
            return (
                max(self._layout_size[0], MIN_WIDTH),
                max(self._layout_size[1], MIN_HEIGHT),
            )
        return self._canvas_size()

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

    def _draw_edge(self, scene, u: str, v: str, weight: float, tree_keys: Set, selected_key) -> None:
        if u not in self.positions or v not in self.positions:
            return

        x1, y1 = self.positions[u]
        x2, y2 = self.positions[v]
        key = _edge_key(u, v, self.directed)
        color = EDGE_COLOR
        line_width = 2
        if key in tree_keys:
            color = TREE_COLOR
            line_width = 4
        if selected_key == key:
            color = SELECTED_COLOR
            line_width = 4

        sx, sy, ex, ey = self._trim(x1, y1, x2, y2)
        pen = QPen(QColor(color), line_width)
        line = QGraphicsLineItem(sx, sy, ex, ey)
        line.setPen(pen)
        scene.addItem(line)

        if self.directed:
            angle = math.atan2(ey - sy, ex - sx)
            arrow_len = 14
            ax = ex - arrow_len * math.cos(angle - 0.4)
            ay = ey - arrow_len * math.sin(angle - 0.4)
            bx = ex - arrow_len * math.cos(angle + 0.4)
            by = ey - arrow_len * math.sin(angle + 0.4)
            arrow = QGraphicsPolygonItem(QPolygonF([(ex, ey), (ax, ay), (bx, by)]))
            arrow.setPen(QPen(Qt.PenStyle.NoPen))
            arrow.setBrush(QBrush(QColor(color)))
            scene.addItem(arrow)

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label = bridge.format_weight(weight)
        font = QFont("Helvetica", 10, QFont.Weight.Bold)
        text = QGraphicsSimpleTextItem(label)
        text.setFont(font)
        text.setBrush(QBrush(QColor(TEXT_COLOR)))
        text_rect = text.boundingRect()
        pad_x = max(14, len(label) * 4 + 8)
        pad_y = 10
        bg = QGraphicsRectItem(
            mx - pad_x,
            my - text_rect.height() / 2 - 4,
            pad_x * 2,
            text_rect.height() + 8,
        )
        bg.setPen(QPen(Qt.PenStyle.NoPen))
        bg.setBrush(QBrush(QColor("#ffffff")))
        scene.addItem(bg)
        text.setPos(mx - text_rect.width() / 2, my - text_rect.height() / 2)
        scene.addItem(text)

    def _draw_vertex(
        self,
        scene,
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
        outline_width = 4 if vertex == current else 2

        ellipse = QGraphicsEllipseItem(
            x - NODE_RADIUS,
            y - NODE_RADIUS,
            NODE_RADIUS * 2,
            NODE_RADIUS * 2,
        )
        ellipse.setPen(QPen(QColor(outline), outline_width))
        ellipse.setBrush(QBrush(QColor(fill)))
        scene.addItem(ellipse)

        font = QFont("Helvetica", 12, QFont.Weight.Bold)
        label = QGraphicsSimpleTextItem(vertex)
        label.setFont(font)
        label.setBrush(QBrush(QColor(text_color)))
        label_rect = label.boundingRect()
        label.setPos(x - label_rect.width() / 2, y - label_rect.height() / 2)
        scene.addItem(label)

        if distances is not None and vertex in distances:
            dfont = QFont("Helvetica", 10)
            dlabel = QGraphicsSimpleTextItem(f"d={bridge.format_distance(distances[vertex])}")
            dlabel.setFont(dfont)
            dlabel.setBrush(QBrush(QColor(TEXT_COLOR)))
            drect = dlabel.boundingRect()
            dlabel.setPos(x - drect.width() / 2, y + NODE_RADIUS + 4)
            scene.addItem(dlabel)

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
