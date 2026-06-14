from collections import defaultdict, deque
import heapq
import itertools
import time


# ============================================================
# GRAPH
# ============================================================

class Graph:
    """
    Weighted graph represented using an adjacency list.
    """

    def __init__(self, directed=False):
        self.directed = directed
        self.adj = defaultdict(list)

    def add_vertex(self, vertex):
        """Add vertex if it does not already exist."""
        if vertex not in self.adj:
            self.adj[vertex] = []

    def add_edge(self, u, v, weight):
        """
        Add a weighted edge.

        For undirected graphs, we store the edge twice:
            u -> v
            v -> u

        Unlike Dijkstra, Prim can work with negative edge weights.
        """

        self.add_vertex(u)
        self.add_vertex(v)

        self.adj[u].append((v, weight))

        if not self.directed:
            self.adj[v].append((u, weight))
            
    def vertices(self):
        """Return all vertices in the graph."""
        return list(self.adj.keys())

    def neighbors(self, vertex):
        """Return neighbors of vertex as (neighbor, weight) pairs."""
        return self.adj[vertex]

    def has_vertex(self, vertex):
        """Check whether vertex exists."""
        return vertex in self.adj
    
    def validate_start(self, start):
        """Prim needs a valid starting vertex."""
        if not self.has_vertex(start):
            raise ValueError(f"Start vertex '{start}' does not exist.")
        
    def edge_count(self):
        """Return number of edges."""
        total = sum(len(edges) for edges in self.adj.values())

        if self.directed:
            return total

        return total // 2 # Undirected graphs have each edge stored twice.
    
    def component_containing(self, start): 
        """Return the set of vertices in the component containing start."""
        self.validate_start(start)

        visited = set()
        queue = deque([start])

        while queue:
            vertex = queue.popleft()

            if vertex in visited:
                continue

            visited.add(vertex)

            for neighbor, _weight in self.adj[vertex]:
                if neighbor not in visited:
                    queue.append(neighbor)

        return visited
    
    def is_connected(self):
        """
        Check if the graph is connected.
        If yes, a full MST exists. If no, a full MST does not exist.
        """
        if not self.adj:
            return True

        start = next(iter(self.adj))
        component = self.component_containing(start)
        return len(component) == len(self.adj)
    
    def validate_for_prim(self, start, allow_partial=False):
        """Validate the graph for Prim's algorithm.
        
        Here we are allowing an optional partial MST. So prim will find the MST for the component containing the start vertex.
        """
        self.validate_start(start)

        if self.directed:
            raise ValueError("Prim's algorithm requires an undirected graph.")

        if not allow_partial and not self.is_connected():
            raise ValueError(
                "Graph is disconnected. A full MST does not exist. "
                "Use allow_partial=True to compute the MST of the component containing the start vertex."
            )
    
    def print_graph(self):
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
    Binary heap fringe.
    """

    def __init__(self):
        self.heap = []
        self.counter = itertools.count()

    def push(self, priority, vertex, parent=None):
        count = next(self.counter)
        heapq.heappush(self.heap, (priority, count, vertex, parent))

    def pop_min(self):
        priority, _count, vertex, parent = heapq.heappop(self.heap)
        return priority, vertex, parent

    def is_empty(self):
        return len(self.heap) == 0

    def snapshot(self):
        return [
            {"priority": priority, "vertex": vertex, "parent": parent}
            for priority, _count, vertex, parent in sorted(self.heap)
        ]


# ============================================================
# LINKED-LIST FRINGE
# ============================================================

class LinkedListFringe:
    """
    Linked-list style fringe implemented with a Python list and linear scan.
    """

    def __init__(self):
        self.items = []

    def push_or_update(self, priority, vertex, parent=None):
        for item in self.items:
            if item["vertex"] == vertex:
                if priority < item["priority"]:
                    item["priority"] = priority
                    item["parent"] = parent
                return

        self.items.append(
            {
                "priority": priority,
                "vertex": vertex,
                "parent": parent,
            }
        )

    def pop_min(self):
        if not self.items:
            raise IndexError("Cannot pop from empty linked-list fringe.")

        min_index = 0

        for i in range(1, len(self.items)):
            current = self.items[i]
            best = self.items[min_index]

            if (current["priority"], current["vertex"]) < (best["priority"], best["vertex"]):
                min_index = i

        item = self.items.pop(min_index)
        return item["priority"], item["vertex"], item["parent"]

    def is_empty(self):
        return len(self.items) == 0

    def snapshot(self):
        return sorted(self.items, key=lambda item: (item["priority"], item["vertex"]))


# ============================================================
# PRIM HELPERS
# ============================================================

def make_step(message, current_vertex, selected_edge, mst_edges, total_weight, fringe_snapshot, visited):
    return {
        "message": message,
        "current_vertex": current_vertex,
        "selected_edge": selected_edge,
        "mst_edges": list(mst_edges),
        "total_weight": total_weight,
        "fringe": fringe_snapshot,
        "visited": sorted(visited),
    }
    
def build_result(algorithm, fringe_name, start, mst_edges, total_weight, visited, graph, steps, runtime_ms):
    """
    This checks whether the result spans the whole graph.
    If all vertices were visited:
        is_full_graph_mst = True
    If some vertices were not visited:
        is_full_graph_mst = False

    That means the result is only a component MST.
    """
    all_vertices = set(graph.vertices())
    unvisited = all_vertices - visited
    is_full_graph_mst = len(unvisited) == 0

    warning = None
    if not is_full_graph_mst:
        warning = (
            f"Graph is disconnected. Returned a component MST for the component "
            f"containing start vertex '{start}', not a full-graph MST."
        )

    return {
        "algorithm": algorithm,
        "fringe": fringe_name,
        "start": start,
        "mst_edges": mst_edges,
        "total_weight": total_weight,
        "visited_vertices": sorted(visited),
        "unvisited_vertices": sorted(unvisited),
        "is_full_graph_mst": is_full_graph_mst,
        "warning": warning,
        "steps": steps,
        "runtime_ms": runtime_ms,
    }


# ============================================================
# PRIM USING BINARY HEAP
# ============================================================

"""
Complexity Overview:

Prim using binary heap.

Time:
    O(E log V)

Space:
    O(V + E)

Reason:
    Each edge consideration may cause a heap insertion.
    Heap operations cost O(log V).
"""
def prim_binary_heap(graph, start, record_steps=True, allow_partial=False):
    graph.validate_for_prim(start, allow_partial=allow_partial)

    start_time = time.perf_counter()

    visited = set()
    mst_edges = []
    total_weight = 0
    steps = []

    fringe = BinaryHeapFringe()
    fringe.push(0, start, parent=None)

    if record_steps:
        steps.append(
            make_step(
                message=f"Initialize Prim from start vertex {start}.",
                current_vertex=start,
                selected_edge=None,
                mst_edges=mst_edges,
                total_weight=total_weight,
                fringe_snapshot=fringe.snapshot(),
                visited=visited,
            )
        )

    while not fringe.is_empty():
        edge_weight, current_vertex, parent = fringe.pop_min()

        if current_vertex in visited:
            continue

        visited.add(current_vertex)

        selected_edge = None

        if parent is not None:
            selected_edge = (parent, current_vertex, edge_weight)
            mst_edges.append(selected_edge)
            total_weight += edge_weight

        if record_steps:
            steps.append(
                make_step(
                    message=(
                        f"Add {current_vertex} to the MST."
                        if parent is None
                        else f"Add edge {parent}-{current_vertex} with weight {edge_weight} to the MST."
                    ),
                    current_vertex=current_vertex,
                    selected_edge=selected_edge,
                    mst_edges=mst_edges,
                    total_weight=total_weight,
                    fringe_snapshot=fringe.snapshot(),
                    visited=visited,
                )
            )

        for neighbor, weight in graph.neighbors(current_vertex):
            if neighbor not in visited:
                fringe.push(weight, neighbor, parent=current_vertex)

                if record_steps:
                    steps.append(
                        make_step(
                            message=f"Consider edge {current_vertex}-{neighbor} with weight {weight}.",
                            current_vertex=current_vertex,
                            selected_edge=(current_vertex, neighbor, weight),
                            mst_edges=mst_edges,
                            total_weight=total_weight,
                            fringe_snapshot=fringe.snapshot(),
                            visited=visited,
                        )
                    )

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return build_result(
        algorithm="Prim",
        fringe_name="Binary Heap",
        start=start,
        mst_edges=mst_edges,
        total_weight=total_weight,
        visited=visited,
        graph=graph,
        steps=steps,
        runtime_ms=runtime_ms,
    )


# ============================================================
# PRIM WITH LINKED-LIST FRINGE
# ============================================================

"""
Complexity Overview:

Prim using a linked-list style fringe.

Time:
    O(V² + E)

Space:
    O(V + E)

Reason:
    Extract-min requires scanning all fringe vertices.
"""
def prim_linked_list(graph, start, record_steps=True, allow_partial=False):
    graph.validate_for_prim(start, allow_partial=allow_partial)

    start_time = time.perf_counter()

    visited = set()
    mst_edges = []
    total_weight = 0
    steps = []

    fringe = LinkedListFringe()
    fringe.push_or_update(0, start, parent=None)

    if record_steps:
        steps.append(
            make_step(
                message=f"Initialize Prim from start vertex {start}.",
                current_vertex=start,
                selected_edge=None,
                mst_edges=mst_edges,
                total_weight=total_weight,
                fringe_snapshot=fringe.snapshot(),
                visited=visited,
            )
        )

    while not fringe.is_empty():
        edge_weight, current_vertex, parent = fringe.pop_min()

        if current_vertex in visited:
            continue

        visited.add(current_vertex)

        selected_edge = None

        if parent is not None:
            selected_edge = (parent, current_vertex, edge_weight)
            mst_edges.append(selected_edge)
            total_weight += edge_weight

        if record_steps:
            steps.append(
                make_step(
                    message=(
                        f"Add {current_vertex} to the MST."
                        if parent is None
                        else f"Add edge {parent}-{current_vertex} with weight {edge_weight} to the MST."
                    ),
                    current_vertex=current_vertex,
                    selected_edge=selected_edge,
                    mst_edges=mst_edges,
                    total_weight=total_weight,
                    fringe_snapshot=fringe.snapshot(),
                    visited=visited,
                )
            )

        for neighbor, weight in graph.neighbors(current_vertex):
            if neighbor not in visited:
                fringe.push_or_update(weight, neighbor, parent=current_vertex)

                if record_steps:
                    steps.append(
                        make_step(
                            message=f"Update/consider edge {current_vertex}-{neighbor} with weight {weight}.",
                            current_vertex=current_vertex,
                            selected_edge=(current_vertex, neighbor, weight),
                            mst_edges=mst_edges,
                            total_weight=total_weight,
                            fringe_snapshot=fringe.snapshot(),
                            visited=visited,
                        )
                    )

    runtime_ms = (time.perf_counter() - start_time) * 1000

    return build_result(
        algorithm="Prim",
        fringe_name="Linked List",
        start=start,
        mst_edges=mst_edges,
        total_weight=total_weight,
        visited=visited,
        graph=graph,
        steps=steps,
        runtime_ms=runtime_ms,
    )


# ============================================================
# SAMPLE DATA
# ============================================================

def build_prim_sample_graph():
    """
    Prim-specific sample graph.

    Expected MST total weight: 10
    Valid MST: A-B(3), B-C(1), C-D(2), D-E(4)
    """
    graph = Graph(directed=False)

    edges = [
        ("A", "B", 3),
        ("A", "C", 6),
        ("B", "C", 1),
        ("B", "D", 5),
        ("C", "D", 2),
        ("C", "E", 7),
        ("D", "E", 4),
    ]

    for u, v, weight in edges:
        graph.add_edge(u, v, weight)

    return graph


def build_negative_weight_prim_graph():
    """
    Prim can handle negative edge weights.

    Expected MST: A-B(-2), B-C(1), C-D(2)
    Total: 1
    """
    graph = Graph(directed=False)

    edges = [
        ("A", "B", -2),
        ("A", "C", 4),
        ("B", "C", 1),
        ("B", "D", 3),
        ("C", "D", 2),
    ]

    for u, v, weight in edges:
        graph.add_edge(u, v, weight)

    return graph


def build_disconnected_graph():
    """
    Disconnected graph:

        A - B - C

        D - E
    """
    graph = Graph(directed=False)

    graph.add_edge("A", "B", 1)
    graph.add_edge("B", "C", 2)
    graph.add_edge("D", "E", 5)

    return graph


# ============================================================
# OUTPUT HELPERS
# ============================================================

def print_prim_result(result):
    print("\n" + "=" * 70)
    print(f"{result['algorithm']} using {result['fringe']}")
    print("=" * 70)
    print(f"Start: {result['start']}")
    print(f"Runtime: {result['runtime_ms']:.6f} ms")
    print(f"Total MST weight: {result['total_weight']}")
    print(f"Full graph MST?: {result['is_full_graph_mst']}")

    if result["warning"]:
        print(f"Warning: {result['warning']}")

    print(f"Visited vertices: {result['visited_vertices']}")
    print(f"Unvisited vertices: {result['unvisited_vertices']}")

    print("\nMST edges:")
    for u, v, weight in result["mst_edges"]:
        print(f"  {u} - {v}  weight={weight}")


# ============================================================
# TESTS
# ============================================================

def test_sample_graph_mst_weight():
    graph = build_prim_sample_graph()

    heap_result = prim_binary_heap(graph, "A", record_steps=False)
    list_result = prim_linked_list(graph, "A", record_steps=False)

    assert heap_result["total_weight"] == 10
    assert list_result["total_weight"] == 10
    assert heap_result["is_full_graph_mst"] is True
    assert list_result["is_full_graph_mst"] is True
    assert len(heap_result["mst_edges"]) == len(graph.vertices()) - 1
    assert len(list_result["mst_edges"]) == len(graph.vertices()) - 1

    print("Passed: Prim sample graph MST total is correct for both fringe versions.")


def test_negative_weight_graph_allowed():
    graph = build_negative_weight_prim_graph()

    heap_result = prim_binary_heap(graph, "A", record_steps=False)
    list_result = prim_linked_list(graph, "A", record_steps=False)

    assert heap_result["total_weight"] == 1
    assert list_result["total_weight"] == 1
    assert heap_result["is_full_graph_mst"] is True
    assert list_result["is_full_graph_mst"] is True

    print("Passed: Prim correctly handles a graph with a negative edge.")


def test_invalid_start():
    graph = build_prim_sample_graph()

    try:
        prim_binary_heap(graph, "Z", record_steps=False)
        raise AssertionError("Expected invalid start to raise ValueError.")
    except ValueError:
        print("Passed: invalid start vertex is rejected.")


def test_directed_graph_rejected():
    graph = Graph(directed=True)
    graph.add_edge("A", "B", 1)

    try:
        prim_binary_heap(graph, "A", record_steps=False)
        raise AssertionError("Expected directed graph to raise ValueError.")
    except ValueError:
        print("Passed: directed graph is rejected.")


def test_disconnected_graph_rejected_by_default():
    graph = build_disconnected_graph()

    try:
        prim_binary_heap(graph, "A", record_steps=False)
        raise AssertionError("Expected disconnected graph to raise ValueError.")
    except ValueError:
        print("Passed: disconnected graph is rejected by default.")


def test_disconnected_graph_partial_mode():
    graph = build_disconnected_graph()

    heap_result = prim_binary_heap(graph, "A", record_steps=False, allow_partial=True)
    list_result = prim_linked_list(graph, "A", record_steps=False, allow_partial=True)

    assert heap_result["total_weight"] == 3
    assert list_result["total_weight"] == 3
    assert heap_result["is_full_graph_mst"] is False
    assert list_result["is_full_graph_mst"] is False
    assert heap_result["visited_vertices"] == ["A", "B", "C"]
    assert list_result["visited_vertices"] == ["A", "B", "C"]
    assert heap_result["unvisited_vertices"] == ["D", "E"]
    assert list_result["unvisited_vertices"] == ["D", "E"]
    assert heap_result["warning"] is not None
    assert list_result["warning"] is not None

    print("Passed: partial mode returns MST for the start component only.")


def test_single_vertex_graph():
    graph = Graph(directed=False)
    graph.add_vertex("A")

    heap_result = prim_binary_heap(graph, "A", record_steps=False)
    list_result = prim_linked_list(graph, "A", record_steps=False)

    assert heap_result["total_weight"] == 0
    assert list_result["total_weight"] == 0
    assert heap_result["mst_edges"] == []
    assert list_result["mst_edges"] == []

    print("Passed: single-vertex graph MST has total weight 0.")


def test_equal_weight_graph():
    graph = Graph(directed=False)
    graph.add_edge("A", "B", 1)
    graph.add_edge("A", "C", 1)
    graph.add_edge("B", "C", 1)

    heap_result = prim_binary_heap(graph, "A", record_steps=False)
    list_result = prim_linked_list(graph, "A", record_steps=False)

    assert heap_result["total_weight"] == 2
    assert list_result["total_weight"] == 2
    assert len(heap_result["mst_edges"]) == 2
    assert len(list_result["mst_edges"]) == 2

    print("Passed: equal-weight graph returns a valid MST total.")


def run_tests():
    print("\nRunning Prim tests...")
    test_sample_graph_mst_weight()
    test_negative_weight_graph_allowed()
    test_invalid_start()
    test_directed_graph_rejected()
    test_disconnected_graph_rejected_by_default()
    test_disconnected_graph_partial_mode()
    test_single_vertex_graph()
    test_equal_weight_graph()
    print("All Prim tests passed.")


# ============================================================
# MAIN DEMO
# ============================================================

def main():
    graph = build_prim_sample_graph()

    print("\nPRIM DEMO")
    print("=" * 70)

    graph.print_graph()

    heap_result = prim_binary_heap(graph, "A")
    list_result = prim_linked_list(graph, "A")

    print_prim_result(heap_result)
    print_prim_result(list_result)

    print("\nPartial/component mode demo:")
    disconnected = build_disconnected_graph()
    partial_result = prim_binary_heap(
        disconnected,
        "A",
        allow_partial=True,
        record_steps=False
    )
    print_prim_result(partial_result)

    print("\nStep counts:")
    print(f"  Binary heap steps: {len(heap_result['steps'])}")
    print(f"  Linked-list steps: {len(list_result['steps'])}")

    run_tests()


if __name__ == "__main__":
    main()
