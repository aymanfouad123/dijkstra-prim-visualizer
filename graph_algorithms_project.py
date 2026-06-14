"""
Graph Algorithms Final Project - Option 1
=========================================

Project scope:
    Implement and compare Dijkstra's shortest-path algorithm and Prim's
    minimum-spanning-tree algorithm using two different fringe data structures:
        1. Binary heap fringe
        2. Linked-list fringe

This file is designed as a self-contained backend for the assignment. It includes:
    - Graph representation using adjacency lists
    - Binary heap fringe implementation
    - Linked-list fringe implementation
    - Dijkstra with binary heap
    - Dijkstra with linked list
    - Prim with binary heap
    - Prim with linked list
    - Sample graph with known expected answers
    - Correctness and edge-case tests
    - Random sparse/dense graph generators
    - Benchmark runner that exports CSV data for the final report
    - Optional algorithm step export as JSON for screenshots/animations later

How to run:
    python graph_algorithms_project.py --mode demo
    python graph_algorithms_project.py --mode test
    python graph_algorithms_project.py --mode benchmark
    python graph_algorithms_project.py --mode export-steps
    python graph_algorithms_project.py --mode all

Notes for the report:
    - Dijkstra requires non-negative edge weights.
    - Prim requires an undirected, connected graph.
    - Both algorithms are greedy algorithms that repeatedly select the minimum
      priority item from a fringe.
    - The main experiment compares the cost of extract-min using a binary heap
      versus scanning a linked list.

Author: Ayman Fouad
"""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import os
import random
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Set, Iterable, Any, Callable


# =============================================================================
# Type aliases
# =============================================================================

Vertex = str
Weight = float
AdjacentEdge = Tuple[Vertex, Weight]
TreeEdge = Dict[str, Any]
Step = Dict[str, Any]


# =============================================================================
# Graph representation
# =============================================================================

class Graph:
    """
    Weighted graph represented using adjacency lists.

    This matches the project requirement:
        "Assume adjacency list representations of the input graphs."

    For an undirected graph, each edge is stored twice:
        u -> v
        v -> u

    For a directed graph, each edge is stored only once:
        u -> v

    In this project, Prim's algorithm requires an undirected connected graph.
    Dijkstra can run on directed or undirected graphs, but all weights must be
    non-negative.
    """

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self.vertices: Set[Vertex] = set()
        self.adj: Dict[Vertex, List[AdjacentEdge]] = {}

    def add_vertex(self, v: Vertex) -> None:
        """Add a vertex if it does not already exist."""
        self.vertices.add(v)
        if v not in self.adj:
            self.adj[v] = []

    def add_edge(self, u: Vertex, v: Vertex, weight: Weight) -> None:
        """
        Add a weighted edge.

        We reject negative weights because Dijkstra's algorithm is part of the
        project and Dijkstra is not correct with negative edge weights.
        Prim's algorithm can mathematically handle negative weights, but keeping
        all weights non-negative makes the project input rules consistent.
        """
        if weight < 0:
            raise ValueError(
                f"Negative edge weight {weight} is not allowed. "
                "Dijkstra's algorithm requires non-negative weights."
            )

        self.add_vertex(u)
        self.add_vertex(v)

        self.adj[u].append((v, weight))

        if not self.directed:
            self.adj[v].append((u, weight))

    def neighbors(self, v: Vertex) -> List[AdjacentEdge]:
        """Return adjacency list for vertex v."""
        return self.adj.get(v, [])

    def vertex_count(self) -> int:
        return len(self.vertices)

    def edge_count(self) -> int:
        """Return number of logical edges."""
        total = sum(len(edges) for edges in self.adj.values())
        return total if self.directed else total // 2

    def validate_vertex_exists(self, v: Vertex) -> None:
        if v not in self.vertices:
            raise ValueError(f"Vertex {v!r} does not exist in the graph.")

    def validate_no_negative_edges(self) -> None:
        """Defensive validation used before Dijkstra."""
        for u in self.vertices:
            for v, weight in self.neighbors(u):
                if weight < 0:
                    raise ValueError(
                        f"Dijkstra cannot run because edge {u}->{v} has negative weight {weight}."
                    )

    def is_connected_undirected(self) -> bool:
        """
        Check connectivity using BFS.

        This is intended for undirected graphs before running Prim. If the graph
        is disconnected, there is no single minimum spanning tree; there is only
        a minimum spanning forest. For this project, we reject disconnected input
        for Prim to keep the output simple and correct.
        """
        if self.directed:
            return False

        if not self.vertices:
            return True

        start = next(iter(self.vertices))
        visited: Set[Vertex] = set()
        queue: deque[Vertex] = deque([start])

        while queue:
            u = queue.popleft()
            if u in visited:
                continue
            visited.add(u)

            for v, _ in self.neighbors(u):
                if v not in visited:
                    queue.append(v)

        return len(visited) == len(self.vertices)

    def get_edge_weight(self, u: Vertex, v: Vertex) -> Optional[Weight]:
        """Return the weight of edge u->v if present; otherwise None."""
        for neighbor, weight in self.neighbors(u):
            if neighbor == v:
                return weight
        return None

    def sorted_vertices(self) -> List[Vertex]:
        """Return vertices in deterministic order for stable output."""
        return sorted(self.vertices, key=str)

    def to_edge_list(self) -> List[Tuple[Vertex, Vertex, Weight]]:
        """Return logical edge list, avoiding duplicates for undirected graphs."""
        edges: List[Tuple[Vertex, Vertex, Weight]] = []
        seen: Set[Tuple[Vertex, Vertex]] = set()

        for u in self.sorted_vertices():
            for v, weight in self.neighbors(u):
                if self.directed:
                    edges.append((u, v, weight))
                else:
                    key = tuple(sorted((u, v)))
                    if key not in seen:
                        seen.add(key)
                        edges.append((u, v, weight))

        return edges


# =============================================================================
# Fringe data structures
# =============================================================================

class BinaryHeapFringe:
    """
    Binary heap fringe.

    A fringe is the set of candidate vertices/edges that may be selected next.
    Both Dijkstra and Prim repeatedly perform an extract-min operation on this
    fringe.

    This implementation uses Python's heapq module internally, which implements
    a binary heap. The class wrapper keeps the project logic explicit and makes
    it easy to compare against LinkedListFringe.

    Implementation note:
        We use lazy insertion instead of true decrease-key. When a better
        priority is discovered, we push another entry into the heap. Later, stale
        entries are skipped by the algorithm. This is common in practical
        Dijkstra/Prim implementations and keeps the code simple.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Weight, int, Vertex, Optional[Vertex]]] = []
        self._counter = 0  # Tie-breaker so vertices do not need to be comparable.

    def push(self, priority: Weight, vertex: Vertex, parent: Optional[Vertex] = None) -> None:
        heapq.heappush(self._heap, (priority, self._counter, vertex, parent))
        self._counter += 1

    def pop_min(self) -> Tuple[Weight, Vertex, Optional[Vertex]]:
        if self.is_empty():
            raise IndexError("Cannot pop from an empty binary heap fringe.")
        priority, _, vertex, parent = heapq.heappop(self._heap)
        return priority, vertex, parent

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def snapshot(self) -> List[Dict[str, Any]]:
        """
        Return a copy of fringe contents for output/animation.

        The heap array is not globally sorted, so we sort only the snapshot for
        readability. This does not affect the actual algorithm.
        """
        items = [
            {"vertex": vertex, "priority": priority, "parent": parent}
            for priority, _, vertex, parent in self._heap
        ]
        return sorted(items, key=lambda x: (x["priority"], str(x["vertex"])))


class LinkedListFringe:
    """
    Linked-list style fringe.

    Python's built-in list is used as the storage container, but the operations
    model a simple linked-list fringe:
        - Insert/update candidate: O(V) scan in this simple implementation
        - Extract minimum: O(V) scan

    The important behavior for the assignment is that extract-min is not a heap
    operation; it scans the fringe linearly. This gives the expected comparison
    against the binary heap version.
    """

    def __init__(self) -> None:
        self._items: List[Dict[str, Any]] = []

    def push_or_update(self, priority: Weight, vertex: Vertex, parent: Optional[Vertex] = None) -> None:
        """
        Insert a new candidate or update an existing one if the new priority is better.
        """
        for item in self._items:
            if item["vertex"] == vertex:
                if priority < item["priority"]:
                    item["priority"] = priority
                    item["parent"] = parent
                return

        self._items.append({"priority": priority, "vertex": vertex, "parent": parent})

    def pop_min(self) -> Tuple[Weight, Vertex, Optional[Vertex]]:
        """Remove and return the item with minimum priority by scanning the list."""
        if self.is_empty():
            raise IndexError("Cannot pop from an empty linked-list fringe.")

        min_index = 0
        for i in range(1, len(self._items)):
            current = self._items[i]
            best = self._items[min_index]
            if (current["priority"], str(current["vertex"])) < (best["priority"], str(best["vertex"])):
                min_index = i

        item = self._items.pop(min_index)
        return item["priority"], item["vertex"], item["parent"]

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def snapshot(self) -> List[Dict[str, Any]]:
        return sorted([dict(item) for item in self._items], key=lambda x: (x["priority"], str(x["vertex"])))


# =============================================================================
# Result helpers
# =============================================================================

@dataclass
class AlgorithmResult:
    """
    Standard result object returned by all four algorithm implementations.
    """
    algorithm: str
    fringe_type: str
    source_or_start: Vertex
    vertices: int
    edges: int
    runtime_ms: float
    distances: Optional[Dict[Vertex, Weight]] = None
    previous: Optional[Dict[Vertex, Optional[Vertex]]] = None
    shortest_path_tree_edges: Optional[List[TreeEdge]] = None
    mst_edges: Optional[List[TreeEdge]] = None
    total_mst_weight: Optional[Weight] = None
    steps: Optional[List[Step]] = None


def _safe_number(x: Any) -> Any:
    """Convert infinity to a string so exported JSON is strict and readable."""
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return x


def make_step(
    description: str,
    current_vertex: Optional[Vertex] = None,
    selected_edge: Optional[TreeEdge] = None,
    visited: Optional[Set[Vertex]] = None,
    fringe: Optional[List[Dict[str, Any]]] = None,
    tree_edges: Optional[List[TreeEdge]] = None,
    distances: Optional[Dict[Vertex, Weight]] = None,
) -> Step:
    """
    Create a serializable algorithm state.

    The project asks for showing major iterations using animation. Even though
    this file focuses on algorithms/evaluation, returning steps makes it easy to
    build animation later or export PNG/GIF frames from another UI.
    """
    step: Step = {
        "description": description,
        "current_vertex": current_vertex,
        "selected_edge": selected_edge,
        "visited": sorted(list(visited)) if visited else [],
        "fringe": fringe if fringe else [],
        "tree_edges": tree_edges if tree_edges else [],
    }

    if distances is not None:
        step["distances"] = {v: _safe_number(d) for v, d in sorted(distances.items())}

    return step


def build_shortest_path_tree_edges(
    previous: Dict[Vertex, Optional[Vertex]],
    previous_edge_weight: Dict[Vertex, Optional[Weight]],
) -> List[TreeEdge]:
    """
    Build edge list for the current shortest-path tree.

    For Dijkstra, previous[v] is the predecessor of v on the shortest path from
    the source. previous_edge_weight[v] stores the actual edge weight from
    previous[v] to v.
    """
    edges: List[TreeEdge] = []
    for v in sorted(previous.keys(), key=str):
        parent = previous[v]
        if parent is not None:
            edges.append({
                "from": parent,
                "to": v,
                "weight": previous_edge_weight[v],
            })
    return edges


def serialize_result(result: AlgorithmResult) -> Dict[str, Any]:
    """Convert AlgorithmResult into JSON-safe dictionary."""
    data = asdict(result)

    if data.get("distances") is not None:
        data["distances"] = {k: _safe_number(v) for k, v in data["distances"].items()}

    return data


# =============================================================================
# Dijkstra's shortest-path algorithm
# =============================================================================

def dijkstra_binary_heap(graph: Graph, source: Vertex, record_steps: bool = True) -> AlgorithmResult:
    """
    Dijkstra using a binary heap fringe.

    Input:
        - Weighted graph with non-negative edge weights
        - Source vertex

    Output:
        - Shortest distance from source to every vertex
        - Predecessor map for shortest-path tree
        - Runtime
        - Optional step trace

    Complexity with adjacency list and binary heap:
        Time:  O((V + E) log V), often written as O(E log V) for connected graphs
        Space: O(V + E)
    """
    graph.validate_vertex_exists(source)
    graph.validate_no_negative_edges()

    start_time = time.perf_counter()

    distances: Dict[Vertex, Weight] = {v: math.inf for v in graph.vertices}
    previous: Dict[Vertex, Optional[Vertex]] = {v: None for v in graph.vertices}
    previous_edge_weight: Dict[Vertex, Optional[Weight]] = {v: None for v in graph.vertices}
    visited: Set[Vertex] = set()
    steps: List[Step] = []

    distances[source] = 0

    fringe = BinaryHeapFringe()
    fringe.push(0, source, None)

    if record_steps:
        steps.append(make_step(
            description=f"Initialize source {source} with distance 0.",
            current_vertex=source,
            visited=visited,
            fringe=fringe.snapshot(),
            tree_edges=[],
            distances=distances,
        ))

    while not fringe.is_empty():
        current_distance, u, _ = fringe.pop_min()

        # Lazy-heap stale entry checks.
        if u in visited:
            continue
        if current_distance > distances[u]:
            continue

        visited.add(u)

        if record_steps:
            steps.append(make_step(
                description=f"Extract-min selects vertex {u} with shortest known distance {current_distance}.",
                current_vertex=u,
                visited=visited,
                fringe=fringe.snapshot(),
                tree_edges=build_shortest_path_tree_edges(previous, previous_edge_weight),
                distances=distances,
            ))

        for v, weight in graph.neighbors(u):
            if v in visited:
                continue

            candidate_distance = distances[u] + weight

            # Relaxation step: improve the best known distance to v.
            if candidate_distance < distances[v]:
                distances[v] = candidate_distance
                previous[v] = u
                previous_edge_weight[v] = weight
                fringe.push(candidate_distance, v, u)

                if record_steps:
                    steps.append(make_step(
                        description=(
                            f"Relax edge {u}->{v} with weight {weight}. "
                            f"Update distance of {v} to {candidate_distance}."
                        ),
                        current_vertex=u,
                        selected_edge={"from": u, "to": v, "weight": weight},
                        visited=visited,
                        fringe=fringe.snapshot(),
                        tree_edges=build_shortest_path_tree_edges(previous, previous_edge_weight),
                        distances=distances,
                    ))

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return AlgorithmResult(
        algorithm="Dijkstra",
        fringe_type="Binary Heap",
        source_or_start=source,
        vertices=graph.vertex_count(),
        edges=graph.edge_count(),
        runtime_ms=runtime_ms,
        distances=distances,
        previous=previous,
        shortest_path_tree_edges=build_shortest_path_tree_edges(previous, previous_edge_weight),
        steps=steps if record_steps else None,
    )


def dijkstra_linked_list(graph: Graph, source: Vertex, record_steps: bool = True) -> AlgorithmResult:
    """
    Dijkstra using a linked-list fringe.

    The algorithm is the same greedy shortest-path algorithm as the heap version,
    but extract-min scans the whole fringe linearly.

    Complexity with adjacency list and linked-list fringe:
        Time:  O(V^2 + E)
        Space: O(V + E)
    """
    graph.validate_vertex_exists(source)
    graph.validate_no_negative_edges()

    start_time = time.perf_counter()

    distances: Dict[Vertex, Weight] = {v: math.inf for v in graph.vertices}
    previous: Dict[Vertex, Optional[Vertex]] = {v: None for v in graph.vertices}
    previous_edge_weight: Dict[Vertex, Optional[Weight]] = {v: None for v in graph.vertices}
    visited: Set[Vertex] = set()
    steps: List[Step] = []

    distances[source] = 0

    fringe = LinkedListFringe()
    fringe.push_or_update(0, source, None)

    if record_steps:
        steps.append(make_step(
            description=f"Initialize source {source} with distance 0.",
            current_vertex=source,
            visited=visited,
            fringe=fringe.snapshot(),
            tree_edges=[],
            distances=distances,
        ))

    while not fringe.is_empty():
        current_distance, u, _ = fringe.pop_min()

        if u in visited:
            continue

        visited.add(u)

        if record_steps:
            steps.append(make_step(
                description=(
                    f"Linked-list scan selects vertex {u} with minimum tentative "
                    f"distance {current_distance}."
                ),
                current_vertex=u,
                visited=visited,
                fringe=fringe.snapshot(),
                tree_edges=build_shortest_path_tree_edges(previous, previous_edge_weight),
                distances=distances,
            ))

        for v, weight in graph.neighbors(u):
            if v in visited:
                continue

            candidate_distance = distances[u] + weight

            if candidate_distance < distances[v]:
                distances[v] = candidate_distance
                previous[v] = u
                previous_edge_weight[v] = weight
                fringe.push_or_update(candidate_distance, v, u)

                if record_steps:
                    steps.append(make_step(
                        description=(
                            f"Relax edge {u}->{v} with weight {weight}. "
                            f"Update distance of {v} to {candidate_distance}."
                        ),
                        current_vertex=u,
                        selected_edge={"from": u, "to": v, "weight": weight},
                        visited=visited,
                        fringe=fringe.snapshot(),
                        tree_edges=build_shortest_path_tree_edges(previous, previous_edge_weight),
                        distances=distances,
                    ))

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return AlgorithmResult(
        algorithm="Dijkstra",
        fringe_type="Linked List",
        source_or_start=source,
        vertices=graph.vertex_count(),
        edges=graph.edge_count(),
        runtime_ms=runtime_ms,
        distances=distances,
        previous=previous,
        shortest_path_tree_edges=build_shortest_path_tree_edges(previous, previous_edge_weight),
        steps=steps if record_steps else None,
    )


# =============================================================================
# Prim's minimum-spanning-tree algorithm
# =============================================================================

def _validate_prim_input(graph: Graph, start: Vertex) -> None:
    graph.validate_vertex_exists(start)
    if graph.directed:
        raise ValueError("Prim's algorithm requires an undirected graph.")
    if not graph.is_connected_undirected():
        raise ValueError("Prim's algorithm requires a connected undirected graph.")


def prim_binary_heap(graph: Graph, start: Vertex, record_steps: bool = True) -> AlgorithmResult:
    """
    Prim using a binary heap fringe.

    Input:
        - Connected, undirected, weighted graph
        - Start vertex

    Output:
        - MST edges
        - Total MST weight
        - Runtime
        - Optional step trace

    Complexity with adjacency list and binary heap:
        Time:  O(E log V)
        Space: O(V + E)
    """
    _validate_prim_input(graph, start)

    start_time = time.perf_counter()

    visited: Set[Vertex] = set()
    mst_edges: List[TreeEdge] = []
    total_weight: Weight = 0
    steps: List[Step] = []

    fringe = BinaryHeapFringe()
    fringe.push(0, start, None)

    if record_steps:
        steps.append(make_step(
            description=f"Initialize Prim's algorithm at start vertex {start}.",
            current_vertex=start,
            visited=visited,
            fringe=fringe.snapshot(),
            tree_edges=mst_edges,
        ))

    while not fringe.is_empty() and len(visited) < graph.vertex_count():
        edge_weight, u, parent = fringe.pop_min()

        # Lazy heap: multiple candidate edges may exist for the same vertex.
        if u in visited:
            continue

        visited.add(u)

        selected_edge = None
        if parent is not None:
            selected_edge = {"from": parent, "to": u, "weight": edge_weight}
            mst_edges.append(selected_edge)
            total_weight += edge_weight

        if record_steps:
            steps.append(make_step(
                description=(
                    f"Add vertex {u} to the MST"
                    + (f" using edge {parent}-{u} with weight {edge_weight}." if parent is not None else ".")
                ),
                current_vertex=u,
                selected_edge=selected_edge,
                visited=visited,
                fringe=fringe.snapshot(),
                tree_edges=list(mst_edges),
            ))

        for v, weight in graph.neighbors(u):
            if v not in visited:
                fringe.push(weight, v, u)

                if record_steps:
                    steps.append(make_step(
                        description=f"Consider candidate edge {u}-{v} with weight {weight}.",
                        current_vertex=u,
                        selected_edge={"from": u, "to": v, "weight": weight},
                        visited=visited,
                        fringe=fringe.snapshot(),
                        tree_edges=list(mst_edges),
                    ))

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return AlgorithmResult(
        algorithm="Prim",
        fringe_type="Binary Heap",
        source_or_start=start,
        vertices=graph.vertex_count(),
        edges=graph.edge_count(),
        runtime_ms=runtime_ms,
        mst_edges=mst_edges,
        total_mst_weight=total_weight,
        steps=steps if record_steps else None,
    )


def prim_linked_list(graph: Graph, start: Vertex, record_steps: bool = True) -> AlgorithmResult:
    """
    Prim using a linked-list fringe.

    This version keeps only the best currently known connecting edge for each
    unvisited vertex in the fringe. Extract-min scans the fringe linearly.

    Complexity with adjacency list and linked-list fringe:
        Time:  O(V^2 + E)
        Space: O(V + E)
    """
    _validate_prim_input(graph, start)

    start_time = time.perf_counter()

    visited: Set[Vertex] = set()
    mst_edges: List[TreeEdge] = []
    total_weight: Weight = 0
    steps: List[Step] = []

    fringe = LinkedListFringe()
    fringe.push_or_update(0, start, None)

    if record_steps:
        steps.append(make_step(
            description=f"Initialize Prim's algorithm at start vertex {start}.",
            current_vertex=start,
            visited=visited,
            fringe=fringe.snapshot(),
            tree_edges=mst_edges,
        ))

    while not fringe.is_empty() and len(visited) < graph.vertex_count():
        edge_weight, u, parent = fringe.pop_min()

        if u in visited:
            continue

        visited.add(u)

        selected_edge = None
        if parent is not None:
            selected_edge = {"from": parent, "to": u, "weight": edge_weight}
            mst_edges.append(selected_edge)
            total_weight += edge_weight

        if record_steps:
            steps.append(make_step(
                description=(
                    f"Linked-list scan adds vertex {u} to the MST"
                    + (f" using edge {parent}-{u} with weight {edge_weight}." if parent is not None else ".")
                ),
                current_vertex=u,
                selected_edge=selected_edge,
                visited=visited,
                fringe=fringe.snapshot(),
                tree_edges=list(mst_edges),
            ))

        for v, weight in graph.neighbors(u):
            if v not in visited:
                fringe.push_or_update(weight, v, u)

                if record_steps:
                    steps.append(make_step(
                        description=f"Update/consider candidate edge {u}-{v} with weight {weight}.",
                        current_vertex=u,
                        selected_edge={"from": u, "to": v, "weight": weight},
                        visited=visited,
                        fringe=fringe.snapshot(),
                        tree_edges=list(mst_edges),
                    ))

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return AlgorithmResult(
        algorithm="Prim",
        fringe_type="Linked List",
        source_or_start=start,
        vertices=graph.vertex_count(),
        edges=graph.edge_count(),
        runtime_ms=runtime_ms,
        mst_edges=mst_edges,
        total_mst_weight=total_weight,
        steps=steps if record_steps else None,
    )


# =============================================================================
# Sample and generated graphs
# =============================================================================

def create_sample_graph() -> Graph:
    """
    Create a small graph with known expected results.

    This graph is useful for:
        - correctness testing
        - screenshots
        - report explanation
        - manual step-by-step trace

    Undirected edges:
        A-B 4
        A-C 2
        B-C 1
        B-D 5
        C-D 8
        C-E 10
        D-E 2
        D-F 6
        E-F 3

    Expected Dijkstra distances from A:
        A: 0
        B: 3  via A-C-B
        C: 2  via A-C
        D: 8  via A-C-B-D
        E: 10 via A-C-B-D-E
        F: 13 via A-C-B-D-E-F

    Expected MST total weight:
        13
    """
    graph = Graph(directed=False)
    edges = [
        ("A", "B", 4),
        ("A", "C", 2),
        ("B", "C", 1),
        ("B", "D", 5),
        ("C", "D", 8),
        ("C", "E", 10),
        ("D", "E", 2),
        ("D", "F", 6),
        ("E", "F", 3),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def create_disconnected_graph() -> Graph:
    """Used to prove Prim validation rejects disconnected graphs."""
    graph = Graph(directed=False)
    graph.add_edge("A", "B", 1)
    graph.add_edge("C", "D", 2)
    return graph


def create_equal_weight_graph() -> Graph:
    """
    Graph with many equal edge weights.

    This tests tie handling. There can be more than one valid MST, but the total
    weight should still be correct.
    """
    graph = Graph(directed=False)
    graph.add_edge("A", "B", 1)
    graph.add_edge("B", "C", 1)
    graph.add_edge("C", "D", 1)
    graph.add_edge("D", "A", 1)
    graph.add_edge("A", "C", 2)
    graph.add_edge("B", "D", 2)
    return graph


def generate_connected_random_graph(
    num_vertices: int,
    extra_edges: int,
    max_weight: int = 100,
    seed: Optional[int] = None,
) -> Graph:
    """
    Generate a connected undirected random graph.

    Method:
        1. Add all vertices.
        2. Add a chain 0-1-2-...-(n-1) to guarantee connectivity.
        3. Add random extra edges.

    This is good for Prim because the graph is guaranteed to be connected.
    """
    if num_vertices <= 0:
        raise ValueError("num_vertices must be positive.")

    rng = random.Random(seed)
    graph = Graph(directed=False)
    vertices = [str(i) for i in range(num_vertices)]

    for v in vertices:
        graph.add_vertex(v)

    edge_set: Set[Tuple[Vertex, Vertex]] = set()

    def add_unique_edge(u: Vertex, v: Vertex, weight: Weight) -> bool:
        if u == v:
            return False
        key = tuple(sorted((u, v)))
        if key in edge_set:
            return False
        graph.add_edge(u, v, weight)
        edge_set.add(key)
        return True

    # Connectivity chain.
    for i in range(num_vertices - 1):
        add_unique_edge(vertices[i], vertices[i + 1], rng.randint(1, max_weight))

    max_possible_edges = num_vertices * (num_vertices - 1) // 2
    current_edges = graph.edge_count()
    target_edges = min(current_edges + extra_edges, max_possible_edges)

    attempts = 0
    max_attempts = max(1000, target_edges * 20)

    while graph.edge_count() < target_edges and attempts < max_attempts:
        attempts += 1
        u = rng.choice(vertices)
        v = rng.choice(vertices)
        add_unique_edge(u, v, rng.randint(1, max_weight))

    return graph


def generate_sparse_graph(num_vertices: int, edge_factor: int = 3, seed: Optional[int] = None) -> Graph:
    """
    Generate sparse graph where E is approximately edge_factor * V.

    Because the connectivity chain already has V-1 edges, we add enough extra
    edges to reach about edge_factor * V total edges.
    """
    target_edges = edge_factor * num_vertices
    extra_edges = max(0, target_edges - (num_vertices - 1))
    return generate_connected_random_graph(num_vertices, extra_edges, seed=seed)


def generate_dense_graph(num_vertices: int, density: float = 0.25, seed: Optional[int] = None) -> Graph:
    """
    Generate dense-ish graph.

    density is the fraction of possible undirected edges to include.
    For example, density=0.50 means about 50% of all possible undirected edges,
    which is approximately E = V^2 / 4.
    """
    if not 0 < density <= 1:
        raise ValueError("density must be in the range (0, 1].")

    max_possible_edges = num_vertices * (num_vertices - 1) // 2
    target_edges = int(max_possible_edges * density)
    target_edges = max(target_edges, num_vertices - 1)
    extra_edges = target_edges - (num_vertices - 1)
    return generate_connected_random_graph(num_vertices, extra_edges, seed=seed)


# =============================================================================
# Correctness tests and edge-case tests
# =============================================================================

def assert_distances_equal(actual: Dict[Vertex, Weight], expected: Dict[Vertex, Weight]) -> None:
    for vertex, expected_value in expected.items():
        actual_value = actual.get(vertex)
        if actual_value != expected_value:
            raise AssertionError(
                f"Distance mismatch for {vertex}: expected {expected_value}, got {actual_value}"
            )


def run_correctness_tests() -> None:
    """
    Run correctness tests on a known graph.

    These tests are useful to mention in the final report under Testing Data.
    """
    print("\nRunning correctness tests...")

    graph = create_sample_graph()
    expected_distances = {
        "A": 0,
        "B": 3,
        "C": 2,
        "D": 8,
        "E": 10,
        "F": 13,
    }

    dijkstra_heap_result = dijkstra_binary_heap(graph, "A", record_steps=False)
    dijkstra_list_result = dijkstra_linked_list(graph, "A", record_steps=False)

    assert_distances_equal(dijkstra_heap_result.distances or {}, expected_distances)
    assert_distances_equal(dijkstra_list_result.distances or {}, expected_distances)

    prim_heap_result = prim_binary_heap(graph, "A", record_steps=False)
    prim_list_result = prim_linked_list(graph, "A", record_steps=False)

    if prim_heap_result.total_mst_weight != 13:
        raise AssertionError(f"Prim heap MST expected weight 13, got {prim_heap_result.total_mst_weight}")

    if prim_list_result.total_mst_weight != 13:
        raise AssertionError(f"Prim linked-list MST expected weight 13, got {prim_list_result.total_mst_weight}")

    print("  Passed: Dijkstra heap distances match expected values.")
    print("  Passed: Dijkstra linked-list distances match expected values.")
    print("  Passed: Prim heap MST total weight is 13.")
    print("  Passed: Prim linked-list MST total weight is 13.")


def run_edge_case_tests() -> None:
    """Run tests for invalid and edge-case inputs."""
    print("\nRunning edge-case tests...")

    # 1. Single-vertex graph.
    single = Graph(directed=False)
    single.add_vertex("A")

    d_single = dijkstra_binary_heap(single, "A", record_steps=False)
    p_single = prim_binary_heap(single, "A", record_steps=False)

    if d_single.distances != {"A": 0}:
        raise AssertionError("Single-vertex Dijkstra failed.")
    if p_single.total_mst_weight != 0 or p_single.mst_edges != []:
        raise AssertionError("Single-vertex Prim failed.")

    print("  Passed: Single-vertex graph works for Dijkstra and Prim.")

    # 2. Disconnected graph should be rejected by Prim.
    disconnected = create_disconnected_graph()
    try:
        prim_binary_heap(disconnected, "A", record_steps=False)
        raise AssertionError("Prim should reject disconnected graphs but did not.")
    except ValueError as exc:
        if "connected" not in str(exc):
            raise

    print("  Passed: Prim rejects disconnected graph.")

    # 3. Negative edge should be rejected.
    negative = Graph(directed=False)
    try:
        negative.add_edge("A", "B", -5)
        raise AssertionError("Graph should reject negative edge weights but did not.")
    except ValueError:
        pass

    print("  Passed: Negative edge weights are rejected.")

    # 4. Equal-weight graph should still return valid MST total.
    equal = create_equal_weight_graph()
    p_equal_heap = prim_binary_heap(equal, "A", record_steps=False)
    p_equal_list = prim_linked_list(equal, "A", record_steps=False)

    if p_equal_heap.total_mst_weight != 3:
        raise AssertionError(f"Equal-weight Prim heap expected total 3, got {p_equal_heap.total_mst_weight}")
    if p_equal_list.total_mst_weight != 3:
        raise AssertionError(f"Equal-weight Prim linked-list expected total 3, got {p_equal_list.total_mst_weight}")

    print("  Passed: Equal-weight graph MST total is correct.")

    # 5. Random graph consistency: both fringe versions should agree.
    random_graph = generate_sparse_graph(30, edge_factor=3, seed=123)

    dh = dijkstra_binary_heap(random_graph, "0", record_steps=False)
    dl = dijkstra_linked_list(random_graph, "0", record_steps=False)
    if dh.distances != dl.distances:
        raise AssertionError("Dijkstra heap and linked-list results differ on random graph.")

    ph = prim_binary_heap(random_graph, "0", record_steps=False)
    pl = prim_linked_list(random_graph, "0", record_steps=False)
    if ph.total_mst_weight != pl.total_mst_weight:
        raise AssertionError("Prim heap and linked-list MST weights differ on random graph.")

    print("  Passed: Heap and linked-list versions agree on a random graph.")


# =============================================================================
# Benchmarking
# =============================================================================

AlgorithmFunction = Callable[[Graph, Vertex, bool], AlgorithmResult]


def benchmark_algorithm(
    func: AlgorithmFunction,
    graph: Graph,
    start: Vertex,
    runs: int = 5,
) -> float:
    """
    Measure average runtime for one algorithm on one graph.

    record_steps=False is important for benchmarks because step recording is for
    visualization and would add extra overhead unrelated to the core algorithm.
    """
    timings: List[float] = []
    for _ in range(runs):
        result = func(graph, start, False)
        timings.append(result.runtime_ms)
    return sum(timings) / len(timings)


def run_benchmarks(
    sizes: Iterable[int] = (10, 25, 50, 100, 200),
    runs: int = 5,
    seed: int = 42,
    dense_density: float = 0.50,
) -> List[Dict[str, Any]]:
    """
    Run benchmark suite for sparse and dense graphs.

    The resulting rows are ready to export as CSV and use in the report.
    """
    print("\nRunning benchmarks...")
    print(f"  sizes={list(sizes)}, runs={runs}, seed={seed}, dense_density={dense_density}")

    algorithms: List[Tuple[str, str, AlgorithmFunction]] = [
        ("Dijkstra", "Binary Heap", dijkstra_binary_heap),
        ("Dijkstra", "Linked List", dijkstra_linked_list),
        ("Prim", "Binary Heap", prim_binary_heap),
        ("Prim", "Linked List", prim_linked_list),
    ]

    results: List[Dict[str, Any]] = []

    for size in sizes:
        # Use deterministic but different seeds per graph type/size.
        sparse_graph = generate_sparse_graph(size, edge_factor=3, seed=seed + size)
        dense_graph = generate_dense_graph(size, density=dense_density, seed=seed + 10_000 + size)

        for graph_type, graph in [("Sparse", sparse_graph), ("Dense", dense_graph)]:
            start = "0"
            print(f"  Benchmarking {graph_type} graph: V={graph.vertex_count()}, E={graph.edge_count()}")

            for algorithm_name, fringe_type, func in algorithms:
                avg_ms = benchmark_algorithm(func, graph, start, runs=runs)
                row = {
                    "graph_type": graph_type,
                    "vertices": graph.vertex_count(),
                    "edges": graph.edge_count(),
                    "algorithm": algorithm_name,
                    "fringe": fringe_type,
                    "avg_runtime_ms": round(avg_ms, 6),
                }
                results.append(row)
                print(
                    f"    {algorithm_name:9s} | {fringe_type:11s} | "
                    f"avg {avg_ms:.6f} ms"
                )

    return results


def export_benchmark_csv(results: List[Dict[str, Any]], path: str) -> None:
    """Export benchmark rows to CSV for report charts."""
    fieldnames = ["graph_type", "vertices", "edges", "algorithm", "fringe", "avg_runtime_ms"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nBenchmark CSV written to: {path}")


# =============================================================================
# Printing and exporting demo data
# =============================================================================

def print_graph_summary(graph: Graph) -> None:
    print(f"Graph directed: {graph.directed}")
    print(f"Vertices ({graph.vertex_count()}): {', '.join(graph.sorted_vertices())}")
    print(f"Edges ({graph.edge_count()}):")
    for u, v, w in graph.to_edge_list():
        arrow = "->" if graph.directed else "-"
        print(f"  {u} {arrow} {v}  weight={w}")


def print_dijkstra_result(result: AlgorithmResult) -> None:
    print(f"\n{result.algorithm} using {result.fringe_type}")
    print(f"Source: {result.source_or_start}")
    print(f"Runtime: {result.runtime_ms:.6f} ms")
    print("Shortest distances:")

    assert result.distances is not None
    for vertex in sorted(result.distances.keys(), key=str):
        distance = result.distances[vertex]
        print(f"  {vertex}: {_safe_number(distance)}")

    print("Shortest-path tree edges:")
    for edge in result.shortest_path_tree_edges or []:
        print(f"  {edge['from']} -> {edge['to']}  weight={edge['weight']}")


def print_prim_result(result: AlgorithmResult) -> None:
    print(f"\n{result.algorithm} using {result.fringe_type}")
    print(f"Start: {result.source_or_start}")
    print(f"Runtime: {result.runtime_ms:.6f} ms")
    print(f"Total MST weight: {result.total_mst_weight}")
    print("MST edges:")
    for edge in result.mst_edges or []:
        print(f"  {edge['from']} - {edge['to']}  weight={edge['weight']}")


def run_sample_demo() -> None:
    """Run all four implementations on the sample graph and print results."""
    print("\nSample graph demo")
    print("=" * 80)

    graph = create_sample_graph()
    print_graph_summary(graph)

    d_heap = dijkstra_binary_heap(graph, "A", record_steps=True)
    d_list = dijkstra_linked_list(graph, "A", record_steps=True)
    p_heap = prim_binary_heap(graph, "A", record_steps=True)
    p_list = prim_linked_list(graph, "A", record_steps=True)

    print_dijkstra_result(d_heap)
    print_dijkstra_result(d_list)
    print_prim_result(p_heap)
    print_prim_result(p_list)

    print("\nStep counts, useful for animation/screenshot evidence:")
    print(f"  Dijkstra Binary Heap steps: {len(d_heap.steps or [])}")
    print(f"  Dijkstra Linked List steps: {len(d_list.steps or [])}")
    print(f"  Prim Binary Heap steps: {len(p_heap.steps or [])}")
    print(f"  Prim Linked List steps: {len(p_list.steps or [])}")


def export_sample_steps(output_dir: str) -> None:
    """
    Export sample algorithm traces as JSON.

    These JSON files are not animations themselves, but they provide all major
    iteration states needed by a UI to render animations or screenshots.
    """
    os.makedirs(output_dir, exist_ok=True)

    graph = create_sample_graph()
    results = [
        dijkstra_binary_heap(graph, "A", record_steps=True),
        dijkstra_linked_list(graph, "A", record_steps=True),
        prim_binary_heap(graph, "A", record_steps=True),
        prim_linked_list(graph, "A", record_steps=True),
    ]

    for result in results:
        filename = f"{result.algorithm.lower()}_{result.fringe_type.lower().replace(' ', '_')}_steps.json"
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serialize_result(result), f, indent=2)
        print(f"Exported step trace: {path}")


# =============================================================================
# CLI
# =============================================================================

def parse_sizes(value: str) -> List[int]:
    """Parse comma-separated sizes, e.g. '10,25,50,100'."""
    try:
        sizes = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from exc

    if any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError("all sizes must be positive")

    return sizes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Graph Algorithms Final Project: Dijkstra and Prim with heap/list fringes."
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "test", "benchmark", "export-steps", "all"],
        default="demo",
        help="What to run. Default: demo",
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=[10, 25, 50, 100, 200],
        help="Comma-separated graph sizes for benchmarks. Default: 10,25,50,100,200",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs to average for each benchmark. Default: 5",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for benchmark graph generation. Default: 42",
    )
    parser.add_argument(
        "--dense-density",
        type=float,
        default=0.50,
        help="Density for dense benchmark graphs. Default: 0.50. This is approximately E = V^2 / 4 for undirected graphs.",
    )
    parser.add_argument(
        "--csv",
        default="benchmark_results.csv",
        help="Output CSV path for benchmark mode. Default: benchmark_results.csv",
    )
    parser.add_argument(
        "--steps-dir",
        default="sample_steps",
        help="Output directory for exported sample step traces. Default: sample_steps",
    )

    args = parser.parse_args()

    if args.runs <= 0:
        raise ValueError("--runs must be positive")

    if args.mode in ("demo", "all"):
        run_sample_demo()

    if args.mode in ("test", "all"):
        run_correctness_tests()
        run_edge_case_tests()
        print("\nAll tests passed.")

    if args.mode in ("benchmark", "all"):
        results = run_benchmarks(
            sizes=args.sizes,
            runs=args.runs,
            seed=args.seed,
            dense_density=args.dense_density,
        )
        export_benchmark_csv(results, args.csv)

    if args.mode in ("export-steps", "all"):
        export_sample_steps(args.steps_dir)


if __name__ == "__main__":
    main()
