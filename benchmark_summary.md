# Benchmark Summary

Graphs were generated programmatically. Sparse graphs used approximately `3V` edges. Dense graphs used approximately half of all possible undirected edges.

| Graph Type |   V |    E | Algorithm | Fringe      | Runs | Avg Runtime (ms) | Median Runtime (ms) |
| ---------- | --: | ---: | --------- | ----------- | ---: | ---------------: | ------------------: |
| Sparse     |  25 |   75 | Dijkstra  | Binary Heap |   20 |         0.038815 |            0.037542 |
| Sparse     |  25 |   75 | Dijkstra  | Linked List |   20 |         0.068800 |            0.066812 |
| Sparse     |  25 |   75 | Prim      | Binary Heap |   20 |         0.048654 |            0.048646 |
| Sparse     |  25 |   75 | Prim      | Linked List |   20 |         0.070352 |            0.067646 |
| Dense      |  25 |  150 | Dijkstra  | Binary Heap |   20 |         0.054812 |            0.053417 |
| Dense      |  25 |  150 | Dijkstra  | Linked List |   20 |         0.087948 |            0.086083 |
| Dense      |  25 |  150 | Prim      | Binary Heap |   20 |         0.090150 |            0.088542 |
| Dense      |  25 |  150 | Prim      | Linked List |   20 |         0.104956 |            0.103521 |
| Sparse     |  50 |  150 | Dijkstra  | Binary Heap |   20 |         0.070986 |            0.070646 |
| Sparse     |  50 |  150 | Dijkstra  | Linked List |   20 |         0.201415 |            0.192292 |
| Sparse     |  50 |  150 | Prim      | Binary Heap |   20 |         0.099498 |            0.097270 |
| Sparse     |  50 |  150 | Prim      | Linked List |   20 |         0.216419 |            0.212396 |
| Dense      |  50 |  612 | Dijkstra  | Binary Heap |   20 |         0.158450 |            0.154500 |
| Dense      |  50 |  612 | Dijkstra  | Linked List |   20 |         0.324471 |            0.314312 |
| Dense      |  50 |  612 | Prim      | Binary Heap |   20 |         0.390744 |            0.384375 |
| Dense      |  50 |  612 | Prim      | Linked List |   20 |         0.525442 |            0.516396 |
| Sparse     | 100 |  300 | Dijkstra  | Binary Heap |   20 |         0.156508 |            0.149021 |
| Sparse     | 100 |  300 | Dijkstra  | Linked List |   20 |         0.655642 |            0.634937 |
| Sparse     | 100 |  300 | Prim      | Binary Heap |   20 |         0.205773 |            0.200791 |
| Sparse     | 100 |  300 | Prim      | Linked List |   20 |         0.707375 |            0.693708 |
| Dense      | 100 | 2475 | Dijkstra  | Binary Heap |   20 |         0.507131 |            0.496604 |
| Dense      | 100 | 2475 | Dijkstra  | Linked List |   20 |         1.285375 |            1.281979 |
| Dense      | 100 | 2475 | Prim      | Binary Heap |   20 |         1.694862 |            1.683042 |
| Dense      | 100 | 2475 | Prim      | Linked List |   20 |         3.114175 |            3.108500 |
| Sparse     | 200 |  600 | Dijkstra  | Binary Heap |   20 |         0.311594 |            0.307625 |
| Sparse     | 200 |  600 | Dijkstra  | Linked List |   20 |         2.194244 |            2.180834 |
| Sparse     | 200 |  600 | Prim      | Binary Heap |   20 |         0.424850 |            0.417979 |
| Sparse     | 200 |  600 | Prim      | Linked List |   20 |         2.523450 |            2.510333 |
| Dense      | 200 | 9950 | Dijkstra  | Binary Heap |   20 |         1.681188 |            1.646687 |
| Dense      | 200 | 9950 | Dijkstra  | Linked List |   20 |         5.327771 |            5.304292 |
| Dense      | 200 | 9950 | Prim      | Binary Heap |   20 |         7.606423 |            7.577458 |
| Dense      | 200 | 9950 | Prim      | Linked List |   20 |        22.050450 |           21.998770 |

## Notes

- The same generated graph was used for binary heap and linked-list comparisons.
- `record_steps=False` was used during benchmarks so visualization recording did not affect runtime.
- The benchmark checks that heap and linked-list implementations produce identical outputs before recording timing results.
- Small graphs may show only minor differences because fixed overhead dominates. Larger graphs better show the effect of the fringe data structure.
