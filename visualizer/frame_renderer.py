"""
Render algorithm steps to PNG frames and an animated GIF using Pillow.

This mirrors the geometry and colors of :mod:`graph_view` so exported frames
look like the live canvas. Rendering with Pillow (rather than screenshotting the
Tk canvas) means frames can be produced reliably and even without a display,
which satisfies the assignment requirement to save iterations as ``.png``/``.gif``.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import graph_view as gv

Edge = Tuple[str, str, float]


def _font(size: int):
    for name in ("Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _text_center(draw: ImageDraw.ImageDraw, xy, text, font, fill) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((x - w / 2, y - h / 2), text, font=font, fill=fill)


def render_step(
    positions: Dict[str, Tuple[float, float]],
    vertices: List[str],
    edges: List[Edge],
    directed: bool,
    step: Dict[str, Any],
    size: Tuple[int, int] = (gv.DEFAULT_W, gv.DEFAULT_H),
    title: Optional[str] = None,
) -> Image.Image:
    """Render a single algorithm step to a Pillow image."""
    width, height = size
    img = Image.new("RGB", (width, height), gv.COLOR_BG)
    draw = ImageDraw.Draw(img)
    r = gv.NODE_RADIUS

    label_font = _font(11)
    node_font = _font(13)
    dist_font = _font(10)
    caption_font = _font(13)

    visited: Set[str] = set(step.get("visited") or [])
    current = step.get("current_vertex")
    selected = step.get("selected_edge")
    tree_keys = gv.edge_key_set(directed, step.get("tree_edges"))
    selected_key = gv.edge_key(directed, selected["from"], selected["to"]) if selected else None
    fringe_vertices = {item["vertex"]: item for item in (step.get("fringe") or [])}
    distances = step.get("distances")

    # Edges.
    for u, v, w in edges:
        if u not in positions or v not in positions:
            continue
        x1, y1 = positions[u]
        x2, y2 = positions[v]
        key = gv.edge_key(directed, u, v)
        if selected_key is not None and key == selected_key:
            color, lw = gv.COLOR_SELECTED, 4
        elif key in tree_keys:
            color, lw = gv.COLOR_TREE, 4
        else:
            color, lw = gv.COLOR_EDGE, 2

        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        sx, sy = x1 + ux * r, y1 + uy * r
        ex, ey = x2 - ux * r, y2 - uy * r
        draw.line((sx, sy, ex, ey), fill=color, width=lw)
        if directed:
            _arrow_head(draw, sx, sy, ex, ey, color)

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label = w if not isinstance(w, float) or not float(w).is_integer() else int(w)
        _text_center(draw, (mx, my), str(label), label_font, gv.COLOR_TEXT)

    # Nodes.
    for v in vertices:
        if v not in positions:
            continue
        x, y = positions[v]
        if v in visited:
            fill, text_color = gv.COLOR_NODE_VISITED, gv.COLOR_TEXT_LIGHT
        elif v in fringe_vertices:
            fill, text_color = gv.COLOR_NODE_FRINGE, gv.COLOR_TEXT
        else:
            fill, text_color = gv.COLOR_NODE, gv.COLOR_TEXT
        outline = gv.COLOR_NODE_CURRENT_OUTLINE if v == current else gv.COLOR_NODE_OUTLINE
        lw = 4 if v == current else 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=lw)
        _text_center(draw, (x, y), str(v), node_font, text_color)
        if distances is not None and v in distances:
            _text_center(draw, (x, y + r + 11), f"d={distances[v]}", dist_font, gv.COLOR_TEXT)

    caption = title or step.get("description", "")
    if caption:
        draw.rectangle((0, height - 28, width, height), fill="#f1f3f4")
        draw.text((10, height - 22), _truncate(caption, 110), font=caption_font, fill=gv.COLOR_TEXT)

    return img


def _arrow_head(draw, sx, sy, ex, ey, color) -> None:
    angle = math.atan2(ey - sy, ex - sx)
    size = 12
    for offset in (math.pi - 0.4, math.pi + 0.4):
        ax = ex + size * math.cos(angle + offset)
        ay = ey + size * math.sin(angle + offset)
        draw.line((ex, ey, ax, ay), fill=color, width=3)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def export_frames(
    output_dir: str,
    positions: Dict[str, Tuple[float, float]],
    vertices: List[str],
    edges: List[Edge],
    directed: bool,
    steps: List[Dict[str, Any]],
    prefix: str = "step",
    size: Tuple[int, int] = (gv.DEFAULT_W, gv.DEFAULT_H),
    make_gif: bool = True,
) -> List[str]:
    """Write one PNG per step and (optionally) an animated GIF. Returns paths."""
    os.makedirs(output_dir, exist_ok=True)
    paths: List[str] = []
    frames: List[Image.Image] = []
    for i, step in enumerate(steps):
        img = render_step(positions, vertices, edges, directed, step, size=size)
        path = os.path.join(output_dir, f"{prefix}_{i:03d}.png")
        img.save(path)
        paths.append(path)
        frames.append(img)

    if make_gif and frames:
        gif_path = os.path.join(output_dir, f"{prefix}.gif")
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=900,
            loop=0,
        )
        paths.append(gif_path)
    return paths
