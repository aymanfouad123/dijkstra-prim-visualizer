"""
Interactive Tkinter app for the Graph Algorithms Final Project.

Implements every UI requirement from the assignment (Section 7):

    * Add vertex / add weighted edge (incremental graph building)
    * Select source/start vertex
    * Select algorithm: Dijkstra or Prim
    * Select fringe: binary heap or linked list
    * Run the algorithm
    * Step through every major iteration (first/prev/next/last/play)
    * Display the final shortest-path tree or MST
    * Display runtime
    * Display fringe contents, visited vertices, and current tree state

It also exports the recorded iterations as PNG frames + a GIF (Section 6).
All algorithmic work is delegated to ``dijkstra.py`` and ``prim.py`` via
``algorithm_bridge``; this module only handles presentation and flow.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple

from . import algorithm_bridge as bridge
from . import frame_renderer
from .graph_view import (
    COLOR_NODE_FRINGE,
    COLOR_NODE_VISITED,
    COLOR_SELECTED,
    COLOR_TREE,
    GraphView,
)

Edge = Tuple[str, str, float]


class VisualizerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Graph Algorithm Visualizer - Dijkstra & Prim")
        self.root.geometry("1240x760")
        self.root.minsize(1080, 680)

        # ---- Model state -------------------------------------------------
        self.vertices: List[str] = []
        self.edges: List[Edge] = []

        # ---- Run state ---------------------------------------------------
        self.result = None
        self.steps: List[Dict[str, Any]] = []
        self.step_index: int = 0
        self._play_job: Optional[str] = None
        self._last_run_label: str = ""

        # ---- Tk variables ------------------------------------------------
        default_preset = bridge.GRAPH_PRESETS[0].label
        self.preset_var = tk.StringVar(value=default_preset)
        self.directed_var = tk.BooleanVar(value=False)
        self.algorithm_var = tk.StringVar(value="Dijkstra")
        self.fringe_var = tk.StringVar(value="Binary Heap")
        self.source_var = tk.StringVar(value="")
        self.vertex_name_var = tk.StringVar(value="")
        self.edge_u_var = tk.StringVar(value="")
        self.edge_v_var = tk.StringVar(value="")
        self.edge_w_var = tk.StringVar(value="1")
        self.prim_allow_partial_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(
            value="Load a preset or build a graph, then run an algorithm."
        )

        self._build_ui()
        self.algorithm_var.trace_add("write", lambda *_: self._on_algorithm_change())
        self._refresh_vertex_widgets()
        self._on_algorithm_change()

    # ====================================================================
    # UI construction
    # ====================================================================
    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        self._build_quick_start(container)

        body = ttk.Frame(container)
        body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        controls = ttk.Frame(body)
        controls.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        main = ttk.Frame(body)
        main.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_controls(controls)
        self._build_main(main)

    def _build_quick_start(self, parent: ttk.Frame) -> None:
        """Top bar: preset, algorithm, fringe, source, run."""
        bar = ttk.LabelFrame(parent, text="Quick start", padding=8)
        bar.pack(fill=tk.X)

        ttk.Label(bar, text="Preset:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        preset_menu = ttk.OptionMenu(bar, self.preset_var, self.preset_var.get())
        preset_menu.config(width=32)
        preset_menu.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))
        self._set_optionmenu(
            preset_menu,
            self.preset_var,
            bridge.PRESET_LABELS,
        )
        ttk.Button(bar, text="Load preset", command=self.load_preset).grid(
            row=0, column=2, sticky=tk.W, padx=(0, 16)
        )

        ttk.Label(bar, text="Algorithm:").grid(row=0, column=3, sticky=tk.W, padx=(0, 4))
        for i, name in enumerate(bridge.ALGORITHM_NAMES):
            ttk.Radiobutton(bar, text=name, value=name, variable=self.algorithm_var).grid(
                row=0, column=4 + i, sticky=tk.W, padx=(0, 8)
            )

        ttk.Label(bar, text="Fringe:").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        for i, name in enumerate(bridge.FRINGE_NAMES):
            ttk.Radiobutton(bar, text=name, value=name, variable=self.fringe_var).grid(
                row=1, column=1 + i, sticky=tk.W, pady=(6, 0), padx=(0, 8)
            )

        self.source_label = ttk.Label(bar, text="Source vertex:")
        self.source_label.grid(row=1, column=3, sticky=tk.W, pady=(6, 0), padx=(8, 4))
        self.source_menu = ttk.OptionMenu(bar, self.source_var, "")
        self.source_menu.config(width=6)
        self.source_menu.grid(row=1, column=4, sticky=tk.W, pady=(6, 0))

        ttk.Button(bar, text="Run", command=self.run_algorithm).grid(
            row=1, column=5, sticky=tk.EW, padx=(16, 0), pady=(6, 0)
        )

    def _build_controls(self, parent: ttk.Frame) -> None:
        # --- Manual graph building --------------------------------------
        graph_box = ttk.LabelFrame(parent, text="Build your own graph", padding=8)
        graph_box.pack(fill=tk.X, pady=(0, 8))

        helper = (
            "Add vertices first, then choose two vertices and a weight to add an edge."
        )
        ttk.Label(graph_box, text=helper, wraplength=240, justify=tk.LEFT).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 6)
        )

        self.directed_check = ttk.Checkbutton(
            graph_box,
            text="Directed (Dijkstra only)",
            variable=self.directed_var,
            command=self._on_directed_change,
        )
        self.directed_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))

        ttk.Label(graph_box, text="Vertex name:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(graph_box, textvariable=self.vertex_name_var, width=10).grid(
            row=2, column=1, sticky=tk.W, padx=4
        )
        ttk.Button(graph_box, text="Add vertex", command=self.add_vertex).grid(
            row=2, column=2, sticky=tk.W
        )

        ttk.Separator(graph_box, orient=tk.HORIZONTAL).grid(
            row=3, column=0, columnspan=3, sticky=tk.EW, pady=6
        )

        ttk.Label(graph_box, text="From:").grid(row=4, column=0, sticky=tk.W)
        self.edge_u_menu = ttk.OptionMenu(graph_box, self.edge_u_var, "")
        self.edge_u_menu.config(width=5)
        self.edge_u_menu.grid(row=4, column=1, sticky=tk.W, padx=4)

        ttk.Label(graph_box, text="To:").grid(row=5, column=0, sticky=tk.W, pady=(4, 0))
        self.edge_v_menu = ttk.OptionMenu(graph_box, self.edge_v_var, "")
        self.edge_v_menu.config(width=5)
        self.edge_v_menu.grid(row=5, column=1, sticky=tk.W, padx=4, pady=(4, 0))

        ttk.Label(graph_box, text="Weight:").grid(row=6, column=0, sticky=tk.W, pady=(4, 0))
        ttk.Entry(graph_box, textvariable=self.edge_w_var, width=10).grid(
            row=6, column=1, sticky=tk.W, padx=4, pady=(4, 0)
        )
        ttk.Button(graph_box, text="Add edge", command=self.add_edge).grid(
            row=6, column=2, sticky=tk.W, pady=(4, 0)
        )

        btns = ttk.Frame(graph_box)
        btns.grid(row=7, column=0, columnspan=3, sticky=tk.EW, pady=(8, 0))
        ttk.Button(btns, text="Re-layout", command=self.relayout).pack(side=tk.LEFT)
        ttk.Button(btns, text="Clear graph", command=self.clear_graph).pack(
            side=tk.LEFT, padx=4
        )

        # --- Edge list ---------------------------------------------------
        edge_box = ttk.LabelFrame(parent, text="Current edges", padding=4)
        edge_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.edge_list = tk.Listbox(edge_box, height=8, width=28, font=("Menlo", 10))
        self.edge_list.pack(fill=tk.BOTH, expand=True)

        # --- Advanced Prim option ----------------------------------------
        advanced_box = ttk.LabelFrame(parent, text="Advanced", padding=8)
        advanced_box.pack(fill=tk.X, pady=(0, 8))

        self.prim_partial_check = ttk.Checkbutton(
            advanced_box,
            text="Allow partial MST for disconnected graph",
            variable=self.prim_allow_partial_var,
        )
        self.prim_partial_check.pack(anchor=tk.W)

        # --- Playback ----------------------------------------------------
        play_box = ttk.LabelFrame(parent, text="Step through iterations", padding=8)
        play_box.pack(fill=tk.X, pady=(0, 8))

        row = ttk.Frame(play_box)
        row.pack(fill=tk.X)
        ttk.Button(row, text="First", width=6, command=self.first_step).pack(side=tk.LEFT)
        ttk.Button(row, text="Back", width=6, command=self.prev_step).pack(side=tk.LEFT, padx=2)
        self.play_button = ttk.Button(row, text="Play", width=6, command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Next", width=6, command=self.next_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(row, text="Last", width=6, command=self.last_step).pack(side=tk.LEFT)

        self.step_label = ttk.Label(play_box, text="Step 0 / 0")
        self.step_label.pack(anchor=tk.W, pady=(6, 0))

        # --- Export ------------------------------------------------------
        export_box = ttk.LabelFrame(parent, text="Export animation", padding=8)
        export_box.pack(fill=tk.X)
        ttk.Button(export_box, text="Save current frame (PNG)",
                   command=self.save_current_frame).pack(fill=tk.X)
        ttk.Button(export_box, text="Export all frames (PNG + GIF)",
                   command=self.export_all_frames).pack(fill=tk.X, pady=(4, 0))

    def _build_main(self, parent: ttk.Frame) -> None:
        self.description_var = tk.StringVar(
            value="Load a preset or add vertices and edges, then run an algorithm."
        )
        desc = ttk.Label(
            parent,
            textvariable=self.description_var,
            anchor=tk.W,
            font=("Helvetica", 12, "bold"),
            wraplength=820,
            justify=tk.LEFT,
        )
        desc.pack(fill=tk.X, pady=(0, 4))

        self._build_legend(parent)

        self.view = GraphView(parent)
        self.view.pack(fill=tk.BOTH, expand=True)

        info = ttk.Frame(parent)
        info.pack(fill=tk.X, pady=(8, 0))

        fringe_frame = ttk.LabelFrame(info, text="Fringe / priority queue", padding=4)
        fringe_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fringe_list = tk.Listbox(fringe_frame, height=7)
        self.fringe_list.pack(fill=tk.BOTH, expand=True)

        state_frame = ttk.LabelFrame(info, text="Current step", padding=4)
        state_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.state_text = tk.Text(
            state_frame, height=7, width=34, state=tk.DISABLED, font=("Menlo", 10)
        )
        self.state_text.pack(fill=tk.BOTH, expand=True)

        result_frame = ttk.LabelFrame(info, text="Final result", padding=4)
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.result_text = tk.Text(
            result_frame, height=7, width=34, state=tk.DISABLED, font=("Menlo", 10)
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        status = ttk.Label(
            parent, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN, padding=4
        )
        status.pack(fill=tk.X, pady=(8, 0))

    def _build_legend(self, parent: ttk.Frame) -> None:
        legend = ttk.Frame(parent)
        legend.pack(fill=tk.X, pady=(0, 4))

        items = [
            (COLOR_NODE_VISITED, "Green = visited"),
            (COLOR_NODE_FRINGE, "Yellow = fringe"),
            (COLOR_TREE, "Blue = tree edge"),
            (COLOR_SELECTED, "Red = current edge / vertex"),
        ]
        for color, text in items:
            swatch = tk.Canvas(legend, width=14, height=14, highlightthickness=1,
                               highlightbackground="#dadce0")
            swatch.create_rectangle(1, 1, 13, 13, fill=color, outline="")
            swatch.pack(side=tk.LEFT, padx=(0, 2))
            ttk.Label(legend, text=text).pack(side=tk.LEFT, padx=(0, 12))

    # ====================================================================
    # Graph building actions
    # ====================================================================
    def add_vertex(self) -> None:
        name = self.vertex_name_var.get().strip()
        if not name:
            messagebox.showwarning("Add vertex", "Enter a vertex name.")
            return
        if name in self.vertices:
            messagebox.showinfo("Add vertex", f"Vertex {name!r} already exists.")
            return
        self.vertices.append(name)
        self.vertex_name_var.set("")
        self._invalidate_run()
        self._refresh_vertex_widgets()
        self._render_graph()
        self._set_status(f"Added vertex {name}.")

    def add_edge(self) -> None:
        u = self.edge_u_var.get().strip()
        v = self.edge_v_var.get().strip()
        if not u or not v:
            messagebox.showwarning("Add edge", "Select both endpoints.")
            return
        if u == v:
            messagebox.showwarning("Add edge", "Self-loops are not supported.")
            return
        try:
            weight = bridge.edge_weight_value(
                self.edge_w_var.get().strip(),
                algorithm=self.algorithm_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Add edge", str(exc))
            return

        directed = self.directed_var.get() and self.algorithm_var.get() == "Dijkstra"

        # Update weight if the edge already exists (incremental editing).
        for i, (eu, ev, _) in enumerate(self.edges):
            if {eu, ev} == {u, v} and not directed:
                self.edges[i] = (eu, ev, weight)
                self._invalidate_run()
                self._refresh_edge_list()
                self._render_graph()
                self._set_status(f"Updated edge {u}-{v} weight to {weight}.")
                return
            if (eu, ev) == (u, v) and directed:
                self.edges[i] = (u, v, weight)
                self._invalidate_run()
                self._refresh_edge_list()
                self._render_graph()
                self._set_status(f"Updated edge {u}->{v} weight to {weight}.")
                return

        self.edges.append((u, v, weight))
        self._invalidate_run()
        self._refresh_vertex_widgets()
        self._refresh_edge_list()
        self._render_graph()
        arrow = "->" if directed else "-"
        self._set_status(f"Added edge {u}{arrow}{v} (weight {weight}).")

    def load_preset(self) -> None:
        try:
            preset = bridge.get_preset_by_label(self.preset_var.get())
            vertices, edges, default_source, description = bridge.load_preset_data(preset.id)
        except ValueError as exc:
            messagebox.showerror("Load preset", str(exc))
            return

        self.directed_var.set(False)
        self.vertices = vertices
        self.edges = edges
        self.source_var.set(default_source)
        self._invalidate_run()
        self.view.reset_layout()
        self._refresh_vertex_widgets()
        self._refresh_edge_list()
        self._render_graph()
        self._set_status(f"Loaded preset: {preset.label}. {description}")

    def load_sample(self) -> None:
        """Compatibility alias for the assignment sample preset."""
        self.preset_var.set(bridge.GRAPH_PRESETS[0].label)
        self.load_preset()

    def relayout(self) -> None:
        self.view.reset_layout()
        self._render_graph()

    def clear_graph(self) -> None:
        self.vertices = []
        self.edges = []
        self.source_var.set("")
        self._invalidate_run()
        self.view.positions = {}
        self._refresh_vertex_widgets()
        self._refresh_edge_list()
        self._render_graph()
        self._set_status("Cleared graph.")

    # ====================================================================
    # Running the algorithm
    # ====================================================================
    def run_algorithm(self) -> None:
        self._stop_play()
        if not self.vertices:
            messagebox.showwarning("Run", "Add at least one vertex first.")
            return
        source = self.source_var.get().strip()
        if source not in self.vertices:
            messagebox.showwarning("Run", "Select a valid source/start vertex.")
            return

        algorithm = self.algorithm_var.get()
        fringe = self.fringe_var.get()
        directed = self.directed_var.get() and algorithm == "Dijkstra"

        try:
            result = bridge.run_algorithm(
                algorithm=algorithm,
                fringe=fringe,
                vertices=self.vertices,
                edges=self.edges,
                source=source,
                directed=directed,
                record_steps=True,
                allow_partial=self.prim_allow_partial_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror(f"{algorithm} validation", str(exc))
            self._set_status(f"Run rejected: {exc}")
            return

        self.result = result
        self.steps = result.steps or []
        self.step_index = 0
        self._last_run_label = f"{result.algorithm} - {result.fringe_type}"
        self._update_result_panel()
        self.show_step(0)
        status = (
            f"{result.algorithm} ({result.fringe_type}) finished in "
            f"{result.runtime_ms:.4f} ms over {len(self.steps)} steps."
        )
        if result.warning:
            status += f" Warning: {result.warning}"
        self._set_status(status)

    # ====================================================================
    # Step playback
    # ====================================================================
    def show_step(self, index: int) -> None:
        if not self.steps:
            self.view.draw()
            self.step_label.config(text="Step 0 / 0")
            self.description_var.set(
                "Load a preset or add vertices and edges, then run an algorithm."
            )
            return

        self.step_index = max(0, min(index, len(self.steps) - 1))
        step = self.steps[self.step_index]

        self.view.draw(
            visited=set(step.get("visited") or []),
            current=step.get("current_vertex"),
            selected_edge=step.get("selected_edge"),
            tree_edges=step.get("tree_edges"),
            distances=step.get("distances"),
            fringe=step.get("fringe"),
        )

        self.step_label.config(text=f"Step {self.step_index + 1} / {len(self.steps)}")
        self.description_var.set(
            f"[{self._last_run_label}] {step.get('description') or step.get('message', '')}"
        )
        self._update_fringe_panel(step)
        self._update_state_panel(step)

    def first_step(self) -> None:
        self.show_step(0)

    def last_step(self) -> None:
        self.show_step(len(self.steps) - 1)

    def next_step(self) -> None:
        if self.steps and self.step_index < len(self.steps) - 1:
            self.show_step(self.step_index + 1)
        else:
            self._stop_play()

    def prev_step(self) -> None:
        if self.steps and self.step_index > 0:
            self.show_step(self.step_index - 1)

    def toggle_play(self) -> None:
        if self._play_job is not None:
            self._stop_play()
        elif self.steps:
            self.play_button.config(text="Pause")
            self._advance_play()

    def _advance_play(self) -> None:
        if not self.steps or self.step_index >= len(self.steps) - 1:
            self._stop_play()
            return
        self.show_step(self.step_index + 1)
        self._play_job = self.root.after(900, self._advance_play)

    def _stop_play(self) -> None:
        if self._play_job is not None:
            self.root.after_cancel(self._play_job)
            self._play_job = None
        self.play_button.config(text="Play")

    # ====================================================================
    # Info panels
    # ====================================================================
    def _update_fringe_panel(self, step: Dict[str, Any]) -> None:
        self.fringe_list.delete(0, tk.END)
        fringe = step.get("fringe") or []
        if not fringe:
            self.fringe_list.insert(tk.END, "(empty)")
            return
        for item in fringe:
            parent = item.get("parent")
            parent_text = parent if parent is not None else "-"
            self.fringe_list.insert(
                tk.END, f"({item['priority']}, {item['vertex']}, parent={parent_text})"
            )

    def _update_state_panel(self, step: Dict[str, Any]) -> None:
        visited = step.get("visited") or []
        lines = [
            f"Algorithm : {self._last_run_label}",
            f"Current   : {step.get('current_vertex') or '-'}",
            f"Visited   : {', '.join(map(str, visited)) or '(none)'}",
            f"Visited # : {len(visited)} / {len(self.vertices)}",
        ]
        distances = step.get("distances")
        if distances is not None:
            lines.append("Distances :")
            for v in sorted(distances):
                lines.append(f"   {v} = {distances[v]}")
        else:
            total_weight = step.get("total_weight")
            if total_weight is not None:
                lines.append(f"MST weight: {total_weight}")
            else:
                tree_weight = sum(e["weight"] for e in (step.get("tree_edges") or []))
                lines.append(f"MST weight: {tree_weight}")
        self._set_text(self.state_text, "\n".join(lines))

    def _update_result_panel(self) -> None:
        result = self.result
        if result is None:
            self._set_text(self.result_text, "")
            return
        lines = [
            f"{result.algorithm} / {result.fringe_type}",
            f"Source/Start: {result.source_or_start}",
            f"V={result.vertices}  E={result.edges}",
            f"Runtime: {result.runtime_ms:.4f} ms",
            "",
        ]
        if result.algorithm == "Dijkstra":
            lines.append("Shortest distances:")
            source = result.source_or_start
            previous = result.previous or {}
            for v in sorted(result.distances or {}):
                dist = self._fmt(result.distances[v])
                path = bridge.reconstruct_shortest_path(previous, source, v)
                if path:
                    lines.append(f"   {v}: {dist}  ({' -> '.join(path)})")
                else:
                    lines.append(f"   {v}: {dist}")
            lines.append("Tree edges:")
            for e in result.shortest_path_tree_edges or []:
                lines.append(f"   {e['from']} -> {e['to']} ({e['weight']})")
        else:
            lines.append(f"Total MST weight: {result.total_mst_weight}")
            lines.append(f"Full graph MST?: {result.is_full_graph_mst}")
            if result.warning:
                lines.append(f"Warning: {result.warning}")
            lines.append("MST edges:")
            for e in result.mst_edges or []:
                lines.append(f"   {e['from']} - {e['to']} ({e['weight']})")
        self._set_text(self.result_text, "\n".join(lines))

    @staticmethod
    def _fmt(value: Any) -> str:
        try:
            if value == float("inf"):
                return "inf (unreachable)"
        except TypeError:
            pass
        return str(value)

    # ====================================================================
    # Export
    # ====================================================================
    def save_current_frame(self) -> None:
        if not self.steps:
            messagebox.showinfo("Export", "Run an algorithm first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile=f"{self._safe_label()}_step_{self.step_index:03d}.png",
        )
        if not path:
            return
        img = frame_renderer.render_step(
            self.view.positions,
            self.vertices,
            self.edges,
            self.directed_var.get() and self.algorithm_var.get() == "Dijkstra",
            self.steps[self.step_index],
        )
        img.save(path)
        self._set_status(f"Saved frame to {path}")

    def export_all_frames(self) -> None:
        if not self.steps:
            messagebox.showinfo("Export", "Run an algorithm first.")
            return
        directory = filedialog.askdirectory(title="Choose output folder for frames")
        if not directory:
            return
        out_dir = os.path.join(directory, self._safe_label())
        paths = frame_renderer.export_frames(
            out_dir,
            self.view.positions,
            self.vertices,
            self.edges,
            self.directed_var.get() and self.algorithm_var.get() == "Dijkstra",
            self.steps,
            prefix=self._safe_label(),
        )
        self._set_status(f"Exported {len(self.steps)} PNG frames + GIF to {out_dir}")
        messagebox.showinfo("Export complete", f"Wrote {len(paths)} files to:\n{out_dir}")

    def _safe_label(self) -> str:
        label = self._last_run_label or "algorithm"
        return label.lower().replace(" ", "_").replace("-", "").replace("__", "_")

    # ====================================================================
    # Helpers
    # ====================================================================
    def _on_algorithm_change(self) -> None:
        is_prim = self.algorithm_var.get() == "Prim"
        is_dijkstra = not is_prim

        if is_prim and self.directed_var.get():
            self.directed_var.set(False)
            self._set_status("Prim requires an undirected graph; switched to undirected.")

        self.source_label.config(
            text="Start vertex:" if is_prim else "Source vertex:"
        )

        if is_prim:
            self.prim_partial_check.state(["!disabled"])
            self.directed_check.state(["disabled"])
        else:
            self.prim_allow_partial_var.set(False)
            self.prim_partial_check.state(["disabled"])
            self.directed_check.state(["!disabled"])

        self._render_graph()

    def _on_directed_change(self) -> None:
        if self.directed_var.get() and self.algorithm_var.get() == "Prim":
            self.directed_var.set(False)
            messagebox.showinfo("Directed", "Prim requires an undirected graph.")
            return
        self._invalidate_run()
        self._refresh_edge_list()
        self._render_graph()

    def _invalidate_run(self) -> None:
        """A graph edit makes any previous run stale."""
        self._stop_play()
        self.result = None
        self.steps = []
        self.step_index = 0
        self._update_result_panel()
        self.fringe_list.delete(0, tk.END)
        self._set_text(self.state_text, "")
        self.description_var.set("Graph changed — run an algorithm to see iterations.")
        self.step_label.config(text="Step 0 / 0")

    def _render_graph(self) -> None:
        directed = self.directed_var.get() and self.algorithm_var.get() == "Dijkstra"
        self.view.set_model(self.vertices, self.edges, directed)
        if not self.steps:
            self.view.draw()

    def _refresh_edge_list(self) -> None:
        self.edge_list.delete(0, tk.END)
        directed = self.directed_var.get() and self.algorithm_var.get() == "Dijkstra"
        if not self.edges:
            self.edge_list.insert(tk.END, "(no edges yet)")
            return
        for u, v, w in self.edges:
            arrow = "->" if directed else "-"
            label = w if not isinstance(w, float) or not float(w).is_integer() else int(w)
            self.edge_list.insert(tk.END, f"{u} {arrow} {v}  ({label})")

    def _refresh_vertex_widgets(self) -> None:
        options = self.vertices or [""]
        self._set_optionmenu(self.edge_u_menu, self.edge_u_var, options)
        self._set_optionmenu(self.edge_v_menu, self.edge_v_var, options)
        self._set_optionmenu(self.source_menu, self.source_var, options)
        if self.source_var.get() not in self.vertices:
            self.source_var.set(self.vertices[0] if self.vertices else "")
        self._refresh_edge_list()

    @staticmethod
    def _set_optionmenu(option_menu: ttk.OptionMenu, var: tk.StringVar, values: List[str]) -> None:
        menu = option_menu["menu"]
        menu.delete(0, tk.END)
        for value in values:
            menu.add_command(label=value, command=lambda v=value: var.set(v))
        if var.get() not in values:
            var.set(values[0] if values else "")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    VisualizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
