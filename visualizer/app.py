"""Stable assignment demo visualizer for Dijkstra and Prim (PySide6)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import algorithm_bridge as bridge
from . import frame_renderer
from .graph_view import GraphView

Edge = Tuple[str, str, float]
AppMode = Literal["editing", "viewing_results"]


class App(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dijkstra and Prim Visualizer")
        self.resize(1280, 740)
        self.setMinimumSize(1020, 620)

        self.algorithm = ""
        self.fringe = "Binary Heap"
        self.graph_mode = ""
        self.preset = ""
        self.directed = False
        self.allow_partial_prim = False
        self.start = ""
        self.status_text = "Choose an algorithm to begin."
        self.readiness_text = "Blocked: choose an algorithm."

        self.vertices: List[str] = []
        self.edges: List[Edge] = []
        self.graph_source = "empty"
        self.loaded_preset: Optional[str] = None

        self.result: Optional[Dict[str, Any]] = None
        self.steps: List[Dict[str, Any]] = []
        self.step_index = 0
        self.is_running = False
        self.mode: AppMode = "editing"

        self._build()
        self._set_preset_options([])
        self._sync_state()

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(300)
        left_scroll.setMaximumWidth(340)

        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 4, 0)
        self._build_controls(left_layout)
        left_layout.addStretch()
        left_scroll.setWidget(left_content)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        self.view = GraphView()
        center_layout.addWidget(self.view)

        right = QWidget()
        right.setMinimumWidth(320)
        right.setMaximumWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._build_right_panel(right_layout)

        splitter.addWidget(left_scroll)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([300, 640, 320])

    def _build_controls(self, parent: QVBoxLayout) -> None:
        step1 = QGroupBox("1. Algorithm")
        step1_layout = QVBoxLayout(step1)
        self.algorithm_widgets: List[QWidget] = []
        self.algorithm_group = QButtonGroup(self)
        for name in bridge.ALGORITHMS:
            radio = QRadioButton(name)
            radio.toggled.connect(lambda checked, n=name: self._on_algorithm_toggled(checked, n))
            self.algorithm_group.addButton(radio)
            step1_layout.addWidget(radio)
            self.algorithm_widgets.append(radio)
        parent.addWidget(step1)

        step2 = QGroupBox("2. Graph")
        step2_layout = QVBoxLayout(step2)
        self.graph_widgets: List[QWidget] = []
        self.preset_widgets: List[QWidget] = []
        self.vertex_widgets: List[QWidget] = []
        self.edge_widgets: List[QWidget] = []
        self.graph_mode_group = QButtonGroup(self)

        for label, value in (("Load preset", "preset"), ("Create from scratch", "manual")):
            radio = QRadioButton(label)
            radio.toggled.connect(lambda checked, v=value: self._on_graph_mode_toggled(checked, v))
            self.graph_mode_group.addButton(radio)
            step2_layout.addWidget(radio)
            self.graph_widgets.append(radio)

        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self._choose_preset)
        step2_layout.addWidget(self.preset_combo)
        self.preset_widgets.append(self.preset_combo)

        self.load_preset_button = QPushButton("Load selected preset")
        self.load_preset_button.clicked.connect(self.load_preset)
        step2_layout.addWidget(self.load_preset_button)
        self.preset_widgets.append(self.load_preset_button)

        self.manual_frame = QWidget()
        manual_layout = QVBoxLayout(self.manual_frame)
        manual_layout.setContentsMargins(0, 8, 0, 0)

        vertex_row = QHBoxLayout()
        vertex_row.addWidget(QLabel("Vertex"))
        self.vertex_entry = QLineEdit()
        self.vertex_entry.returnPressed.connect(self.add_vertex)
        vertex_row.addWidget(self.vertex_entry, stretch=1)
        self.add_vertex_button = QPushButton("Add")
        self.add_vertex_button.clicked.connect(self.add_vertex)
        vertex_row.addWidget(self.add_vertex_button)
        manual_layout.addLayout(vertex_row)
        self.vertex_widgets.extend([self.vertex_entry, self.add_vertex_button])

        edge_label = QLabel("Edge")
        manual_layout.addWidget(edge_label)

        edge_row = QHBoxLayout()
        self.u_combo = QComboBox()
        self.v_combo = QComboBox()
        edge_row.addWidget(self.u_combo, stretch=1)
        edge_row.addWidget(self.v_combo, stretch=1)
        manual_layout.addLayout(edge_row)
        self.edge_widgets.extend([self.u_combo, self.v_combo])

        weight_row = QHBoxLayout()
        self.weight_entry = QLineEdit("1")
        self.weight_entry.returnPressed.connect(self.add_edge)
        weight_row.addWidget(self.weight_entry, stretch=1)
        self.add_edge_button = QPushButton("Add edge")
        self.add_edge_button.clicked.connect(self.add_edge)
        weight_row.addWidget(self.add_edge_button)
        manual_layout.addLayout(weight_row)
        self.edge_widgets.extend([self.weight_entry, self.add_edge_button])

        self.directed_check = QCheckBox("Directed edges")
        self.directed_check.toggled.connect(self._on_directed_change)
        manual_layout.addWidget(self.directed_check)

        self.clear_button = QPushButton("Clear graph")
        self.clear_button.clicked.connect(self.clear_graph)
        manual_layout.addWidget(self.clear_button)

        step2_layout.addWidget(self.manual_frame)

        self.graph_summary_label = QLabel("No graph loaded.")
        self.graph_summary_label.setWordWrap(True)
        step2_layout.addWidget(self.graph_summary_label)
        parent.addWidget(step2)

        step3 = QGroupBox("3. Run")
        step3_layout = QVBoxLayout(step3)
        self.fringe_widgets: List[QWidget] = []
        step3_layout.addWidget(QLabel("Fringe"))
        self.fringe_group = QButtonGroup(self)
        for name in bridge.FRINGES:
            radio = QRadioButton(name)
            radio.setChecked(name == self.fringe)
            radio.toggled.connect(lambda checked, n=name: self._on_fringe_toggled(checked, n))
            self.fringe_group.addButton(radio)
            step3_layout.addWidget(radio)
            self.fringe_widgets.append(radio)

        step3_layout.addWidget(QLabel("Source / start"))
        self.start_combo = QComboBox()
        self.start_combo.currentTextChanged.connect(self._on_start_change)
        step3_layout.addWidget(self.start_combo)

        self.partial_check = QCheckBox("Allow disconnected Prim")
        self.partial_check.toggled.connect(self._on_partial_prim_change)
        step3_layout.addWidget(self.partial_check)

        self.run_button = QPushButton("Run algorithm")
        self.run_button.clicked.connect(self.run)
        step3_layout.addWidget(self.run_button)

        self.readiness_label = QLabel(self.readiness_text)
        self.readiness_label.setWordWrap(True)
        step3_layout.addWidget(self.readiness_label)
        parent.addWidget(step3)

        step4 = QGroupBox("4. Step through")
        step4_layout = QVBoxLayout(step4)
        self.playback_widgets: List[QWidget] = []
        row = QHBoxLayout()
        for text, handler in (
            ("|<", self.first),
            ("Back", self.back),
            ("Next", self.next),
            (">|", self.last),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            row.addWidget(button)
            self.playback_widgets.append(button)
        step4_layout.addLayout(row)
        self.step_label = QLabel("Step 0 / 0")
        step4_layout.addWidget(self.step_label)
        parent.addWidget(step4)

        step5 = QGroupBox("5. Export / Reset")
        step5_layout = QVBoxLayout(step5)
        self.export_gif_button = QPushButton("Export GIF")
        self.export_gif_button.clicked.connect(self.export_gif)
        step5_layout.addWidget(self.export_gif_button)
        self.reset_button = QPushButton("Reset / Edit Graph")
        self.reset_button.clicked.connect(self.reset_to_editing)
        step5_layout.addWidget(self.reset_button)
        parent.addWidget(step5)

        self.status_label = QLabel(self.status_text)
        self.status_label.setWordWrap(True)
        self.status_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.status_label.setFrameShadow(QFrame.Shadow.Sunken)
        self.status_label.setContentsMargins(5, 5, 5, 5)
        parent.addWidget(self.status_label)

    def _build_right_panel(self, parent: QVBoxLayout) -> None:
        step_box = QGroupBox("Current step")
        step_layout = QVBoxLayout(step_box)
        self.step_text = QTextEdit()
        self.step_text.setReadOnly(True)
        self.step_text.setFontFamily("Menlo")
        self.step_text.setMinimumHeight(200)
        step_layout.addWidget(self.step_text)
        parent.addWidget(step_box, stretch=1)

        result_box = QGroupBox("Result")
        result_layout = QVBoxLayout(result_box)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFontFamily("Menlo")
        self.result_text.setMinimumHeight(200)
        result_layout.addWidget(self.result_text)
        parent.addWidget(result_box, stretch=1)

    def _on_algorithm_toggled(self, checked: bool, name: str) -> None:
        if not checked:
            return
        if self.mode == "viewing_results":
            self.reset_to_editing()
        self.algorithm = name
        self.graph_mode = ""
        self.preset = ""
        self.directed = False
        self.directed_check.setChecked(False)
        self.allow_partial_prim = False
        self.partial_check.setChecked(False)
        for button in self.graph_mode_group.buttons():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)
        self._set_preset_options(bridge.preset_labels(name))
        self._replace_graph([], [], False, "", source="empty", reset_layout=True)
        self.status_text = "Choose a preset or create a graph."
        self._sync_state()

    def _on_graph_mode_toggled(self, checked: bool, value: str) -> None:
        if not checked:
            return
        if self.mode == "viewing_results":
            self.reset_to_editing()
        self.graph_mode = value
        self.loaded_preset = None
        if value == "manual":
            self._replace_graph([], [], self.directed, "", source="manual", reset_layout=True)
            self.status_text = "Manual graph started."
        elif value == "preset":
            self._replace_graph([], [], False, "", source="empty", reset_layout=True)
            self.status_text = "Select and load a preset."
        else:
            self._replace_graph([], [], False, "", source="empty", reset_layout=True)
        self._sync_state()

    def _on_fringe_toggled(self, checked: bool, name: str) -> None:
        if checked:
            self.fringe = name
            self._invalidate_run()

    def _on_partial_prim_change(self, checked: bool) -> None:
        self.allow_partial_prim = checked
        self._invalidate_run()

    def _set_mode(self, mode: AppMode) -> None:
        self.mode = mode
        if mode == "editing":
            self.view.unfreeze_layout()
        elif mode == "viewing_results":
            self.view.freeze_layout()
        self._sync_state()

    def reset_to_editing(self) -> None:
        self.result = None
        self.steps = []
        self.step_index = 0
        self.step_label.setText("Step 0 / 0")
        self._write(self.result_text, "")
        self._write(self.step_text, "")
        self._set_mode("editing")
        self.view.draw()
        self.status_text = "Returned to editing mode. Graph is unchanged."
        self._sync_state()

    def _set_preset_options(self, labels: List[str]) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(labels)
        self.preset = labels[0] if labels else ""
        self.preset_combo.blockSignals(False)

    def _choose_preset(self, label: str) -> None:
        self.preset = label
        if self.graph_mode == "preset" and self.graph_source == "preset" and self.loaded_preset != label:
            self._replace_graph([], [], False, "", source="empty", reset_layout=True)
            self.status_text = "Preset changed. Load the selected preset."
        self._sync_state()

    def load_preset(self) -> None:
        if not self._can_edit_graph("Load a preset"):
            return

        if not self.algorithm:
            self.status_text = "Choose an algorithm first."
            self._sync_state()
            return

        self.graph_mode = "preset"
        try:
            preset = bridge.get_preset(self.preset, algorithm=self.algorithm)
        except ValueError as exc:
            QMessageBox.critical(self, "Preset", str(exc))
            self.status_text = str(exc)
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
        self.status_text = f"Loaded {preset.label}."

    def add_vertex(self) -> None:
        if not self._can_edit_manual_graph("Add a vertex"):
            return
        self._add_vertex(self.vertex_entry.text().strip())

    def _add_vertex(self, vertex: str) -> None:
        if not vertex:
            QMessageBox.warning(self, "Vertex", "Enter a vertex name.")
            return
        if vertex in self.vertices:
            QMessageBox.information(self, "Vertex", f"{vertex} already exists.")
            return

        self.vertices.append(vertex)
        self.vertices.sort(key=str)
        self.graph_source = "manual"
        self.loaded_preset = None

        if not self.start:
            self.start = vertex
        if not self.u_combo.currentText():
            self._set_combo(self.u_combo, self.vertices, vertex)
        elif not self.v_combo.currentText() and self.u_combo.currentText() != vertex:
            self._set_combo(self.v_combo, self.vertices, vertex)

        self.vertex_entry.clear()
        self._invalidate_run(sync=False)
        self._refresh_graph()
        self.status_text = f"Added vertex {vertex}."

    def add_edge(self) -> None:
        if not self._can_edit_manual_graph("Add an edge"):
            return
        self._add_edge_between(self.u_combo.currentText().strip(), self.v_combo.currentText().strip())

    def _add_edge_between(self, u: str, v: str) -> None:
        if len(self.vertices) < 2:
            self.status_text = "Add at least two vertices before connecting them."
            self._sync_state()
            return
        if u not in self.vertices or v not in self.vertices or u == v:
            QMessageBox.warning(self, "Edge", "Choose two different vertices.")
            return

        try:
            weight = bridge.parse_weight(self.weight_entry.text(), self.algorithm)
        except ValueError as exc:
            QMessageBox.critical(self, "Edge", str(exc))
            self.status_text = str(exc)
            return

        directed = self.directed and self.algorithm == "Dijkstra"
        for index, (eu, ev, _old_weight) in enumerate(self.edges):
            same_edge = (eu, ev) == (u, v) if directed else {eu, ev} == {u, v}
            if same_edge:
                self.edges[index] = (u, v, weight)
                break
        else:
            self.edges.append((u, v, weight))

        self.graph_source = "manual"
        self.loaded_preset = None
        self._set_combo(self.u_combo, self.vertices, u)
        self._set_combo(self.v_combo, self.vertices, v)
        self._invalidate_run(sync=False)
        self._refresh_graph()

        arrow = "->" if directed else "-"
        self.status_text = f"Added edge {u} {arrow} {v} with weight {bridge.format_weight(weight)}."

    def _can_edit_graph(self, action: str) -> bool:
        if self.mode == "viewing_results":
            self.status_text = f"{action}: use Reset / Edit Graph first."
            return False
        if self.is_running:
            self.status_text = "Wait for the current run to finish."
            return False
        return True

    def _can_edit_manual_graph(self, action: str) -> bool:
        if not self._can_edit_graph(action):
            return False
        if not self.algorithm:
            self.status_text = f"{action}: choose an algorithm first."
            self._sync_state()
            return False
        if self.graph_mode != "manual":
            self.status_text = f"{action}: choose Create from scratch first."
            self._sync_state()
            return False
        return True

    def _on_directed_change(self, checked: bool) -> None:
        if not self._can_edit_graph("Change edge direction"):
            self.directed_check.blockSignals(True)
            self.directed_check.setChecked(self.directed)
            self.directed_check.blockSignals(False)
            return

        if self.algorithm != "Dijkstra":
            self.directed = False
            self.directed_check.blockSignals(True)
            self.directed_check.setChecked(False)
            self.directed_check.blockSignals(False)
            self.status_text = "Prim uses undirected edges."
            self._sync_state()
            return

        self.directed = checked
        merged = 0
        if not self.directed:
            merged = self._merge_undirected_duplicates()

        self._invalidate_run(sync=False)
        self._refresh_graph()
        if merged:
            self.status_text = f"Switched to undirected edges and merged {merged} duplicate pair(s)."
        else:
            mode = "directed" if self.directed else "undirected"
            self.status_text = f"Switched to {mode} edges."

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
        if not self._can_edit_graph("Clear graph"):
            return
        source = "manual" if self.graph_mode == "manual" else "empty"
        self._replace_graph([], [], self.directed, "", source=source, reset_layout=True)
        if not quiet:
            self.status_text = "Graph cleared."

    def run(self) -> None:
        errors = self._run_validation_errors()
        if errors:
            message = "Cannot run yet:\n" + "\n".join(f"- {error}" for error in errors)
            self._invalidate_run(sync=True)
            self._write(self.step_text, message)
            self.status_text = errors[0]
            return

        start = self.start
        self._set_running(True)
        self.status_text = f"Running {self.algorithm} from {start}..."
        QApplication.processEvents()

        try:
            self.result = bridge.run_algorithm(
                algorithm=self.algorithm,
                fringe=self.fringe,
                vertices=self.vertices,
                edges=self.edges,
                start=start,
                directed=self.directed,
                allow_partial_prim=self.allow_partial_prim,
            )
        except ValueError as exc:
            self._invalidate_run(sync=False)
            self._write(self.step_text, str(exc))
            self.status_text = str(exc)
            return
        except Exception as exc:
            self._invalidate_run(sync=False)
            self._write(self.step_text, f"Run failed: {exc}")
            self.status_text = f"Run failed: {exc}"
            return
        finally:
            self._set_running(False)

        self.steps = self.result.get("steps", [])
        self.step_index = 0
        self._render_result()
        self._set_mode("viewing_results")
        self.show_step(0)
        self.status_text = (
            f"{self.algorithm} finished with {len(self.steps)} recorded steps. Use step controls to review."
        )

    def export_gif(self) -> None:
        if self.mode != "viewing_results" or not self.steps:
            self.status_text = "Run an algorithm first, then export frames."
            return

        prefix = f"{self.algorithm.lower()}_{self.fringe.replace(' ', '_').lower()}"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save GIF animation",
            f"{prefix}.gif",
            "GIF files (*.gif)",
        )
        if not path:
            return

        try:
            directed = self.directed and self.algorithm == "Dijkstra"
            width, height = self.view.export_canvas_size()
            frame_renderer.export_gif(
                steps=self.steps,
                vertices=self.vertices,
                edges=self.edges,
                directed=directed,
                positions=dict(self.view.positions),
                output_path=path,
                width=width,
                height=height,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export", f"GIF export failed: {exc}")
            self.status_text = f"GIF export failed: {exc}"
            return

        self.status_text = f"Exported GIF to {path}."

    def _run_validation_errors(self) -> List[str]:
        errors = self._flow_issues()
        if errors:
            return errors

        try:
            bridge.validate_graph_inputs(
                algorithm=self.algorithm,
                fringe=self.fringe,
                vertices=self.vertices,
                edges=self.edges,
                start=self.start,
                directed=self.directed and self.algorithm == "Dijkstra",
            )
        except ValueError as exc:
            return [str(exc)]
        return []

    def _flow_issues(self) -> List[str]:
        mode = self.graph_mode
        issues: List[str] = []

        if not self.algorithm:
            return ["choose an algorithm"]

        if mode not in {"preset", "manual"}:
            issues.append("choose how to create the graph")
        elif mode == "preset" and self.graph_source != "preset":
            issues.append("load the selected preset")
        elif mode == "manual" and not self.vertices:
            issues.append("add at least one vertex")

        if self.vertices and self.start not in self.vertices:
            issues.append("choose a valid source/start vertex")

        if (
            self.algorithm == "Prim"
            and self.vertices
            and self.start in self.vertices
            and not self.allow_partial_prim
        ):
            reachable = self._reachable_vertices(self.start)
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
            self.step_label.setText("Step 0 / 0")
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
        self.step_label.setText(f"Step {self.step_index + 1} / {len(self.steps)}")
        self._render_step(step)
        self._sync_state()

    def first(self) -> None:
        self.show_step(0)

    def back(self) -> None:
        self.show_step(self.step_index - 1)

    def next(self) -> None:
        self.show_step(self.step_index + 1)

    def last(self) -> None:
        self.show_step(len(self.steps) - 1)

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
        self.directed = bool(directed and self.algorithm == "Dijkstra")
        self.directed_check.blockSignals(True)
        self.directed_check.setChecked(self.directed)
        self.directed_check.blockSignals(False)
        self.start = start if start in self.vertices else (self.vertices[0] if self.vertices else "")
        self._invalidate_run(sync=False)
        self._refresh_graph(reset_layout=reset_layout)

    def _refresh_graph(self, reset_layout: bool = False) -> None:
        directed = self.directed and self.algorithm == "Dijkstra"
        self.view.set_graph(self.vertices, self.edges, directed)
        if reset_layout:
            self.view.reset_layout()
        else:
            self.view.draw()
        self._refresh_menus()
        self._update_graph_summary()
        self._sync_state()

    def _refresh_menus(self) -> None:
        self._set_combo(self.u_combo, self.vertices, self.u_combo.currentText())
        self._set_combo(self.v_combo, self.vertices, self.v_combo.currentText())
        self._set_combo(self.start_combo, self.vertices, self.start)

    def _on_start_change(self, value: str) -> None:
        if value:
            self.start = value
            self._invalidate_run(sync=True)
            self.status_text = f"Start vertex set to {value}."

    @staticmethod
    def _set_combo(combo: QComboBox, values: List[str], current: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(values)
        if current in values:
            combo.setCurrentText(current)
        elif values:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _update_graph_summary(self) -> None:
        if not self.vertices:
            if self.graph_mode == "manual":
                text = "Manual graph is empty."
            elif self.graph_mode == "preset":
                text = "No preset loaded."
            else:
                text = "No graph loaded."
            self.graph_summary_label.setText(text)
            return

        source = "Manual graph"
        if self.graph_source == "preset" and self.loaded_preset:
            source = f"Preset: {self.loaded_preset}"
        directed = "directed" if self.directed and self.algorithm == "Dijkstra" else "undirected"
        self.graph_summary_label.setText(f"{source}. V={len(self.vertices)} E={len(self.edges)} {directed}.")

    def _invalidate_run(self, sync: bool = True) -> None:
        if self.mode == "viewing_results":
            self.mode = "editing"
            self.view.unfreeze_layout()
        self.result = None
        self.steps = []
        self.step_index = 0
        self.step_label.setText("Step 0 / 0")
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
        editing = self.mode == "editing"
        viewing = self.mode == "viewing_results"
        has_algorithm = bool(self.algorithm)
        has_graph = bool(self.vertices)
        manual_mode = editing and has_algorithm and self.graph_mode == "manual"
        preset_mode = editing and has_algorithm and self.graph_mode == "preset"
        idle = not self.is_running
        issues = self._flow_issues() if editing else []
        can_run = editing and idle and not issues
        has_steps = bool(self.steps)

        self._configure_widgets(self.algorithm_widgets, editing and idle)
        self._configure_widgets(self.graph_widgets, editing and idle and has_algorithm)
        self._configure_widgets(self.preset_widgets, editing and idle and preset_mode)
        self._configure_widgets(self.vertex_widgets, editing and idle and manual_mode)
        self._configure_widgets(
            self.edge_widgets, editing and idle and manual_mode and len(self.vertices) >= 2
        )

        directed_enabled = editing and idle and manual_mode and self.algorithm == "Dijkstra"
        self.directed_check.setEnabled(directed_enabled)
        clear_enabled = editing and idle and manual_mode and has_graph
        self.clear_button.setEnabled(clear_enabled)

        run_controls_enabled = editing and idle and has_algorithm and has_graph
        self._configure_widgets(self.fringe_widgets, run_controls_enabled)
        self.start_combo.setEnabled(run_controls_enabled)
        prim_partial_enabled = run_controls_enabled and self.algorithm == "Prim"
        self.partial_check.setEnabled(prim_partial_enabled)
        self.run_button.setEnabled(can_run)
        self.run_button.setText("Running..." if self.is_running else "Run algorithm")

        playback_enabled = viewing and idle and has_steps
        self._configure_widgets(self.playback_widgets, playback_enabled)
        self.export_gif_button.setEnabled(playback_enabled)
        self.reset_button.setEnabled(viewing and idle)

        if self.is_running:
            self.readiness_text = "Running..."
        elif viewing:
            self.readiness_text = f"Viewing results. Step {self.step_index + 1} of {len(self.steps)}."
        elif issues:
            self.readiness_text = "Blocked: " + "; ".join(issues) + "."
        else:
            self.readiness_text = "Ready to run."

        self.readiness_label.setText(self.readiness_text)
        self.status_label.setText(self.status_text)

    @staticmethod
    def _configure_widgets(widgets: List[QWidget], enabled: bool) -> None:
        for widget in widgets:
            widget.setEnabled(enabled)

    def _set_running(self, running: bool) -> None:
        self.is_running = running
        self._sync_state()

    @staticmethod
    def _write(widget: QTextEdit, text: str) -> None:
        widget.setPlainText(text)


def main() -> None:
    app = QApplication([])
    window = App()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
