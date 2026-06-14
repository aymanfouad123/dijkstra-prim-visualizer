"""
Bridge between the Tkinter visualizer and the standalone algorithm modules.

The visualizer builds a graph from UI state, calls ``dijkstra.py`` or
``prim.py``, and receives a normalized :class:`VisualizerResult` object
(including recorded ``steps``) for rendering.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import dijkstra as dijkstra_mod  # noqa: E402
import prim as prim_mod  # noqa: E402

Edge = Tuple[str, str, float]
TreeEdge = Dict[str, Union[str, float]]
RawEdge = Union[TreeEdge, Tuple[str, str, float]]

ALGORITHMS = {
    ("Dijkstra", "Binary Heap"): dijkstra_mod.dijkstra_binary_heap,
    ("Dijkstra", "Linked List"): dijkstra_mod.dijkstra_linked_list,
    ("Prim", "Binary Heap"): prim_mod.prim_binary_heap,
    ("Prim", "Linked List"): prim_mod.prim_linked_list,
}

ALGORITHM_NAMES = ["Dijkstra", "Prim"]
FRINGE_NAMES = ["Binary Heap", "Linked List"]


@dataclass(frozen=True)
class GraphPreset:
    """Named graph preset for the visualizer quick-start menu."""

    id: str
    label: str
    default_source: str
    description: str
    builder: Any  # callable returning a graph with .vertices() and .neighbors()


def _graph_to_model(graph) -> Tuple[List[str], List[Edge]]:
    """Convert a backend graph object to (vertices, edges) for the UI model."""
    vertices = sorted(graph.vertices())
    seen = set()
    edge_list: List[Edge] = []
    for u in vertices:
        for v, weight in graph.neighbors(u):
            key = (min(u, v), max(u, v))
            if key in seen:
                continue
            seen.add(key)
            edge_list.append((u, v, weight))
    return vertices, edge_list


GRAPH_PRESETS: List[GraphPreset] = [
    GraphPreset(
        id="assignment",
        label="Assignment sample (Dijkstra + Prim)",
        default_source="A",
        description=(
            "6 vertices (A–F). Dijkstra from A: B=3, C=2, D=8, E=10, F=13. "
            "Prim MST total weight: 13."
        ),
        builder=dijkstra_mod.build_sample_graph,
    ),
    GraphPreset(
        id="prim_sample",
        label="Prim sample",
        default_source="A",
        description="5 vertices. Prim MST total weight: 10 (A-B, B-C, C-D, D-E).",
        builder=prim_mod.build_prim_sample_graph,
    ),
    GraphPreset(
        id="disconnected",
        label="Disconnected Prim demo",
        default_source="A",
        description=(
            "Two components: A-B-C and D-E. Prim fails unless partial MST is enabled."
        ),
        builder=prim_mod.build_disconnected_graph,
    ),
]

PRESET_BY_ID: Dict[str, GraphPreset] = {p.id: p for p in GRAPH_PRESETS}
PRESET_LABELS: List[str] = [p.label for p in GRAPH_PRESETS]


def get_preset(preset_id: str) -> GraphPreset:
    try:
        return PRESET_BY_ID[preset_id]
    except KeyError as exc:
        raise ValueError(f"Unknown preset: {preset_id!r}") from exc


def get_preset_by_label(label: str) -> GraphPreset:
    for preset in GRAPH_PRESETS:
        if preset.label == label:
            return preset
    raise ValueError(f"Unknown preset label: {label!r}")


def load_preset_data(preset_id: str) -> Tuple[List[str], List[Edge], str, str]:
    """Return (vertices, edges, default_source, description) for a preset."""
    preset = get_preset(preset_id)
    vertices, edges = _graph_to_model(preset.builder())
    return vertices, edges, preset.default_source, preset.description


def reconstruct_shortest_path(
    previous: Optional[Dict[str, Optional[str]]],
    source: str,
    target: str,
) -> List[str]:
    """Reconstruct a shortest path using the Dijkstra predecessor map."""
    return dijkstra_mod.reconstruct_path(previous, source, target)


@dataclass
class VisualizerResult:
    """UI-facing normalized result from either algorithm backend."""

    algorithm: str
    fringe_type: str
    source_or_start: str
    vertices: int
    edges: int
    runtime_ms: float
    steps: List[Dict[str, Any]] = field(default_factory=list)
    distances: Optional[Dict[str, float]] = None
    previous: Optional[Dict[str, Optional[str]]] = None
    shortest_path_tree_edges: Optional[List[TreeEdge]] = None
    mst_edges: Optional[List[TreeEdge]] = None
    total_mst_weight: Optional[float] = None
    warning: Optional[str] = None
    is_full_graph_mst: Optional[bool] = None


def edge_to_dict(edge: Optional[RawEdge]) -> Optional[TreeEdge]:
    """Convert tuple or dict edge representations to the UI dict shape."""
    if edge is None:
        return None
    if isinstance(edge, dict):
        return edge
    u, v, weight = edge
    return {"from": u, "to": v, "weight": weight}


def edges_to_dicts(edges: Optional[List[RawEdge]]) -> List[TreeEdge]:
    return [edge_to_dict(edge) for edge in (edges or []) if edge_to_dict(edge) is not None]


def normalize_step(step: Dict[str, Any], algorithm: str) -> Dict[str, Any]:
    """Map backend step records to the shape expected by GraphView and the app."""
    normalized = dict(step)
    normalized["description"] = step.get("message") or step.get("description", "")

    if algorithm == "Prim":
        normalized["tree_edges"] = edges_to_dicts(step.get("mst_edges"))
    else:
        normalized["tree_edges"] = edges_to_dicts(step.get("tree_edges"))

    selected = step.get("selected_edge")
    if selected is not None:
        normalized["selected_edge"] = edge_to_dict(selected)

    return normalized


def build_graph(
    algorithm: str,
    vertices: List[str],
    edges: List[Edge],
    directed: bool = False,
):
    """Construct the correct graph class for the selected algorithm."""
    if algorithm == "Dijkstra":
        graph = dijkstra_mod.Graph(directed=directed)
    else:
        graph = prim_mod.Graph(directed=False)
    for vertex in vertices:
        graph.add_vertex(vertex)
    for u, v, weight in edges:
        graph.add_edge(u, v, weight)
    return graph


def normalize_result(
    raw: Dict[str, Any],
    algorithm: str,
    vertex_count: int,
    edge_count: int,
) -> VisualizerResult:
    """Convert a raw algorithm dict into a VisualizerResult."""
    steps = [normalize_step(step, algorithm) for step in (raw.get("steps") or [])]

    if algorithm == "Dijkstra":
        tree_edges = edges_to_dicts(raw.get("tree_edges"))
        return VisualizerResult(
            algorithm=raw["algorithm"],
            fringe_type=raw["fringe"],
            source_or_start=raw["source"],
            vertices=vertex_count,
            edges=edge_count,
            runtime_ms=raw["runtime_ms"],
            steps=steps,
            distances=raw.get("distances"),
            previous=raw.get("previous"),
            shortest_path_tree_edges=tree_edges,
        )

    mst_edges = edges_to_dicts(raw.get("mst_edges"))
    return VisualizerResult(
        algorithm=raw["algorithm"],
        fringe_type=raw["fringe"],
        source_or_start=raw["start"],
        vertices=vertex_count,
        edges=edge_count,
        runtime_ms=raw["runtime_ms"],
        steps=steps,
        mst_edges=mst_edges,
        total_mst_weight=raw.get("total_weight"),
        warning=raw.get("warning"),
        is_full_graph_mst=raw.get("is_full_graph_mst"),
    )


def run_algorithm(
    algorithm: str,
    fringe: str,
    vertices: List[str],
    edges: List[Edge],
    source: str,
    directed: bool = False,
    record_steps: bool = True,
    allow_partial: bool = False,
) -> VisualizerResult:
    """
    Run the selected algorithm/fringe combination on the given graph.

    Validation errors from the backend surface as ``ValueError``.
    """
    try:
        func = ALGORITHMS[(algorithm, fringe)]
    except KeyError as exc:  # pragma: no cover - guarded by the UI menus.
        raise ValueError(f"Unknown algorithm/fringe combination: {algorithm} / {fringe}") from exc

    graph = build_graph(algorithm, vertices, edges, directed=directed)
    edge_count = len(edges) if directed or algorithm == "Dijkstra" else len(edges)

    if algorithm == "Prim":
        raw = func(graph, source, record_steps=record_steps, allow_partial=allow_partial)
    else:
        raw = func(graph, source, record_steps=record_steps)

    return normalize_result(raw, algorithm, len(vertices), edge_count)


def sample_graph_data() -> Tuple[List[str], List[Edge]]:
    """Return the assignment sample graph as (vertices, edges) for the UI model."""
    vertices, edges, _, _ = load_preset_data("assignment")
    return vertices, edges


def edge_weight_value(weight_text: str, algorithm: str = "Dijkstra") -> float:
    """Parse and validate a weight string coming from a UI entry field."""
    try:
        weight = float(weight_text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Weight {weight_text!r} is not a number.") from exc
    if algorithm == "Dijkstra" and weight < 0:
        raise ValueError("Negative edge weights are not allowed for Dijkstra's algorithm.")
    return int(weight) if weight == int(weight) else weight
