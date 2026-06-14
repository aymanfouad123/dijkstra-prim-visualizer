# Final Project Specification — Option 1: Shortest Paths and Minimum Spanning Trees

## Project Context

This programming project is the final project for the algorithms course.

- **Due:** Before writing the final exam
- **Total:** 100 marks
- **Weight:** 20% of final grade
- **Allowed languages:** Java, C/C++, or Python
- **Chosen option:** Option 1 — Shortest Paths and Minimum Spanning Trees

The project should bring together algorithm design, implementation, testing, efficiency analysis, visualization/animation, and written reflection.

---

# 1. Selected Project Option

## Option 1: Shortest Paths and Minimum Spanning Trees

The project must implement and compare two graph algorithms:

1. **Dijkstra’s shortest-path algorithm**
2. **Prim’s minimum-spanning-tree algorithm**

The project must assume that input graphs are represented using **adjacency lists**.

For both algorithms, the **fringe data structure** must be implemented in two ways:

1. **Binary heap fringe**
2. **Linked list fringe**

The project must compare the performance and behavior of these two fringe implementations.

---

# 2. Required Algorithm Implementations

The code should include four main algorithm implementations:

| Algorithm | Fringe Data Structure | Required Output                                            |
| --------- | --------------------- | ---------------------------------------------------------- |
| Dijkstra  | Binary heap           | Shortest distances, predecessor tree, runtime, major steps |
| Dijkstra  | Linked list           | Shortest distances, predecessor tree, runtime, major steps |
| Prim      | Binary heap           | MST edges, total MST weight, runtime, major steps          |
| Prim      | Linked list           | MST edges, total MST weight, runtime, major steps          |

---

# 3. Graph Representation Requirement

The project must use an **adjacency list representation**.

Expected structure conceptually:

```python
graph = {
    "A": [("B", 4), ("C", 2)],
    "B": [("A", 4), ("C", 1), ("D", 5)],
    "C": [("A", 2), ("B", 1)],
}
```

The implementation should support:

- Adding vertices
- Adding weighted edges
- Directed or undirected graph mode, if useful
- Non-negative edge weights
- Querying neighbors of a vertex
- Counting vertices and edges
- Checking graph connectivity for Prim’s algorithm

---

# 4. Input Expectations

The assignment does not provide fixed input files, so the project should include its own testing data.

The program should support at least these input sources:

## 4.1 Built-In Sample Graph

Use a small hand-made graph with known correct results. This is needed for correctness testing and screenshots.

Recommended sample graph:

```text
Vertices: A, B, C, D, E, F

Undirected weighted edges:
A-B 4
A-C 2
B-C 1
B-D 5
C-D 8
C-E 10
D-E 2
D-F 6
E-F 3

Start/source vertex: A
```

Expected Dijkstra shortest distances from `A`:

| Vertex | Distance from A | Path                  |
| ------ | --------------: | --------------------- |
| A      |               0 | A                     |
| B      |               3 | A → C → B             |
| C      |               2 | A → C                 |
| D      |               8 | A → C → B → D         |
| E      |              10 | A → C → B → D → E     |
| F      |              13 | A → C → B → D → E → F |

Expected Prim MST total weight:

```text
13
```

One valid MST is:

| Edge | Weight |
| ---- | -----: |
| B-C  |      1 |
| A-C  |      2 |
| D-E  |      2 |
| E-F  |      3 |
| B-D  |      5 |

Total weight: `13`

## 4.2 Manually Entered Graphs

The UI or command-line program should allow users to add vertices and weighted edges incrementally.

For Dijkstra:

- Input graph may be directed or undirected.
- Edge weights must be non-negative.
- A source vertex must be selected.

For Prim:

- Input graph must be undirected.
- Input graph must be connected.
- A start vertex must be selected.

## 4.3 Randomly Generated Graphs

The project should generate random graphs for performance experiments.

Recommended categories:

| Graph Type | Edge Count Goal      | Purpose                                         |
| ---------- | -------------------- | ----------------------------------------------- |
| Sparse     | `E ≈ 2V` or `E ≈ 3V` | Shows heap advantage more clearly               |
| Dense      | `E ≈ V² / 4`         | Shows behavior when many edges dominate runtime |

Recommended graph sizes:

```text
V = 10, 25, 50, 100, 200
```

The generated graphs should be connected when used with Prim’s algorithm.

---

# 5. Output Expectations

Each algorithm run should output enough data to support correctness checking, animation, and report writing.

## 5.1 Dijkstra Output

Each Dijkstra implementation should return or print:

- Source vertex
- Shortest distance from source to every vertex
- Predecessor map
- Shortest-path tree edges
- Runtime in milliseconds
- Major iteration steps for animation or screenshots

Example output:

```text
Dijkstra using Binary Heap
Source: A
Distances:
A: 0
B: 3
C: 2
D: 8
E: 10
F: 13
Runtime: ... ms
```

## 5.2 Prim Output

Each Prim implementation should return or print:

- Start vertex
- MST edges
- Total MST weight
- Runtime in milliseconds
- Major iteration steps for animation or screenshots

Example output:

```text
Prim using Linked List
Start: A
MST edges:
A-C 2
C-B 1
B-D 5
D-E 2
E-F 3
Total weight: 13
Runtime: ... ms
```

---

# 6. Animation / Major Iteration Requirement

The assignment requires:

> Show each major iteration of the algorithms using animation. Save these animations as `.gif` or `.png` files and zip them into a folder with the project report.

The code should therefore record major algorithm steps, even if the initial backend is command-line based.

Each major step should include enough information for a future UI or visualization layer.

Recommended step format:

```python
{
    "description": "Relax edge A-C and update C to distance 2.",
    "current_vertex": "A",
    "selected_edge": ["A", "C", 2],
    "visited": ["A"],
    "fringe": [
        {"vertex": "B", "priority": 4, "parent": "A"},
        {"vertex": "C", "priority": 2, "parent": "A"}
    ],
    "tree_edges": [["A", "C", 2]],
    "distances": {"A": 0, "B": 4, "C": 2}
}
```

## Major Iterations for Dijkstra

A major step occurs when:

- The source is initialized.
- A minimum-distance vertex is extracted from the fringe.
- A vertex is finalized/visited.
- An outgoing edge is relaxed.
- A tentative distance is updated.
- The predecessor tree changes.

## Major Iterations for Prim

A major step occurs when:

- The start vertex is initialized.
- A minimum-key vertex is extracted from the fringe.
- A new vertex is added to the MST.
- A selected edge is added to the MST.
- Candidate edges are considered or updated.

---

# 7. User Interface Requirement

The assignment requires:

> Have a user interface in which you can incrementally add edges to the graph and update the trees accordingly.

The UI should support:

- Add vertex
- Add weighted edge
- Select source/start vertex
- Select algorithm: Dijkstra or Prim
- Select fringe: binary heap or linked list
- Run algorithm
- Step through major iterations
- Display final shortest-path tree or MST
- Display runtime
- Display fringe contents, visited vertices, and current tree state

The UI does not need to be over-engineered. It only needs to clearly demonstrate that the algorithms work and that edges can be added incrementally.

---

# 8. Correctness and Validation Requirements

The code should validate algorithm assumptions.

## Dijkstra Validation

Dijkstra’s algorithm requires:

- Source vertex exists
- Edge weights are non-negative

If the graph is disconnected, unreachable vertices may remain at infinity.

The program should reject negative weights.

## Prim Validation

Prim’s algorithm requires:

- Graph is undirected
- Graph is connected
- Start vertex exists

If the graph is disconnected, the program should raise an error or clearly report that no single MST exists.

---

# 9. Complexity Expectations

The report must include complexity analysis.

| Algorithm | Fringe      |           Expected Time Complexity | Expected Space Complexity |
| --------- | ----------- | ---------------------------------: | ------------------------: |
| Dijkstra  | Binary heap | `O((V + E) log V)` or `O(E log V)` |                `O(V + E)` |
| Dijkstra  | Linked list |                        `O(V² + E)` |                `O(V + E)` |
| Prim      | Binary heap |                       `O(E log V)` |                `O(V + E)` |
| Prim      | Linked list |                        `O(V² + E)` |                `O(V + E)` |

Where:

- `V` = number of vertices
- `E` = number of edges

Key explanation:

- The binary heap improves the `extract-min` operation.
- The linked list version must scan the fringe to find the minimum item.
- The graph is represented by adjacency lists, so outgoing edges are scanned efficiently.

---

# 10. Testing and Evaluation Requirements

The project should include both correctness tests and performance tests.

## 10.1 Correctness Tests

Include tests for:

- Known sample graph for Dijkstra
- Known sample graph for Prim
- Single-vertex graph
- Two-vertex graph
- Equal-weight edges
- Disconnected graph for Prim
- Negative edge rejection for Dijkstra

## 10.2 Performance Tests

Run benchmarks on sparse and dense graphs.

Recommended benchmark table format:

| Graph Type |   V |   E | Algorithm | Fringe      | Average Runtime (ms) |
| ---------- | --: | --: | --------- | ----------- | -------------------: |
| Sparse     |  10 |  30 | Dijkstra  | Binary Heap |                  ... |
| Sparse     |  10 |  30 | Dijkstra  | Linked List |                  ... |
| Sparse     |  10 |  30 | Prim      | Binary Heap |                  ... |
| Sparse     |  10 |  30 | Prim      | Linked List |                  ... |

Recommended methodology:

- Run each configuration multiple times.
- Report average runtime.
- Use the same graph for heap and linked-list comparisons.
- Compare sparse vs dense graph behavior.

---

# 11. Required Project Report

After coding the project, prepare a polished project report.

## Report Format

- PDF or Microsoft Word format only
- Maximum 12 pages
- Standard letter size: 8.5 × 11 inches
- Single spaced
- 1-inch margins
- 12-point Times New Roman font

Recommended target length for this project: **8–10 pages**.

## Required Report Contents

The report must include:

1. Software and hardware environment
2. Algorithm design and pseudocode
3. Testing data
4. Experimental results
5. Complexity analysis
6. Screenshots showing running scenarios and running results
7. User manual / README
8. Discussion and reflection on knowledge gained
9. References, if applicable
10. Source files and executable file included in submission package

---

# 12. Recommended Report Structure

## Page 1 — Title and Overview

Include:

- Project title
- Student information
- Selected option
- Brief project objective
- Summary of implemented algorithms

Suggested project title:

```text
Interactive Graph Algorithm Visualizer: Comparing Binary Heap and Linked List Fringes for Dijkstra and Prim
```

## Page 2 — Software and Hardware Environment

Include:

- Programming language
- Framework/UI technology, if used
- Operating system
- CPU/RAM
- IDE/editor
- Libraries

Mention whether the graph algorithms and fringe structures were implemented manually.

## Pages 3–4 — Algorithm Design and Pseudocode

Include pseudocode for:

- Dijkstra with binary heap
- Dijkstra with linked list
- Prim with binary heap
- Prim with linked list

Explain the role of the fringe in both algorithms.

## Page 5 — Complexity Analysis

Include the complexity table and explain why heap and linked list differ.

## Page 6 — Implementation and UI Design

Discuss:

- Adjacency list representation
- Binary heap fringe
- Linked list fringe
- Step recording for animation
- User input and validation
- UI controls

## Pages 7–8 — Testing Data and Results

Include:

- Sample graph
- Expected Dijkstra output
- Expected Prim output
- Benchmark table
- Runtime chart
- Screenshots

## Page 9 — Discussion

Discuss:

- Binary heap vs linked list performance
- Sparse vs dense graph behavior
- Similarities and differences between Dijkstra and Prim
- Whether observed runtime matches theoretical complexity

## Page 10 — User Manual and Reflection

Include:

- How to run the program
- How to add vertices/edges
- How to choose algorithms/fringe type
- How to interpret output
- Reflection on challenges, learning outcomes, and future improvements

---

# 13. Submission Package Requirements

Prepare a zip folder containing:

```text
FinalProject_<Name>/
  report.pdf or report.docx
  README.md
  source files
  executable file or run instructions
  screenshots/
  animations/
    dijkstra_heap.gif or .png frames
    dijkstra_linked_list.gif or .png frames
    prim_heap.gif or .png frames
    prim_linked_list.gif or .png frames
  benchmark_results.csv
```

The assignment requires a zip folder containing the project report and supporting `.gif` or `.png` animation files, if applicable.

---

# 14. Grading Rubric

Total: **100 marks**

Each category is worth **20 marks**.

---

## 14.1 Understanding and Design of the Algorithms — 20 marks

### Does Not Meet Expectations: 0–6 marks

- Algorithm pseudocode is flawed.
- Demonstrates significant misunderstanding of the problem.

### Meets Expectations: 7–15 marks

- Algorithm pseudocode is correctly applied.
- Shows good understanding of the problem.

### Exceeds Expectations: 16–20 marks

- Algorithm pseudocode is well-described and correctly applied.
- Shows deep insight into the problem.
- Considers alternative approaches.
- Effectively justifies the chosen approach.

### How to Target Full Marks

- Clearly explain Dijkstra and Prim.
- Explain how the fringe is used in both algorithms.
- Compare binary heap and linked list operations.
- State algorithm assumptions.
- Include correct pseudocode.
- Explain why adjacency lists are appropriate.

---

## 14.2 Coding and Efficiency — 20 marks

### Does Not Meet Expectations: 0–6 marks

- Code is disorganized.
- Lacks comments.
- Has significant inefficiencies or errors.

### Meets Expectations: 7–15 marks

- Code is well-organized.
- Includes comments.
- Follows good programming practices.
- Uses efficient implementation.

### Exceeds Expectations: 16–20 marks

- Code demonstrates exceptional organization, efficiency, and clarity.
- Shows evidence of advanced programming techniques to optimize performance.

### How to Target Full Marks

- Keep graph logic separate from UI logic.
- Use clear classes/functions.
- Implement binary heap and linked list fringe cleanly.
- Use adjacency lists.
- Add validation for invalid inputs.
- Include comments explaining theory and implementation choices.
- Include a benchmark mode.
- Avoid unnecessary inefficiencies in the heap version.

---

## 14.3 Test Data, Results, and Analysis — 20 marks

### Does Not Meet Expectations: 0–6 marks

- Limited test cases.
- Unclear user manual.
- Unclear results.
- Superficial analysis.
- Missing complexity analysis or important screenshots.

### Meets Expectations: 7–15 marks

- Adequate range of test cases.
- Clear user manual.
- Clear presentation of results.
- Thoughtful analysis with logical conclusions.
- Includes complexity analysis and some screenshots.

### Exceeds Expectations: 16–20 marks

- Comprehensive test cases covering edge cases.
- Exceptionally clear and detailed user manual.
- Insightful analysis beyond the basic requirements.
- Explores implications and potential optimizations.
- Includes detailed complexity analysis and complete screenshots.

### How to Target Full Marks

- Include correctness tests with known expected answers.
- Include edge cases.
- Include sparse and dense graph experiments.
- Include runtime tables and charts.
- Include screenshots of running scenarios and final results.
- Explain why results match or differ from theory.

---

## 14.4 Project Report Quality and Organization — 20 marks

### Does Not Meet Expectations: 0–6 marks

- Report is poorly organized.
- Significant grammatical errors.
- Unclear explanations.
- No user manual included.

### Meets Expectations: 7–15 marks

- Report is well-structured.
- Minor grammatical errors only.
- Clear explanations of project components.
- User manual included.

### Exceeds Expectations: 16–20 marks

- Report demonstrates exceptional clarity and organization.
- Professional-quality writing.
- Communicates complex ideas succinctly.
- Precise and concise user manual included.

### How to Target Full Marks

- Use clear headings.
- Keep the report within 8–10 pages if possible.
- Include tables and screenshots.
- Avoid dumping large code blocks into the report.
- Explain results clearly.
- Include a concise user manual.

---

## 14.5 Reflection — 20 marks

### Does Not Meet Expectations: 0–6 marks

- Minimal or no reflection on the design and implementation process.

### Meets Expectations: 7–15 marks

- Reflection adequately discusses the design and implementation process.

### Exceeds Expectations: 16–20 marks

- Reflection is deep and insightful.
- Clearly articulates challenges, learning outcomes, and potential improvements.

### How to Target Full Marks

Discuss:

- What was learned about greedy graph algorithms.
- How Dijkstra and Prim are similar and different.
- How the fringe data structure affects runtime.
- Challenges in visualizing algorithm iterations.
- How theoretical complexity appeared in experimental results.
- Future improvements, such as Fibonacci heaps, better graph layout, larger benchmarks, or exportable GIF generation.

---

# 15. Submission Instructions

Submit the completed final project to the Final Project assessment link.

Once submitted, the submission is final. Resubmission requires special permission from the instructor.

## Required File Naming Template

```text
<course shortname>_<assignment#>_<lastname><firstname>_<studentID>
```

Examples:

```text
ABCD123_Assignment1_DoeJane_1234567
ABCD123_Assignment1_file1_DoeJane_1234567
ABCD123_FinalAssignment_DoeJane_1234567
```

For this project, use the appropriate course shortname, final assignment label, your name, and student ID.

---

# 16. Codex Implementation Checklist

Use this checklist while implementing the project.

## Core Algorithm Requirements

- [ ] Implement adjacency-list graph representation.
- [ ] Implement Dijkstra with binary heap fringe.
- [ ] Implement Dijkstra with linked list fringe.
- [ ] Implement Prim with binary heap fringe.
- [ ] Implement Prim with linked list fringe.
- [ ] Compare binary heap and linked list methods.

## Input and Validation Requirements

- [ ] Support adding vertices.
- [ ] Support adding weighted edges.
- [ ] Reject negative edge weights.
- [ ] Validate source/start vertex exists.
- [ ] Validate connected graph for Prim.
- [ ] Validate undirected graph for Prim.

## Output Requirements

- [ ] Output Dijkstra distances.
- [ ] Output Dijkstra predecessor tree.
- [ ] Output Prim MST edges.
- [ ] Output Prim total MST weight.
- [ ] Output runtime measurements.
- [ ] Record major algorithm steps.

## Testing Requirements

- [ ] Include sample graph with known Dijkstra answer.
- [ ] Include sample graph with known Prim answer.
- [ ] Include edge case tests.
- [ ] Include sparse random graph benchmark.
- [ ] Include dense random graph benchmark.
- [ ] Export benchmark results to CSV or table.

## UI / Animation Requirements

- [ ] UI allows incremental edge insertion.
- [ ] UI allows algorithm selection.
- [ ] UI allows fringe selection.
- [ ] UI displays algorithm steps.
- [ ] UI displays final tree.
- [ ] Save animation or step screenshots as `.gif` or `.png`.

## Report Support Requirements

- [ ] Generate screenshots.
- [ ] Generate runtime table.
- [ ] Generate chart of runtime vs input size.
- [ ] Include README/user manual.
- [ ] Include source files and executable/run instructions.

---

# 17. One-Sentence Project Narrative

This project implements Dijkstra’s shortest-path algorithm and Prim’s minimum-spanning-tree algorithm using adjacency-list graphs, compares binary heap and linked-list fringe implementations, visualizes each major iteration, and experimentally analyzes how fringe choice affects runtime on sparse and dense weighted graphs.
