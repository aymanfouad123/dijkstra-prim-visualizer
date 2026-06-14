from collections import defaultdict
import heapq
import itertools
import math
import time


# ============================================================
# GRAPH
# ============================================================

class Graph:
    """
    Weighted graph represented using an adjacency list.
    Adjacency list representation:
        A: [(B, 4), (C, 2)]
        B: [(A, 4), (C, 1), (D, 5)]
        C: [(A, 2), (B, 1)]
    Dijkstra works on graphs with non-negative edge weights.
    """

    def __init__(self, directed=False):
        self.directed = directed
        self.adj = defaultdict(list)

    def add_vertex(self, v):
        """Add vertex if it does not already exist."""
        if v not in self.adj:
            self.adj[v] = []

    def add_edge(self, u, v, weight):
        """
        Add a weighted edge.
        For undirected graphs, we can store the edges twice: u -> v and v -> u.
        """
        if weight < 0:
            raise ValueError("Negative weights are not allowed for Dijkstra's algorithm.")

        self.add_vertex(u)
        self.add_vertex(v)

        self.adj[u].append((v, weight))

        if not self.directed:
            self.adj[v].append((u, weight))

    def neighbors(self, v):
        """Return neighbors of vertex v as (neighbor, weight) pairs."""
        return self.adj[v]

    def vertices(self):
        """Return all vertices in the graph."""
        return list(self.adj.keys())

    def has_vertex(self, v):
        """Check whether vertex exists."""
        return v in self.adj

    def validate_source(self, source):
        """Dijkstra needs a valid source vertex."""
        if not self.has_vertex(source):
            raise ValueError(f"Source vertex '{source}' does not exist.")

    def edge_count(self):
        """Return number of edges."""
        total = sum(len(edges) for edges in self.adj.values())
        if self.directed:
            return total
        return total // 2 # Since we store the edges twice for undirected graphs.

    def print_graph(self):
        """Print the graph in adjacency-list form."""
        print("\nAdjacency list:")
        for vertex in sorted(self.adj.keys()):
            formatted_edges = ", ".join(
                f"({neighbor}, {weight})" for neighbor, weight in self.adj[vertex]
            )
            print(f"  {vertex}: [{formatted_edges}]")

# ============================================================
# BINARY HEAP FRINGE
# ============================================================

class BinaryHeapFringe:
    """
    Heap Fringe Implementation. 
    Fringe: set of candidate vertices that may be visited next.

    Here we choose the minimum priority item from our heap.

    Extraction complexity: pop_min = O(log V)

    Implementation detail:
    We use lazy insertion. If a better distance is found for a vertex, we push another entry. When an old/stale entry is popped later, Dijkstra skips it.
    """

    def __init__(self):
        self.heap = []
        self.counter = itertools.count()  # Tie-breaker so vertices do not need to be comparable.
        
    def push(self, priority, vertex, parent=None):
        """Push a candidate vertex into the heap."""
        count = next(self.counter)
        heapq.heappush(self.heap, (priority, count, vertex))

    def pop_min(self):
        """Popping the vertex with the smallest priority."""
        priority, _, vertex = heapq.heappop(self.heap)
        return priority, vertex

    def is_empty(self):
        return len(self.heap) == 0

    def snapshot(self):
        """
        Return a readable copy of the fringe contents. 
        Sorted only for display purposes.
        """
        return [
            {"vertex": vertex, "priority": priority}
            for priority, _, vertex in sorted(self.heap)
        ]


# ============================================================
# LINKED-LIST FRINGE
# ============================================================

class LinkedListFringe:
    """
    LinkedList Fringe Implementation.

    Here the items are stored without heap ordering, so extract-min requires scanning through all candidates.
    Therefore, pop_min = O(V).

    We can see that this will be slower than the binary heap.
    """

    def __init__(self):
        self.items = []

    def push_or_update(self, priority, vertex):
        """
        Add vertex if it is not present.
        If it is already present, update only if the new priority is smaller.
        """
        for item in self.items:
            if item["vertex"] == vertex:
                if priority < item["priority"]:
                    item["priority"] = priority
                return

        self.items.append({"priority": priority, "vertex": vertex})

    def pop_min(self):
        """Find and remove the minimum-priority candidate by scanning the list."""
        if not self.items:
            raise IndexError("Cannot pop from an empty linked-list fringe.")

        min_index = 0
        
        for i in range(1, len(self.items)):
            current = self.items[i]
            best = self.items[min_index]

            # Tie-break by vertex label for stable, deterministic output.
            if (current["priority"], current["vertex"]) < (best["priority"], best["vertex"]):
                min_index = i

        item = self.items.pop(min_index)
        return item["priority"], item["vertex"]

    def is_empty(self):
        return len(self.items) == 0

    def snapshot(self):
        """
        Returning a readable copy of the fringe contents. 
        Sorted only for display purposes.
        """
        return sorted(self.items, key=lambda item: (item["priority"], item["vertex"]))


# ============================================================
# DIJKSTRA HELPERS
# ============================================================

def reconstruct_path(previous, source, target):
    """
    Reconstruct shortest path from source to target using the previous map.

    If target is unreachable, returns an empty list.
    
    Example:
    previous["F"] = "E"
    previous["E"] = "D"
    previous["D"] = "B"
    and so on.
    
    This helps reconstruct the path and walk backwards.
    """
    if source == target:
        return [source]

    path = []
    current = target

    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse() # Reverse to get the path from source to target.

    if not path or path[0] != source:
        return []

    return path


def shortest_path_tree_edges(previous, edge_to_parent):
    """
    Convert predecessor map into shortest-path tree edges.

    For every vertex v with previous[v] = u, include edge u -> v.
    """

    tree_edges = []

    for vertex, parent in previous.items():
        if parent is not None:
            tree_edges.append((parent, vertex, edge_to_parent[vertex]))

    return tree_edges 


def make_step(
    message,
    current_vertex,
    distances,
    previous,
    fringe_snapshot,
    visited,
    edge_to_parent=None,
    selected_edge=None,
):
    """
    Store one major iteration state for the visualizer.

    ``selected_edge`` is set on relaxation steps. ``tree_edges`` is derived from
    the current predecessor map so the UI can highlight the evolving shortest-path tree.
    """
    if edge_to_parent is None:
        edge_to_parent = {}

    step = {
        "message": message,
        "current_vertex": current_vertex,
        "distances": dict(distances),
        "previous": dict(previous),
        "fringe": fringe_snapshot,
        "visited": sorted(visited),
        "tree_edges": shortest_path_tree_edges(previous, edge_to_parent),
    }

    if selected_edge is not None:
        step["selected_edge"] = selected_edge

    return step


# ============================================================
# DIJKSTRA USING BINARY HEAP
# ============================================================

"""
Complexity Overview:

Dijkstra using binary heap.

Time:
    O((V + E) log V)

Space:
    O(V + E)

Reason:
    Each edge relaxation may cause a heap insertion.
    Heap operations cost O(log V).
"""
def dijkstra_binary_heap(graph, source, record_steps=True):
    graph.validate_source(source)
    
    start_time = time.perf_counter()

    distances = {v: math.inf for v in graph.vertices()}
    previous = {v: None for v in graph.vertices()}
    edge_to_parent = {v: None for v in graph.vertices()}
    visited = set()
    steps = []

    distances[source] = 0

    fringe = BinaryHeapFringe()
    fringe.push(0, source)

    if record_steps:
        steps.append(
            make_step(
                message=f"Initialize source {source} with distance 0.",
                current_vertex=source,
                distances=distances,
                previous=previous,
                fringe_snapshot=fringe.snapshot(),
                visited=visited,
                edge_to_parent=edge_to_parent,
            )
        )

    # Main loop
    while not fringe.is_empty():
        current_distance, current_vertex = fringe.pop_min()

        # Sometimes the heap may contain an old worse entry.
        if current_vertex in visited:
            continue
        if current_distance > distances[current_vertex]:
            continue

        visited.add(current_vertex)
        
        if record_steps:
            steps.append(
                make_step(
                    message=f"Visit {current_vertex}; it has the smallest tentative distance {current_distance}.",
                    current_vertex=current_vertex,
                    distances=distances,
                    previous=previous,
                    fringe_snapshot=fringe.snapshot(),
                    visited=visited,
                    edge_to_parent=edge_to_parent,
                )
            )

        for neighbor, weight in graph.neighbors(current_vertex):
            if neighbor in visited:
                continue

            new_distance = distances[current_vertex] + weight

            # Relaxation step: if going through u improves distance to v, update it.
            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                previous[neighbor] = current_vertex
                edge_to_parent[neighbor] = weight
                
                fringe.push(new_distance, neighbor)

                if record_steps:
                    steps.append(
                        make_step(
                            message=(
                                f"Relax edge {current_vertex}->{neighbor} with weight {weight}. "
                                f"New distance to {neighbor} is {new_distance}."
                            ),
                            current_vertex=current_vertex,
                            distances=distances,
                            previous=previous,
                            fringe_snapshot=fringe.snapshot(),
                            visited=visited,
                            edge_to_parent=edge_to_parent,
                            selected_edge=(current_vertex, neighbor, weight),
                        )
                    )


    runtime_ms = (time.perf_counter() - start_time) * 1000

    return {
        "algorithm": "Dijkstra",
        "fringe": "Binary Heap",
        "source": source,
        "distances": distances,
        "previous": previous,
        "tree_edges": shortest_path_tree_edges(previous, edge_to_parent),
        "steps": steps,
        "runtime_ms": runtime_ms,
    }



# ============================================================
# DIJKSTRA WITH LINKED-LIST FRINGE
# ============================================================

"""
Complexity Overview:

Dijkstra using a linked-list style fringe.

Time:
    O(V² + E)

Space:
    O(V + E)

Reason:
    Extract-min requires scanning all fringe vertices.
"""
def dijkstra_linked_list(graph, source, record_steps=True):
    graph.validate_source(source)

    start_time = time.perf_counter()

    distances = {v: math.inf for v in graph.vertices()}
    previous = {v: None for v in graph.vertices()}
    edge_to_parent = {v: None for v in graph.vertices()}
    visited = set()
    steps = []

    distances[source] = 0

    fringe = LinkedListFringe()
    fringe.push_or_update(0, source)

    if record_steps:
        steps.append(
            make_step(
                message=f"Initialize source {source} with distance 0.",
                current_vertex=source,
                distances=distances,
                previous=previous,
                fringe_snapshot=fringe.snapshot(),
                visited=visited,
                edge_to_parent=edge_to_parent,
            )
        )


    while not fringe.is_empty():
        current_distance, current_vertex = fringe.pop_min()

        if current_vertex in visited:
            continue

        visited.add(current_vertex)

        if record_steps:
            steps.append(
                make_step(
                    message=(
                        f"Visit {current_vertex}; it was found by linearly scanning "
                        f"the linked-list fringe."
                    ),
                    current_vertex=current_vertex,
                    distances=distances,
                    previous=previous,
                    fringe_snapshot=fringe.snapshot(),
                    visited=visited,
                    edge_to_parent=edge_to_parent,
                )
            )


        for neighbor, weight in graph.neighbors(current_vertex):
            if neighbor in visited:
                continue

            new_distance = distances[current_vertex] + weight

            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                previous[neighbor] = current_vertex
                edge_to_parent[neighbor] = weight

                fringe.push_or_update(new_distance, neighbor)

                if record_steps:
                    steps.append(
                        make_step(
                            message=(
                                f"Relax edge {current_vertex}->{neighbor} with weight {weight}. "
                                f"New distance to {neighbor} is {new_distance}."
                            ),
                            current_vertex=current_vertex,
                            distances=distances,
                            previous=previous,
                            fringe_snapshot=fringe.snapshot(),
                            visited=visited,
                            edge_to_parent=edge_to_parent,
                            selected_edge=(current_vertex, neighbor, weight),
                        )
                    )

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return {
        "algorithm": "Dijkstra",
        "fringe": "Linked List",
        "source": source,
        "distances": distances,
        "previous": previous,
        "tree_edges": shortest_path_tree_edges(previous, edge_to_parent),
        "steps": steps,
        "runtime_ms": runtime_ms,
    }


# ============================================================
# SAMPLE DATA
# ============================================================

def build_sample_graph():
    """
    Sample undirected graph.

    Expected shortest distances from A:

        A = 0
        B = 3       via A -> C -> B
        C = 2       via A -> C
        D = 8       via A -> C -> B -> D
        E = 10      via A -> C -> B -> D -> E
        F = 13      via A -> C -> B -> D -> E -> F
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

    for u, v, weight in edges:
        graph.add_edge(u, v, weight)

    return graph

# ============================================================
# OUTPUT HELPERS
# ============================================================

def print_dijkstra_result(result):
    """
    Print result in a report-friendly format.
    """

    print("\n" + "=" * 70)
    print(f"{result['algorithm']} using {result['fringe']}")
    print("=" * 70)
    print(f"Source: {result['source']}")
    print(f"Runtime: {result['runtime_ms']:.6f} ms")

    print("\nShortest distances:")
    for vertex in sorted(result["distances"]):
        distance = result["distances"][vertex]
        if distance == math.inf:
            print(f"  {vertex}: infinity")
        else:
            print(f"  {vertex}: {distance}")

    print("\nShortest-path tree edges:")
    for u, v, weight in result["tree_edges"]:
        print(f"  {u} -> {v}  weight={weight}")

    print("\nPaths from source:")
    source = result["source"]

    for vertex in sorted(result["distances"]):
        path = reconstruct_path(result["previous"], source, vertex)

        if not path:
            print(f"  {source} -> {vertex}: unreachable")
        else:
            print(f"  {source} -> {vertex}: {' -> '.join(path)}")


# ============================================================
# TESTS
# ============================================================

def test_sample_graph_distances():
    """
    Check both Dijkstra versions against known expected distances.
    """

    graph = build_sample_graph()

    expected = {
        "A": 0,
        "B": 3,
        "C": 2,
        "D": 8,
        "E": 10,
        "F": 13,
    }

    heap_result = dijkstra_binary_heap(graph, "A", record_steps=False)
    list_result = dijkstra_linked_list(graph, "A", record_steps=False)

    assert heap_result["distances"] == expected
    assert list_result["distances"] == expected

    print("Passed: sample graph distances are correct for both fringe versions.")


def test_invalid_source():
    """
    Dijkstra should reject a source that is not in the graph.
    """

    graph = build_sample_graph()

    try:
        dijkstra_binary_heap(graph, "Z", record_steps=False)
        raise AssertionError("Expected invalid source to raise ValueError.")
    except ValueError:
        print("Passed: invalid source is rejected.")


def test_negative_weight_rejected():
    """
    Dijkstra does not support negative weights.
    """

    graph = Graph(directed=False)

    try:
        graph.add_edge("A", "B", -1)
        raise AssertionError("Expected negative edge to raise ValueError.")
    except ValueError:
        print("Passed: negative edge weight is rejected.")


def test_disconnected_graph():
    """
    Dijkstra can run on disconnected graphs.
    Unreachable vertices should remain at infinity.
    """

    graph = Graph(directed=False)

    graph.add_edge("A", "B", 5)
    graph.add_vertex("C")

    result = dijkstra_binary_heap(graph, "A", record_steps=False)

    assert result["distances"]["A"] == 0
    assert result["distances"]["B"] == 5
    assert result["distances"]["C"] == math.inf

    print("Passed: disconnected graph keeps unreachable vertices at infinity.")


def run_tests():
    print("\nRunning Dijkstra tests...")
    test_sample_graph_distances()
    test_invalid_source()
    test_negative_weight_rejected()
    test_disconnected_graph()
    print("All Dijkstra tests passed.")


# ============================================================
# MAIN DEMO
# ============================================================

def main():
    graph = build_sample_graph()

    print("\nDIJKSTRA DEMO")
    print("=" * 70)

    graph.print_graph()

    heap_result = dijkstra_binary_heap(graph, "A")
    list_result = dijkstra_linked_list(graph, "A")

    print_dijkstra_result(heap_result)
    print_dijkstra_result(list_result)

    print("\nStep counts:")
    print(f"  Binary heap steps: {len(heap_result['steps'])}")
    print(f"  Linked-list steps: {len(list_result['steps'])}")

    run_tests()


if __name__ == "__main__":
    main()
