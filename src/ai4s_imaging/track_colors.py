"""Stable model-predicted cell identity colors; cautious visual lineage candidates.

The rendered colors do not establish real cellular identities or confirmed
mother/daughter relationships. Never use reference masks as display input.
"""
from __future__ import annotations

import colorsys
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion


@dataclass(frozen=True)
class TrackColor:
    rgb: tuple[int, int, int]
    origin_id: int
    lineage_candidate: bool = False


def stable_rgb(track_id: int) -> tuple[int, int, int]:
    """Deterministic hue keyed by tracking ID, never by instance-mask label."""
    if isinstance(track_id, (bool, np.bool_)) or int(track_id) != track_id or track_id < 0:
        raise ValueError("track_id must be a nonnegative integer")
    hue = ((int(track_id) * 137.50776405) + 192.0) % 360.0 / 360.0
    rgb = colorsys.hsv_to_rgb(hue, 0.75, 0.95)
    return tuple(round(255.0 * channel) for channel in rgb)


def track_color_map(
    nodes: pd.DataFrame,
    lineage_edges: pd.DataFrame | None = None,
) -> dict[int, TrackColor]:
    """Stable colors with derived daughter shades for unambiguous *candidates*.

    A candidate is accepted only if the parent stops in frame t and exactly two
    children begin in t+1, both candidate edges originate from that parent,
    and neither child has another candidate parent. This is stricter than the
    underlying spatial heuristic, but not proof of a biological division.
    """
    required = {"node_id", "track_id", "t"}
    if not required.issubset(nodes):
        raise ValueError("nodes missing identity or timestamp")
    if nodes[list(required)].isna().any().any():
        raise ValueError("null identity fields")
    if nodes["node_id"].duplicated().any():
        raise ValueError("duplicate detection node_id")
    if nodes[["track_id", "t"]].duplicated().any():
        raise ValueError("duplicate time for predicted track")
    colors = {int(i): TrackColor(stable_rgb(int(i)), int(i))
              for i in sorted(nodes["track_id"].unique())}
    if lineage_edges is None or lineage_edges.empty:
        return colors
    if not {"source_id", "target_id", "edge_type"}.issubset(lineage_edges):
        raise ValueError("lineage_edges missing columns")
    indexed = nodes.set_index("node_id")
    first = nodes.groupby("track_id")["t"].min().to_dict()
    last = nodes.groupby("track_id")["t"].max().to_dict()
    candidates = []
    incoming = Counter()
    for edge in lineage_edges.itertuples(index=False):
        if str(edge.edge_type) != "division_parent":
            continue
        src, dst = int(edge.source_id), int(edge.target_id)
        if src not in indexed.index or dst not in indexed.index:
            raise ValueError("division candidate references unknown detected node")
        p, c = indexed.loc[src], indexed.loc[dst]
        pid, cid = int(p.track_id), int(c.track_id)
        if pid == cid:
            continue
        if (int(c.t) == int(p.t) + 1
                and last[pid] == p.t and first[cid] == c.t):
            candidates.append((pid, cid, int(p.t)))
            incoming[cid] += 1
    events = defaultdict(set)
    for pid, cid, t in candidates:
        if incoming[cid] == 1:
            events[pid, t].add(cid)
    for (pid, t), daughters in sorted(events.items()):
        if len(daughters) != 2:
            continue
        if any(colors[c].lineage_candidate for c in daughters):
            continue
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in colors[pid].rgb))
        for offset, cid in zip((-15, 15), sorted(daughters)):
            rgb = colorsys.hsv_to_rgb(((h * 360 + offset) % 360) / 360, .83, .99)
            colors[cid] = TrackColor(tuple(round(x * 255) for x in rgb),
                                     colors[pid].origin_id, True)
    return colors


def _font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans"
            + ("-Bold" if bold else "") + ".ttf", size)
    except OSError:
        return ImageFont.load_default()


def tracked_color_overlay(
    raw: np.ndarray,
    masks: np.ndarray,
    nodes: pd.DataFrame,
    t: int,
    colors: dict[int, TrackColor],
    *,
    hero_track: int | None = None,
    max_trail: int = 24,
) -> Image.Image:
    """Overlay matching predicted mask IDs with stable tracking IDs.

    Trails contain observed history up to current frame, connecting only
    adjacent observed times: no lookahead, no interpolated positions.
    """
    a, m = np.asarray(raw), np.asarray(masks)
    if a.ndim != 2 or m.shape != a.shape or not np.issubdtype(m.dtype, np.integer):
        raise ValueError("expected 2D real microscope frame and integer prediction mask")
    if not np.isfinite(a).all() or (m < 0).any():
        raise ValueError("invalid image or predicted labels")
    required = {"t", "track_id", "instance_id", "x", "y"}
    if not required.issubset(nodes):
        raise ValueError("tracked detections missing instance_id and coordinates")
    current = nodes[nodes["t"].eq(t)]
    if current["instance_id"].duplicated().any():
        raise ValueError("ambiguous mask-to-track identity at frame")
    if {int(v) for v in np.unique(m) if v > 0} != {
        int(v) for v in current["instance_id"]
    }:
        raise ValueError("predicted instances do not match tracked detection labels")
    if not set(int(v) for v in nodes["track_id"]).issubset(colors):
        raise ValueError("missing track colors")
    lo, hi = np.percentile(a.astype(float), [1, 99])
    pixels = (np.uint8(np.clip((a-lo)/(hi-lo), 0, 1)*255)
              if hi > lo else np.zeros_like(a, dtype=np.uint8))
    under = Image.fromarray(pixels, "L").convert("RGBA")
    rgba = np.zeros((*m.shape, 4), dtype=np.uint8)
    for row in current.itertuples(index=False):
        part = m == int(row.instance_id)
        rgb = colors[int(row.track_id)].rgb
        border = binary_dilation(part, iterations=1) & ~binary_erosion(part)
        rgba[part] = (*rgb, 94 if hero_track == row.track_id else 49)
        rgba[border] = (*rgb, 235)
    result = Image.alpha_composite(under, Image.fromarray(rgba, "RGBA")).convert("RGB")
    draw = ImageDraw.Draw(result)
    past = nodes[nodes["t"].le(t) & nodes["t"].gt(t - max_trail)]
    for ident, group in past.groupby("track_id"):
        if hero_track is not None and ident != hero_track:
            continue
        points = list(group.sort_values("t").itertuples(index=False))
        for before, after in zip(points, points[1:]):
            if int(after.t) - int(before.t) == 1:
                draw.line([(float(before.x),float(before.y)),
                           (float(after.x),float(after.y))],
                          fill=colors[int(ident)].rgb,
                          width=4 if ident == hero_track else 2)
    for row in current.itertuples(index=False):
        x,y = float(row.x),float(row.y)
        rgb = colors[int(row.track_id)].rgb
        radius = 5 if hero_track == row.track_id else 3
        draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill=rgb,
                     outline=(255,255,255), width=1)
        if hero_track is None or hero_track == row.track_id:
            draw.text((max(0,x+8),max(0,y-15)), str(int(row.track_id)),
                      fill=(245,246,247), font=_font(14,True),
                      stroke_width=2, stroke_fill=(8,15,22))
    return result
