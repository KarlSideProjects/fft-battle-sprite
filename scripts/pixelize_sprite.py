"""Downsample high-resolution generated sprite sheets into crisp pixel art.

A plain area-average resize turns a generated "pixel art" render into mush: the
generator's blocks do not land on the target grid, so every output pixel is an
average of several source colours. This samples the *modal* colour of each
source block instead, which keeps hard edges, then rebuilds the 1px outline the
averaging would otherwise eat.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

OUTLINE_RGB = np.array([26, 20, 32], dtype=np.int16)
OUTLINE_MIX = 0.70
ALPHA_ON = 0.45
# Buckets used only to make block modes stable against generator noise. Keep
# this generous: it must not become the step that picks the palette. At 64 a
# small high-chroma element -- a steel blade among browns -- gets merged into
# the dominant hue before the mode is even taken, and no later setting can
# bring it back. The real budget is --colors.
MODE_COLORS = 256


def cells(sheet: Image.Image, rows: int, cols: int) -> list[Image.Image]:
    w, h = sheet.size
    cw, ch = w // cols, h // rows
    return [sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            for r in range(rows) for c in range(cols)]


def bbox_of(cell: Image.Image) -> tuple[int, int, int, int]:
    a = np.array(cell)
    ys, xs = np.nonzero(a[..., 3] > 8)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def mode_downsample(crop: Image.Image, tw: int, th: int) -> np.ndarray:
    ca = np.array(crop)
    bh, bw = ca.shape[:2]
    q = Image.fromarray(ca[..., :3]).quantize(
        colors=MODE_COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = np.array(q.getpalette()[:MODE_COLORS * 3]).reshape(-1, 3)
    idx = np.array(q)
    alpha = ca[..., 3]
    out = np.zeros((th, tw, 4), dtype=np.uint8)
    for j in range(th):
        sy0, sy1 = int(j * bh / th), max(int(j * bh / th) + 1, int((j + 1) * bh / th))
        for i in range(tw):
            sx0, sx1 = int(i * bw / tw), max(int(i * bw / tw) + 1, int((i + 1) * bw / tw))
            m = alpha[sy0:sy1, sx0:sx1] > 128
            if m.mean() < ALPHA_ON:
                continue
            hit = Counter(idx[sy0:sy1, sx0:sx1][m].tolist()).most_common(1)[0][0]
            out[j, i, :3] = pal[hit]
            out[j, i, 3] = 255
    return out


def despeckle(px: np.ndarray) -> np.ndarray:
    """Flatten single pixels that share no colour with any 4-neighbour."""
    out = px.copy()
    h, w = px.shape[:2]
    for y in range(h):
        for x in range(w):
            if px[y, x, 3] == 0:
                continue
            neigh = []
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and px[ny, nx, 3] > 0:
                    neigh.append(tuple(px[ny, nx, :3].tolist()))
            if not neigh:
                continue
            here = tuple(px[y, x, :3].tolist())
            if here in neigh:
                continue
            colour, count = Counter(neigh).most_common(1)[0]
            if count >= 3:
                out[y, x, :3] = colour
    return out


def reoutline(px: np.ndarray) -> np.ndarray:
    out = px.copy()
    op = px[..., 3] > 0
    pad = np.pad(op, 1, constant_values=False)
    exposed = (~pad[:-2, 1:-1]) | (~pad[2:, 1:-1]) | (~pad[1:-1, :-2]) | (~pad[1:-1, 2:])
    edge = op & exposed
    out[edge, :3] = (px[edge, :3].astype(np.int16) * (1 - OUTLINE_MIX)
                     + OUTLINE_RGB * OUTLINE_MIX).astype(np.uint8)
    return out


def clamp_palette(frames: list[np.ndarray], colors: int) -> list[np.ndarray]:
    """Force every frame onto one shared palette.

    Quantising each frame on its own gives each one a slightly different set of
    colours, which makes the sprite shimmer as the animation cycles.
    """
    opaque = [f[..., 3] > 0 for f in frames]
    pool = np.concatenate([f[..., :3][m] for f, m in zip(frames, opaque)])
    q = Image.fromarray(pool.reshape(-1, 1, 3)).quantize(
        colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = np.array(q.getpalette()[:colors * 3]).reshape(-1, 3)
    mapped = pal[np.array(q).reshape(-1)]
    out, cursor = [], 0
    for frame, mask in zip(frames, opaque):
        n = int(mask.sum())
        clone = frame.copy()
        clone[..., :3][mask] = mapped[cursor:cursor + n]
        cursor += n
        out.append(clone)
    return out


def feet_center(px: np.ndarray, band: float = 0.15) -> float:
    """Horizontal centre of the bottom slice of the body.

    Centring on the whole bounding box makes the character slide sideways the
    moment a pose reaches out — an extended whip or sword drags the box with it.
    The feet stay put through every pose, so they are the honest anchor.
    """
    h = px.shape[0]
    rows = px[max(0, h - max(1, round(h * band))):, :, 3] > 0
    xs = np.nonzero(rows.any(axis=0))[0]
    return float(xs.mean()) if xs.size else px.shape[1] / 2.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", action="append", required=True,
                    metavar="PATH:ROWS:COLS:NAME[,NAME...]")
    ap.add_argument("--cell", type=int, required=True)
    ap.add_argument("--body-frac", type=float, default=0.70)
    ap.add_argument("--feet-margin", type=int, default=3)
    ap.add_argument("--colors", type=int, default=32,
                    help="shared palette size across all frames")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    jobs: list[tuple[Image.Image, str]] = []
    for spec in args.sheet:
        path, rows, cols, names = spec.split(":")
        sheet = Image.open(path).convert("RGBA")
        frames = cells(sheet, int(rows), int(cols))
        for cell, name in zip(frames, names.split(",")):
            jobs.append((cell, name))

    # One shared scale for every frame: the tallest body defines the budget, so
    # no frame overflows the cell and none of them jitter in size at runtime.
    boxes = [bbox_of(c) for c, _ in jobs]
    tallest = max(b[3] - b[1] for b in boxes)
    target_h = round(args.cell * args.body_frac)
    scale = target_h / tallest

    rendered: list[np.ndarray] = []
    for (cell, name), box in zip(jobs, boxes):
        bw, bh = box[2] - box[0], box[3] - box[1]
        tw, th = max(1, round(bw * scale)), max(1, round(bh * scale))
        px = reoutline(despeckle(mode_downsample(cell.crop(box), tw, th)))
        canvas = np.zeros((args.cell, args.cell, 4), dtype=np.uint8)
        ox = round(args.cell / 2.0 - feet_center(px))
        oy = args.cell - th - args.feet_margin
        if ox < 0 or ox + tw > args.cell or oy < 0:
            raise SystemExit(
                f"{name}: body {tw}x{th} anchored at x={ox} does not fit a "
                f"{args.cell}px cell — the pose reaches too far from the feet"
            )
        canvas[oy:oy + th, ox:ox + tw] = px
        rendered.append(canvas)

    rendered = clamp_palette(rendered, args.colors)

    args.out.mkdir(parents=True, exist_ok=True)
    for (_, name), frame in zip(jobs, rendered):
        Image.fromarray(frame, "RGBA").save(args.out / f"{name}.png")
        used = {tuple(c) for c in frame[..., :3][frame[..., 3] > 0]}
        print(f"{name}.png {args.cell}x{args.cell} colours={len(used)}")


if __name__ == "__main__":
    main()
