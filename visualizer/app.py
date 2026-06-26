"""Stateful, linear Tkinter visualizer for Dijkstra and Prim."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple

from . import algorithm_bridge as bridge
from .graph_view import GraphView

Edge = Tuple[str, str, float]


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Dijkstra and Prim Visualizer")
        self.root.geometry("1180x740")
        self.root.minsize(940, 620)

        self.algorithm = tk.StringVar(value="")
        self.fringe = tk.StringVar(value="Binary Heap")
        self.graph_mode = tk.StringVar(value="")
        self.preset = tk.StringVar(value="")
        self.directed = tk.BooleanVar(value=False)
        self.allow_partial_prim = tk.BooleanVar(value=False)
        self.start = tk.StringVar(value="")
        self.vertex_name = tk.StringVar(value="")
        self.edge_u = tk.StringVar(value="")
        self.edge_v = tk.StringVar(value="")
        self.edge_weight = tk.StringVar(value="1")
        self.status = tk.StringVar(value="Choose an algorithm to begin.")
        self.readiness = tk.StringVar(value="Blocked: choose an algorithm.")
        self.graph_summary = tk.StringVar(value="No graph loaded.")
        self.step_label = tk.StringVar(value="Step 0 / 0")

        self.vertices: List[str] = []
        self.edges: List[Edge] = []
        self.graph_source = "empty"
        self.loaded_preset: Optional[str] = None

        self.result: Optional[Dict[str, Any]] = None
        self.steps: List[Dict[str, Any]] = []
        self.step_index = 0
        self.edge_start: Optional[str] = None
        self.is_running = False
        self.is_animating = False
        self.animation_after_id: Optional[str] = None
        self.animation_delay_ms = 850

        self._build()
        self._set_preset_options([])
        self._sync_state()

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = ttk.Frame(self.root, padding=10)
        shell.grid(row=0, column=0, sticky=tk.NSEW)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        left = ttk.Frame(shell, width=340)
        left.grid(row=0, column=0, sticky=tk.NS, padx=(0, 10))
        left.grid_propagate(False)

        right = ttk.Frame(shell)
        right.grid(row=0, column=1, sticky=tk.NSEW)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        steps_parent = self._build_scrollable_sidebar(left)
        self._build_steps(steps_parent)
        self._bind_sidebar_mousewheel(steps_parent)

        self.view = GraphView(right)
        self.view.on_blank_double_click = self._add_vertex_at
        self.view.on_vertex_click = self._on_canvas_vertex_click
        self.view.grid(row=0, column=0, sticky=tk.NSEW)

        self._build_bottom(right)

    def _build_scrollable_sidebar(self, parent: ttk.Frame) -> ttk.Frame:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        content = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        def update_scrollregion(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_content_width(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", update_content_width)
        self.sidebar_canvas = canvas
        return content

    def _bind_sidebar_mousewheel(self, widget: tk.Widget) -> None:
        for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(event_name, self._on_sidebar_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_sidebar_mousewheel(child)

    def _on_sidebar_mousewheel(self, event) -> str:
        if event.num == 4:
            units = -1
        elif event.num == 5:
            units = 1
        else:
            units = int(-1 * (event.delta / 120))
            if units == 0 and event.delta:
                units = -1 if event.delta > 0 else 1

        if units:
            self.sidebar_canvas.yview_scroll(units, "units")
        return "break"

    def _build_steps(self, parent: ttk.Frame) -> None:
        step1 = ttk.LabelFrame(parent, text="1. Algorithm", padding=8)
        step1.pack(fill=tk.X, pady=(0, 8))
        for name in bridge.ALGORITHMS:
            ttk.Radiobutton(
                step1,
                text=name,
                value=name,
                variable=self.algorithm,
                command=self._on_algorithm_change,
            ).pack(anchor=tk.W)

        step2 = ttk.LabelFrame(parent, text="2. Graph", padding=8)
        step2.pack(fill=tk.X, pady=(0, 8))
        self.graph_widgets: List[tk.Widget] = []
        self.preset_widgets: List[tk.Widget] = []
        self.vertex_widgets: List[tk.Widget] = []
        self.edge_widgets: List[tk.Widget] = []

        for label, value in (("Load preset", "preset"), ("Create from scratch", "manual")):
            widget = ttk.Radiobutton(
                step2,
                text=label,
                value=value,
                variable=self.graph_mode,
                command=self._on_graph_mode_change,
            )
            widget.pack(anchor=tk.W)
            self.graph_widgets.append(widget)

        self.preset_menu = ttk.OptionMenu(step2, self.preset, "")
        self.preset_menu.pack(fill=tk.X, pady=(6, 0))
        self.preset_widgets.append(self.preset_menu)

        self.load_preset_button = ttk.Button(
            step2,
            text="Load selected preset",
            command=self.load_preset,
        )
        self.load_preset_button.pack(fill=tk.X, pady=(4, 0))
        self.preset_widgets.append(self.load_preset_button)

        self.manual_frame = ttk.Frame(step2)
        self.manual_frame.pack(fill=tk.X, pady=(8, 0))
        self.manual_frame.columnconfigure(1, weight=1)
        self.manual_frame.columnconfigure(2, weight=1)

        ttk.Label(self.manual_frame, text="Vertex").grid(row=0, column=0, sticky=tk.W)
        vertex_entry = ttk.Entry(self.manual_frame, textvariable=self.vertex_name, width=10)
        vertex_entry.grid(row=0, column=1, sticky=tk.EW, padx=4)
        vertex_entry.bind("<Return>", lambda _event: self.add_vertex())
        self.vertex_widgets.append(vertex_entry)

        add_vertex_button = ttk.Button(self.manual_frame, text="Add", command=self.add_vertex)
        add_vertex_button.grid(row=0, column=2, sticky=tk.EW)
        self.vertex_widgets.append(add_vertex_button)

        ttk.Label(self.manual_frame, text="Edge").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.u_menu = ttk.OptionMenu(self.manual_frame, self.edge_u, "")
        self.v_menu = ttk.OptionMenu(self.manual_frame, self.edge_v, "")
        self.u_menu.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=(6, 0))
        self.v_menu.grid(row=1, column=2, sticky=tk.EW, pady=(6, 0))
        self.edge_widgets.extend([self.u_menu, self.v_menu])

        weight_entry = ttk.Entry(self.manual_frame, textvariable=self.edge_weight, width=10)
        weight_entry.grid(row=2, column=1, sticky=tk.EW, padx=4, pady=(4, 0))
        weight_entry.bind("<Return>", lambda _event: self.add_edge())
        self.edge_widgets.append(weight_entry)

        add_edge_button = ttk.Button(self.manual_frame, text="Add edge", command=self.add_edge)
        add_edge_button.grid(row=2, column=2, sticky=tk.EW, pady=(4, 0))
        self.edge_widgets.append(add_edge_button)

        self.directed_check = ttk.Checkbutton(
            self.manual_frame,
            text="Directed edges",
            variable=self.directed,
            command=self._on_directed_change,
        )
        self.directed_check.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        clear_button = ttk.Button(self.manual_frame, text="Clear graph", command=self.clear_graph)
        clear_button.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=(6, 0))
        self.clear_button = clear_button

        ttk.Label(step2, textvariable=self.graph_summary, wraplength=310).pack(fill=tk.X, pady=(6, 0))

        step3 = ttk.LabelFrame(parent, text="3. Run", padding=8)
        step3.pack(fill=tk.X, pady=(0, 8))
        self.fringe_widgets: List[tk.Widget] = []

        ttk.Label(step3, text="Fringe").pack(anchor=tk.W)
        for name in bridge.FRINGES:
            widget = ttk.Radiobutton(
                step3,
                text=name,
                value=name,
                variable=self.fringe,
                command=self._invalidate_run,
            )
            widget.pack(anchor=tk.W)
            self.fringe_widgets.append(widget)

        ttk.Label(step3, text="Source / start").pack(anchor=tk.W, pady=(6, 0))
        self.start_menu = ttk.OptionMenu(step3, self.start, "")
        self.start_menu.pack(fill=tk.X)

        self.partial_check = ttk.Checkbutton(
            step3,
            text="Allow disconnected Prim",
            variable=self.allow_partial_prim,
            command=self._invalidate_run,
        )
        self.partial_check.pack(anchor=tk.W, pady=(6, 0))

        self.run_button = ttk.Button(step3, text="Run algorithm", command=self.run)
        self.run_button.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(step3, textvariable=self.readiness, wraplength=310).pack(fill=tk.X, pady=(6, 0))

        step4 = ttk.LabelFrame(parent, text="4. Playback", padding=8)
        step4.pack(fill=tk.X, pady=(0, 8))
        self.playback_widgets: List[tk.Widget] = []
        self.play_pause_button = ttk.Button(
            step4,
            text="Play",
            command=self.toggle_animation,
        )
        self.play_pause_button.pack(fill=tk.X, pady=(0, 6))
        self.playback_widgets.append(self.play_pause_button)
        row = ttk.Frame(step4)
        row.pack(fill=tk.X)
        for text, command in (
            ("|<", self.first),
            ("Back", self.back),
            ("Next", self.next),
            (">|", self.last),
        ):
            button = ttk.Button(row, text=text, command=command, width=7)
            button.pack(side=tk.LEFT, padx=(0, 3))
            self.playback_widgets.append(button)
        ttk.Label(step4, textvariable=self.step_label).pack(anchor=tk.W, pady=(6, 0))

        edges_box = ttk.LabelFrame(parent, text="Graph edges", padding=4)
        edges_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.edge_list = tk.Listbox(edges_box, height=7, font=("Menlo", 10))
        self.edge_list.pack(fill=tk.BOTH, expand=True)

        ttk.Label(parent, textvariable=self.status, wraplength=320, relief=tk.SUNKEN, padding=5).pack(fill=tk.X)

    def _build_bottom(self, parent: ttk.Frame) -> None:
        bottom = ttk.Frame(parent)
        bottom.grid(row=1, column=0, sticky=tk.EW, pady=(8, 0))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)

        step_box = ttk.LabelFrame(bottom, text="Current step", padding=4)
        step_box.grid(row=0, column=0, sticky=tk.NSEW)
        self.step_text = tk.Text(step_box, height=8, width=44, state=tk.DISABLED, font=("Menlo", 10))
        self.step_text.pack(fill=tk.BOTH, expand=True)

        result_box = ttk.LabelFrame(bottom, text="Result", padding=4)
        result_box.grid(row=0, column=1, sticky=tk.NSEW, padx=(8, 0))
        self.result_text = tk.Text(result_box, height=8, width=44, state=tk.DISABLED, font=("Menlo", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _on_algorithm_change(self) -> None:
        algorithm = self.algorithm.get()
        self.graph_mode.set("")
        self.preset.set("")
        self.directed.set(False)
        self.allow_partial_prim.set(False)
        self._set_preset_options(bridge.preset_labels(algorithm))
        self._replace_graph([], [], False, "", source="empty", reset_layout=True)
        self.status.set("Choose a preset or create a graph.")

    def _on_graph_mode_change(self) -> None:
        self.loaded_preset = None
        self._set_edge_start(None)
        if self.graph_mode.get() == "manual":
            self._replace_graph([], [], self.directed.get(), "", source="manual", reset_layout=True)
            self.status.set("Manual graph started.")
        elif self.graph_mode.get() == "preset":
            self._replace_graph([], [], False, "", source="empty", reset_layout=True)
            self.status.set("Select and load a preset.")
        else:
            self._replace_graph([], [], False, "", source="empty", reset_layout=True)

    def _set_preset_options(self, labels: List[str]) -> None:
        menu = self.preset_menu["menu"]
        menu.delete(0, tk.END)
        for label in labels:
            menu.add_command(label=label, command=lambda value=label: self._choose_preset(value))
        self.preset.set(labels[0] if labels else "")

    def _choose_preset(self, label: str) -> None:
        self.preset.set(label)
        if self.graph_mode.get() == "preset" and self.graph_source == "preset" and self.loaded_preset != label:
            self._replace_graph([], [], False, "", source="empty", reset_layout=True)
            self.status.set("Preset changed. Load the selected preset.")
        self._sync_state()

    def load_preset(self) -> None:
        algorithm = self.algorithm.get()
        if not algorithm:
            self.status.set("Choose an algorithm first.")
            self._sync_state()
            return

        self.graph_mode.set("preset")
        try:
            preset = bridge.get_preset(self.preset.get(), algorithm=algorithm)
        except ValueError as exc:
            messagebox.showerror("Preset", str(exc))
            self.status.set(str(exc))
            self._sync_state()
            return

        edges = list(preset.edges)
        vertices = bridge.vertices_from_edges(edges, preset.vertices)
        self._replace_graph(
            vertices,
            edges,
            directed=preset.directed,
            start=preset.default_start,
            source="preset",
            loaded_preset=preset.label,
            reset_layout=True,
        )
        self.status.set(f"Loaded {preset.label}.")

    def add_vertex(self) -> None:
        if not self._can_edit_manual_graph("Add a vertex"):
            return
        self._add_vertex(self.vertex_name.get().strip())

    def _add_vertex_at(self, x: float, y: float) -> None:
        if not self._can_edit_manual_graph("Add a vertex"):
            return
        self._add_vertex(self._next_vertex_name(), position=(x, y))

    def _add_vertex(self, vertex: str, position: Optional[Tuple[float, float]] = None) -> None:
        if not vertex:
            messagebox.showwarning("Vertex", "Enter a vertex name.")
            return
        if vertex in self.vertices:
            messagebox.showinfo("Vertex", f"{vertex} already exists.")
            return

        self.vertices.append(vertex)
        self.vertices.sort(key=str)
        self.graph_source = "manual"
        self.loaded_preset = None
        if position is not None:
            self.view.positions[vertex] = position

        if not self.start.get():
            self.start.set(vertex)
        if not self.edge_u.get():
            self.edge_u.set(vertex)
        elif not self.edge_v.get() and self.edge_u.get() != vertex:
            self.edge_v.set(vertex)

        self.vertex_name.set("")
        self._invalidate_run(sync=False)
        self._refresh_graph()
        self.status.set(f"Added vertex {vertex}.")

    def add_edge(self) -> None:
        if not self._can_edit_manual_graph("Add an edge"):
            return
        self._add_edge_between(self.edge_u.get().strip(), self.edge_v.get().strip())

    def _add_edge_between(self, u: str, v: str) -> None:
        if len(self.vertices) < 2:
            self.status.set("Add at least two vertices before connecting them.")
            self._sync_state()
            return
        if u not in self.vertices or v not in self.vertices or u == v:
            messagebox.showwarning("Edge", "Choose two different vertices.")
            return

        try:
            weight = bridge.parse_weight(self.edge_weight.get(), self.algorithm.get())
        except ValueError as exc:
            messagebox.showerror("Edge", str(exc))
            self.status.set(str(exc))
            return

        directed = self.directed.get() and self.algorithm.get() == "Dijkstra"
        for index, (eu, ev, _old_weight) in enumerate(self.edges):
            same_edge = (eu, ev) == (u, v) if directed else {eu, ev} == {u, v}
            if same_edge:
                self.edges[index] = (u, v, weight)
                break
        else:
            self.edges.append((u, v, weight))

        self.graph_source = "manual"
        self.loaded_preset = None
        self.edge_u.set(u)
        self.edge_v.set(v)
        self._set_edge_start(None)
        self._invalidate_run(sync=False)
        self._refresh_graph()

        arrow = "->" if directed else "-"
        self.status.set(f"Added edge {u} {arrow} {v} with weight {bridge.format_weight(weight)}.")

    def _can_edit_manual_graph(self, action: str) -> bool:
        if self.is_running:
            self.status.set("Wait for the current run to finish.")
            return False
        if not self.algorithm.get():
            self.status.set(f"{action}: choose an algorithm first.")
            self._sync_state()
            return False
        if self.graph_mode.get() != "manual":
            self.status.set(f"{action}: choose Create from scratch first.")
            self._sync_state()
            return False
        return True

    def _next_vertex_name(self) -> str:
        index = 1
        while f"V{index}" in self.vertices:
            index += 1
        return f"V{index}"

    def _on_canvas_vertex_click(self, vertex: str) -> None:
        if not self._can_edit_manual_graph("Connect vertices"):
            return
        if vertex not in self.vertices:
            return

        if self.edge_start is None:
            self._set_edge_start(vertex)
            if len(self.vertices) < 2:
                self.status.set(f"Selected {vertex}. Add another vertex to complete an edge.")
            else:
                self.status.set(f"Selected {vertex}. Click another vertex to add an edge.")
            return

        if self.edge_start == vertex:
            self._set_edge_start(None)
            self.status.set("Edge selection cleared.")
            return

        self.edge_u.set(self.edge_start)
        self.edge_v.set(vertex)
        self._add_edge_between(self.edge_start, vertex)

    def _set_edge_start(self, vertex: Optional[str]) -> None:
        self.edge_start = vertex if vertex in self.vertices else None
        if hasattr(self, "view"):
            self.view.set_pending_vertex(self.edge_start)

    def _on_directed_change(self) -> None:
        if self.algorithm.get() != "Dijkstra":
            self.directed.set(False)
            self.status.set("Prim uses undirected edges.")
            self._sync_state()
            return

        merged = 0
        if not self.directed.get():
            merged = self._merge_undirected_duplicates()

        self._set_edge_start(None)
        self._invalidate_run(sync=False)
        self._refresh_graph()
        if merged:
            self.status.set(f"Switched to undirected edges and merged {merged} duplicate pair(s).")
        else:
            mode = "directed" if self.directed.get() else "undirected"
            self.status.set(f"Switched to {mode} edges.")

    def _merge_undirected_duplicates(self) -> int:
        ordered_keys = []
        merged: Dict[frozenset[str], Edge] = {}
        duplicate_count = 0
        for edge in self.edges:
            u, v, _weight = edge
            key = frozenset((u, v))
            if key in merged:
                duplicate_count += 1
            else:
                ordered_keys.append(key)
            merged[key] = edge
        self.edges = [merged[key] for key in ordered_keys]
        return duplicate_count

    def clear_graph(self, quiet: bool = False) -> None:
        source = "manual" if self.graph_mode.get() == "manual" else "empty"
        self._replace_graph([], [], self.directed.get(), "", source=source, reset_layout=True)
        if not quiet:
            self.status.set("Graph cleared.")

    def run(self) -> None:
        self._stop_animation()
        errors = self._run_validation_errors()
        if errors:
            message = "Cannot run yet:\n" + "\n".join(f"- {error}" for error in errors)
            self._invalidate_run(sync=True)
            self._write(self.step_text, message)
            self.status.set(errors[0])
            return

        algorithm = self.algorithm.get()
        start = self.start.get()
        self._set_edge_start(None)
        self._set_running(True)
        self.status.set(f"Running {algorithm} from {start}...")
        self.root.update_idletasks()

        try:
            self.result = bridge.run_algorithm(
                algorithm=algorithm,
                fringe=self.fringe.get(),
                vertices=self.vertices,
                edges=self.edges,
                start=start,
                directed=self.directed.get(),
                allow_partial_prim=self.allow_partial_prim.get(),
            )
        except ValueError as exc:
            self._invalidate_run(sync=False)
            self._write(self.step_text, str(exc))
            self.status.set(str(exc))
            return
        except Exception as exc:
            self._invalidate_run(sync=False)
            self._write(self.step_text, f"Run failed: {exc}")
            self.status.set(f"Run failed: {exc}")
            return
        finally:
            self._set_running(False)

        self.steps = self.result.get("steps", [])
        self.step_index = 0
        self._render_result()
        self.show_step(0)
        if len(self.steps) > 1:
            self.status.set(f"{algorithm} is animating {len(self.steps)} recorded steps.")
            self._start_animation()
        else:
            self.status.set(f"{algorithm} finished with {len(self.steps)} recorded steps.")
            self._sync_state()

    def _run_validation_errors(self) -> List[str]:
        errors = self._flow_issues()
        if errors:
            return errors

        try:
            bridge.validate_graph_inputs(
                algorithm=self.algorithm.get(),
                fringe=self.fringe.get(),
                vertices=self.vertices,
                edges=self.edges,
                start=self.start.get(),
                directed=self.directed.get() and self.algorithm.get() == "Dijkstra",
            )
        except ValueError as exc:
            return [str(exc)]
        return []

    def _flow_issues(self) -> List[str]:
        algorithm = self.algorithm.get()
        mode = self.graph_mode.get()
        issues: List[str] = []

        if not algorithm:
            return ["choose an algorithm"]

        if mode not in {"preset", "manual"}:
            issues.append("choose how to create the graph")
        elif mode == "preset" and self.graph_source != "preset":
            issues.append("load the selected preset")
        elif mode == "manual" and not self.vertices:
            issues.append("add at least one vertex")

        if self.vertices and self.start.get() not in self.vertices:
            issues.append("choose a valid source/start vertex")

        if (
            algorithm == "Prim"
            and self.vertices
            and self.start.get() in self.vertices
            and not self.allow_partial_prim.get()
        ):
            reachable = self._reachable_vertices(self.start.get())
            if len(reachable) != len(self.vertices):
                missing = ", ".join(v for v in self.vertices if v not in reachable)
                issues.append(f"connect the Prim graph or allow disconnected Prim; unreachable: {missing}")

        return issues

    def _reachable_vertices(self, start: str) -> set[str]:
        adjacency: Dict[str, List[str]] = {vertex: [] for vertex in self.vertices}
        for u, v, _weight in self.edges:
            adjacency.setdefault(u, []).append(v)
            adjacency.setdefault(v, []).append(u)

        seen = set()
        stack = [start]
        while stack:
            vertex = stack.pop()
            if vertex in seen:
                continue
            seen.add(vertex)
            stack.extend(neighbor for neighbor in adjacency.get(vertex, []) if neighbor not in seen)
        return seen

    def show_step(self, index: int) -> None:
        if not self.steps:
            self.step_label.set("Step 0 / 0")
            self.view.draw()
            self._write(self.step_text, "")
            self._sync_state()
            return

        self.step_index = max(0, min(index, len(self.steps) - 1))
        step = self.steps[self.step_index]
        self.view.draw(
            visited=set(step.get("visited", [])),
            current=step.get("current_vertex"),
            fringe=step.get("fringe"),
            tree_edges=step.get("tree_edges"),
            selected_edge=step.get("selected_edge"),
            distances=step.get("distances"),
        )
        self.step_label.set(f"Step {self.step_index + 1} / {len(self.steps)}")
        self._render_step(step)
        self._sync_state()

    def first(self) -> None:
        self._stop_animation()
        self.show_step(0)

    def back(self) -> None:
        self._stop_animation()
        self.show_step(self.step_index - 1)

    def next(self) -> None:
        self._stop_animation()
        self.show_step(self.step_index + 1)

    def last(self) -> None:
        self._stop_animation()
        self.show_step(len(self.steps) - 1)

    def toggle_animation(self) -> None:
        if self.is_animating:
            self._stop_animation()
            self.status.set("Animation paused.")
        else:
            self._start_animation()

    def _start_animation(self) -> None:
        if not self.steps or self.is_running:
            return
        if self.step_index >= len(self.steps) - 1:
            self.show_step(0)
        self._stop_animation(sync=False)
        self.is_animating = True
        self._sync_state()
        self.animation_after_id = self.root.after(self.animation_delay_ms, self._advance_animation)

    def _advance_animation(self) -> None:
        self.animation_after_id = None
        if not self.is_animating or not self.steps:
            return
        if self.step_index >= len(self.steps) - 1:
            self._stop_animation(sync=False)
            self.status.set("Animation finished. Playback is available.")
            self._sync_state()
            return

        self.show_step(self.step_index + 1)
        if self.is_animating:
            self.animation_after_id = self.root.after(self.animation_delay_ms, self._advance_animation)

    def _stop_animation(self, sync: bool = True) -> None:
        if self.animation_after_id is not None:
            try:
                self.root.after_cancel(self.animation_after_id)
            except tk.TclError:
                pass
            self.animation_after_id = None
        self.is_animating = False
        if sync:
            self._sync_state()

    def _replace_graph(
        self,
        vertices: List[str],
        edges: List[Edge],
        directed: bool,
        start: str,
        source: str,
        loaded_preset: Optional[str] = None,
        reset_layout: bool = False,
    ) -> None:
        self.vertices = sorted(dict.fromkeys(vertices), key=str)
        self.edges = list(edges)
        self.graph_source = source
        self.loaded_preset = loaded_preset
        self.directed.set(bool(directed and self.algorithm.get() == "Dijkstra"))
        self.start.set(start if start in self.vertices else (self.vertices[0] if self.vertices else ""))
        self.edge_u.set(self.vertices[0] if self.vertices else "")
        self.edge_v.set(self.vertices[1] if len(self.vertices) > 1 else "")
        self._set_edge_start(None)
        self._invalidate_run(sync=False)
        self._refresh_graph(reset_layout=reset_layout)

    def _refresh_graph(self, reset_layout: bool = False) -> None:
        directed = self.directed.get() and self.algorithm.get() == "Dijkstra"
        self.view.set_graph(self.vertices, self.edges, directed)
        if reset_layout:
            self.view.reset_layout()
        else:
            self.view.draw()
        self._refresh_menus()
        self._refresh_edge_list()
        self._update_graph_summary()
        self._sync_state()

    def _refresh_menus(self) -> None:
        self._set_menu(self.u_menu, self.edge_u, self.vertices)
        self._set_menu(self.v_menu, self.edge_v, self.vertices)
        self._set_menu(self.start_menu, self.start, self.vertices, self._on_start_change)

    def _on_start_change(self, value: str) -> None:
        self._invalidate_run(sync=True)
        self.status.set(f"Start vertex set to {value}.")

    @staticmethod
    def _set_menu(
        menu_widget: ttk.OptionMenu,
        variable: tk.StringVar,
        values: List[str],
        on_select: Optional[Any] = None,
    ) -> None:
        menu = menu_widget["menu"]
        menu.delete(0, tk.END)
        for value in values:
            def select(item=value) -> None:
                variable.set(item)
                if on_select is not None:
                    on_select(item)

            menu.add_command(label=value, command=select)

        if variable.get() not in values:
            variable.set(values[0] if values else "")

    def _refresh_edge_list(self) -> None:
        self.edge_list.delete(0, tk.END)
        if not self.edges:
            self.edge_list.insert(tk.END, "(no edges yet)")
            return

        arrow = "->" if self.directed.get() and self.algorithm.get() == "Dijkstra" else "-"
        for u, v, weight in self.edges:
            self.edge_list.insert(tk.END, f"{u} {arrow} {v}   w={bridge.format_weight(weight)}")

    def _update_graph_summary(self) -> None:
        if not self.vertices:
            if self.graph_mode.get() == "manual":
                self.graph_summary.set("Manual graph is empty.")
            elif self.graph_mode.get() == "preset":
                self.graph_summary.set("No preset loaded.")
            else:
                self.graph_summary.set("No graph loaded.")
            return

        source = "Manual graph"
        if self.graph_source == "preset" and self.loaded_preset:
            source = f"Preset: {self.loaded_preset}"
        directed = "directed" if self.directed.get() and self.algorithm.get() == "Dijkstra" else "undirected"
        self.graph_summary.set(f"{source}. V={len(self.vertices)} E={len(self.edges)} {directed}.")

    def _invalidate_run(self, sync: bool = True) -> None:
        self._stop_animation(sync=False)
        self.result = None
        self.steps = []
        self.step_index = 0
        self.step_label.set("Step 0 / 0")
        if hasattr(self, "view"):
            self.view.draw()
        if hasattr(self, "result_text"):
            self._write(self.result_text, "")
            self._write(self.step_text, "")
        if sync:
            self._sync_state()

    def _render_step(self, step: Dict[str, Any]) -> None:
        lines = [
            step.get("message", ""),
            "",
            f"Current: {step.get('current_vertex', '-')}",
            f"Visited: {', '.join(step.get('visited', [])) or '-'}",
        ]
        if step.get("distances") is not None:
            lines.append("Distances:")
            for vertex, distance in sorted(step["distances"].items()):
                lines.append(f"  {vertex}: {bridge.format_distance(distance)}")
        elif step.get("total_weight") is not None:
            lines.append(f"MST weight so far: {bridge.format_weight(step['total_weight'])}")

        fringe = step.get("fringe") or []
        lines.append("Fringe:")
        if fringe:
            lines.extend(
                f"  {item.get('vertex')} priority={bridge.format_weight(item.get('priority'))} "
                f"parent={item.get('parent', '-')}"
                for item in fringe
            )
        else:
            lines.append("  (empty)")
        self._write(self.step_text, "\n".join(lines))

    def _render_result(self) -> None:
        result = self.result or {}
        lines = [
            f"{result.get('algorithm')} / {result.get('fringe')}",
            f"Runtime: {result.get('runtime_ms', 0):.4f} ms",
            "",
        ]
        if result.get("algorithm") == "Dijkstra":
            lines.append(f"Source: {result.get('source')}")
            lines.append("Distances:")
            for vertex, distance in sorted(result.get("distances", {}).items()):
                lines.append(f"  {vertex}: {bridge.format_distance(distance)}")
            lines.append("Shortest-path tree:")
        else:
            lines.append(f"Start: {result.get('start')}")
            lines.append(f"Total MST weight: {bridge.format_weight(result.get('total_weight'))}")
            lines.append(f"Full graph MST: {result.get('is_full_graph_mst')}")
            if result.get("warning"):
                lines.append(result["warning"])
            lines.append("MST edges:")

        final_edges = result.get("final_edges", [])
        if final_edges:
            for edge in final_edges:
                lines.append(
                    f"  {edge['from']} - {edge['to']} ({bridge.format_weight(edge['weight'])})"
                )
        else:
            lines.append("  (none)")
        self._write(self.result_text, "\n".join(lines))

    def _sync_state(self) -> None:
        has_algorithm = bool(self.algorithm.get())
        has_graph = bool(self.vertices)
        manual_mode = has_algorithm and self.graph_mode.get() == "manual"
        preset_mode = has_algorithm and self.graph_mode.get() == "preset"
        idle = not self.is_running
        issues = self._flow_issues()
        can_run = idle and not issues
        has_steps = bool(self.steps)

        self._configure_widgets(self.graph_widgets, idle and has_algorithm)
        self._configure_widgets(self.preset_widgets, idle and preset_mode)
        self._configure_widgets(self.vertex_widgets, idle and manual_mode)
        self._configure_widgets(self.edge_widgets, idle and manual_mode and len(self.vertices) >= 2)

        directed_enabled = idle and manual_mode and self.algorithm.get() == "Dijkstra"
        self.directed_check.configure(state=tk.NORMAL if directed_enabled else tk.DISABLED)
        clear_enabled = idle and manual_mode and has_graph
        self.clear_button.configure(state=tk.NORMAL if clear_enabled else tk.DISABLED)

        self.view.set_manual_mode(idle and manual_mode)

        run_controls_enabled = idle and has_algorithm and has_graph
        self._configure_widgets(self.fringe_widgets, run_controls_enabled)
        self.start_menu.configure(state=tk.NORMAL if run_controls_enabled else tk.DISABLED)
        prim_partial_enabled = run_controls_enabled and self.algorithm.get() == "Prim"
        self.partial_check.configure(state=tk.NORMAL if prim_partial_enabled else tk.DISABLED)
        self.run_button.configure(
            state=tk.NORMAL if can_run else tk.DISABLED,
            text="Running..." if self.is_running else "Run algorithm",
        )

        playback_enabled = idle and has_steps
        self._configure_widgets(self.playback_widgets, playback_enabled)
        self.play_pause_button.configure(text="Pause" if self.is_animating else "Play")

        if self.is_running:
            self.readiness.set("Running...")
        elif self.is_animating:
            self.readiness.set("Animating. Pause or use playback controls.")
        elif issues:
            self.readiness.set("Blocked: " + "; ".join(issues) + ".")
        elif has_steps:
            self.readiness.set("Run complete. Playback is available.")
        else:
            self.readiness.set("Ready to run.")

    @staticmethod
    def _configure_widgets(widgets: List[tk.Widget], enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in widgets:
            widget.configure(state=state)

    def _set_running(self, running: bool) -> None:
        self.is_running = running
        self._sync_state()

    @staticmethod
    def _write(widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
