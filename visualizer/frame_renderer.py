"""Render algorithm steps to PNG frames using Pillow.

Mirrors the geometry and colors of graph_view so exported frames match the
on-screen visualizer.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import algorithm_bridge as bridge
from .graph_view import (
    EDGE_COLOR,
    FRINGE_COLOR,
    MIN_HEIGHT,
    MIN_WIDTH,
    NODE_COLOR,
    NODE_RADIUS,
    SELECTED_COLOR,
    TEXT_COLOR,
    TREE_COLOR,
    VISITED_COLOR,
    _edge_key,
)

Edge = Tuple[str, str, float]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        name = "Helvetica.ttc" if not bold else "Helvetica-Bold.ttc"
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def _trim(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float, float, float]:
    dx, dy = x2 - x1, y2 - y1
    distance = math.hypot(dx, dy) or 1
    ux, uy = dx / distance, dy / distance
    return (
        x1 + ux * NODE_RADIUS,
        y1 + uy * NODE_RADIUS,
        x2 - ux * NODE_RADIUS,
        y2 - uy * NODE_RADIUS,
    )


def render_step(
    vertices: List[str],
    edges: List[Edge],
    directed: bool,
    positions: Dict[str, Tuple[float, float]],
    step: Dict[str, Any],
    width: int = MIN_WIDTH,
    height: int = MIN_HEIGHT,
) -> Image.Image:
    """Render a single algorithm step to a Pillow image."""
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    visited_set = set(step.get("visited", []))
    fringe_vertices = {item.get("vertex") for item in (step.get("fringe") or [])}
    tree_keys = {
        _edge_key(edge["from"], edge["to"], directed) for edge in (step.get("tree_edges") or [])
    }
    selected_edge = step.get("selected_edge")
    selected_key = (
        _edge_key(selected_edge["from"], selected_edge["to"], directed)
        if selected_edge
        else None
    )
    distances = step.get("distances")
    current = step.get("current_vertex")

    for u, v, weight in edges:
        if u not in positions or v not in positions:
            continue
        x1, y1 = positions[u]
        x2, y2 = positions[v]
        key = _edge_key(u, v, directed)
        color = EDGE_COLOR
        line_width = 2
        if key in tree_keys:
            color = TREE_COLOR
            line_width = 4
        if selected_key == key:
            color = SELECTED_COLOR
            line_width = 4

        sx, sy, ex, ey = _trim(x1, y1, x2, y2)
        draw.line([(sx, sy), (ex, ey)], fill=color, width=line_width)
        if directed:
            angle = math.atan2(ey - sy, ex - sx)
            arrow_len = 14
            ax = ex - arrow_len * math.cos(angle - 0.4)
            ay = ey - arrow_len * math.sin(angle - 0.4)
            bx = ex - arrow_len * math.cos(angle + 0.4)
            by = ey - arrow_len * math.sin(angle + 0.4)
            draw.polygon([(ex, ey), (ax, ay), (bx, by)], fill=color)

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label = bridge.format_weight(weight)
        font = _font(10, bold=True)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x = max(14, tw // 2 + 8)
        draw.rectangle(
            (mx - pad_x, my - th // 2 - 4, mx + pad_x, my + th // 2 + 4),
            fill="#ffffff",
        )
        draw.text((mx - tw // 2, my - th // 2), label, fill=TEXT_COLOR, font=font)

    for vertex in vertices:
        if vertex not in positions:
            continue
        x, y = positions[vertex]
        fill = NODE_COLOR
        text_color = TEXT_COLOR
        if vertex in visited_set:
            fill = VISITED_COLOR
            text_color = "#ffffff"
        elif vertex in fringe_vertices:
            fill = FRINGE_COLOR

        outline = SELECTED_COLOR if vertex == current else "#4b5563"
        outline_width = 4 if vertex == current else 2
        r = NODE_RADIUS
        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=fill,
            outline=outline,
            width=outline_width,
        )
        vfont = _font(12, bold=True)
        vbbox = draw.textbbox((0, 0), vertex, font=vfont)
        vw, vh = vbbox[2] - vbbox[0], vbbox[3] - vbbox[1]
        draw.text((x - vw // 2, y - vh // 2), vertex, fill=text_color, font=vfont)

        if distances is not None and vertex in distances:
            dlabel = f"d={bridge.format_distance(distances[vertex])}"
            dfont = _font(10)
            dbbox = draw.textbbox((0, 0), dlabel, font=dfont)
            dw = dbbox[2] - dbbox[0]
            draw.text((x - dw // 2, y + r + 4), dlabel, fill=TEXT_COLOR, font=dfont)

    return img


def export_gif(
    steps: List[Dict[str, Any]],
    vertices: List[str],
    edges: List[Edge],
    directed: bool,
    positions: Dict[str, Tuple[float, float]],
    output_path: str,
    width: int = MIN_WIDTH,
    height: int = MIN_HEIGHT,
    duration_ms: int = 800,
) -> str:
    """Write all algorithm steps as an animated GIF. Returns the output path."""
    if not steps:
        raise ValueError("No steps to export.")

    frames = [
        render_step(vertices, edges, directed, positions, step, width, height)
        for step in steps
    ]
    first, rest = frames[0], frames[1:]
    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=0,
    )
    return output_path
