"""Adapter layer between the visualizer UI and the algorithm modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import dijkstra
import prim

Edge = Tuple[str, str, float]

ALGORITHMS = ("Dijkstra", "Prim")
FRINGES = ("Binary Heap", "Linked List")


@dataclass(frozen=True)
class Preset:
    label: str
    algorithm_hint: str
    default_start: str
    directed: bool
    edges: Tuple[Edge, ...]
    vertices: Tuple[str, ...] = ()


PRESETS: Tuple[Preset, ...] = (
    Preset(
        label="Dijkstra sample",
        algorithm_hint="Dijkstra",
        default_start="A",
        directed=False,
        edges=(
            ("A", "B", 4),
            ("A", "C", 2),
            ("B", "C", 1),
            ("B", "D", 5),
            ("C", "D", 8),
            ("C", "E", 10),
            ("D", "E", 2),
            ("D", "F", 6),
            ("E", "F", 3),
        ),
    ),
    Preset(
        label="Prim sample",
        algorithm_hint="Prim",
        default_start="A",
        directed=False,
        edges=(
            ("A", "B", 3),
            ("A", "C", 6),
            ("B", "C", 1),
            ("B", "D", 5),
            ("C", "D", 2),
            ("C", "E", 7),
            ("D", "E", 4),
        ),
    ),
    Preset(
        label="Disconnected Prim sample",
        algorithm_hint="Prim",
        default_start="A",
        directed=False,
        edges=(("A", "B", 1), ("B", "C", 2), ("D", "E", 5)),
    ),
)


def preset_labels(algorithm: Optional[str] = None) -> List[str]:
    return [
        preset.label
        for preset in PRESETS
        if algorithm is None or preset.algorithm_hint == algorithm
    ]


def get_preset(label: str, algorithm: Optional[str] = None) -> Preset:
    if not label:
        raise ValueError("Select a preset to load.")

    for preset in PRESETS:
        if preset.label != label:
            continue
        if algorithm is not None and preset.algorithm_hint != algorithm:
            raise ValueError(f"{preset.label} is not available for {algorithm}.")
        return preset

    raise ValueError(f"Unknown preset: {label}")


def vertices_from_edges(
    edges: Iterable[Edge],
    extra_vertices: Optional[Iterable[str]] = None,
) -> List[str]:
    vertices = set(extra_vertices or [])
    for u, v, _weight in edges:
        vertices.add(u)
        vertices.add(v)
    return sorted(vertices, key=str)


def parse_weight(raw: str, algorithm: str) -> float:
    try:
        weight = float(raw.strip())
    except (AttributeError, ValueError) as exc:
        raise ValueError("Weight must be a number.") from exc

    if algorithm == "Dijkstra" and weight < 0:
        raise ValueError("Dijkstra requires non-negative edge weights.")

    return int(weight) if weight.is_integer() else weight


def format_weight(weight: Any) -> str:
    if isinstance(weight, float) and weight.is_integer():
        return str(int(weight))
    return str(weight)


def normalize_edge(edge: Any) -> Optional[Dict[str, Any]]:
    if edge is None:
        return None

    if isinstance(edge, dict):
        try:
            return {
                "from": edge["from"],
                "to": edge["to"],
                "weight": edge["weight"],
            }
        except KeyError as exc:
            raise ValueError(f"Malformed edge record: {edge}") from exc

    u, v, weight = edge
    return {"from": u, "to": v, "weight": weight}


def normalize_edges(edges: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for edge in edges or []:
        item = normalize_edge(edge)
        if item is not None:
            normalized.append(item)
    return normalized


def normalize_step(step: Dict[str, Any], algorithm: str) -> Dict[str, Any]:
    normalized = dict(step)
    normalized["message"] = step.get("message", "")
    if algorithm == "Dijkstra":
        normalized["tree_edges"] = normalize_edges(step.get("tree_edges"))
    else:
        normalized["tree_edges"] = normalize_edges(step.get("mst_edges"))
    normalized["selected_edge"] = normalize_edge(step.get("selected_edge"))
    return normalized


def validate_selection(algorithm: str, fringe: str) -> None:
    if algorithm not in ALGORITHMS:
        raise ValueError("Choose Dijkstra or Prim.")
    if fringe not in FRINGES:
        raise ValueError("Choose Binary Heap or Linked List.")


def validate_graph_inputs(
    algorithm: str,
    fringe: str,
    vertices: Sequence[str],
    edges: Sequence[Edge],
    start: str,
    directed: bool,
) -> None:
    validate_selection(algorithm, fringe)

    if not vertices:
        raise ValueError("Load or build a graph first.")
    if start not in vertices:
        raise ValueError("Choose a valid source/start vertex.")
    if algorithm == "Prim" and directed:
        raise ValueError("Prim requires an undirected graph.")
    if algorithm == "Dijkstra":
        for _u, _v, weight in edges:
            if weight < 0:
                raise ValueError("Dijkstra requires non-negative edge weights.")


def build_graph(algorithm: str, vertices: Sequence[str], edges: Sequence[Edge], directed: bool):
    graph = dijkstra.Graph(directed=directed) if algorithm == "Dijkstra" else prim.Graph()
    for vertex in vertices:
        graph.add_vertex(vertex)
    for u, v, weight in edges:
        graph.add_edge(u, v, weight)
    return graph


def run_algorithm(
    algorithm: str,
    fringe: str,
    vertices: Sequence[str],
    edges: Sequence[Edge],
    start: str,
    directed: bool = False,
    allow_partial_prim: bool = False,
) -> Dict[str, Any]:
    directed = directed and algorithm == "Dijkstra"
    validate_graph_inputs(algorithm, fringe, vertices, edges, start, directed)
    graph = build_graph(algorithm, vertices, edges, directed)

    if algorithm == "Dijkstra":
        if fringe == "Binary Heap":
            raw = dijkstra.dijkstra_binary_heap(graph, start, record_steps=True)
        else:
            raw = dijkstra.dijkstra_linked_list(graph, start, record_steps=True)
    else:
        if fringe == "Binary Heap":
            raw = prim.prim_binary_heap(
                graph, start, record_steps=True, allow_partial=allow_partial_prim
            )
        else:
            raw = prim.prim_linked_list(
                graph, start, record_steps=True, allow_partial=allow_partial_prim
            )

    result = dict(raw)
    result["steps"] = [normalize_step(step, algorithm) for step in raw.get("steps", [])]
    if algorithm == "Dijkstra":
        result["final_edges"] = normalize_edges(raw.get("tree_edges"))
    else:
        result["final_edges"] = normalize_edges(raw.get("mst_edges"))
    return result


def format_distance(value: Any) -> str:
    if value == float("inf"):
        return "inf"
    return str(value)
