"""Segmentation IoU on synthetic composites with exact masks.

Builds 20 "anime" frames (flat cel-shaded figure, black outlines, painted
background) and 20 "live-action" frames (shaded, textured figure, blurred noisy
background, grain). The figure's silhouette is the ground-truth mask. Synthetic,
so the numbers compare models; they are not a claim about real footage.

Usage: uv run --directory servers/assets/subject_extractor python ../../../evals/eval_segmentation.py [--hq]
  --hq  also score general_hq (BiRefNet, slow; needs `fetch_models.py birefnet`)
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from subject_extractor_mcp.segmenter import get_mask

OUT = Path(__file__).resolve().parent / "fixtures" / "seg"
LABELS = Path(__file__).resolve().parent / "labels"
W, H, N = 960, 540, 20


def _figure_parts(rng: random.Random):
    """Head, torso, arms, legs as (kind, box/points, width) in pixel space."""
    s = rng.uniform(0.7, 1.15) * H / 540
    cx, cy = rng.uniform(0.3, 0.7) * W, rng.uniform(0.45, 0.6) * H
    head = (cx - 45 * s, cy - 200 * s, cx + 45 * s, cy - 110 * s)
    torso = (cx - 60 * s, cy - 115 * s, cx + 60 * s, cy + 60 * s)
    limbs = []
    for side in (-1, 1):
        a = rng.uniform(-0.6, 0.6)
        limbs.append(
            ((cx + side * 55 * s, cy - 90 * s), (cx + side * (95 + 40 * a) * s, cy + (10 + 50 * a) * s), 26 * s)
        )
        limbs.append(
            ((cx + side * 30 * s, cy + 50 * s), (cx + side * (40 + 25 * rng.random()) * s, cy + 210 * s), 34 * s)
        )
    return head, torso, limbs, s


def _draw_figure(img: Image.Image, mask: Image.Image, rng: random.Random, anime: bool) -> None:
    head, torso, limbs, s = _figure_parts(rng)
    d, m = ImageDraw.Draw(img), ImageDraw.Draw(mask)
    skin = tuple(rng.randint(200, 255) for _ in range(3))
    cloth = tuple(rng.randint(30, 230) for _ in range(3))
    line = (15, 15, 20) if anime else None
    ow = max(2, int(4 * s)) if anime else 0
    for p0, p1, w in limbs:
        m.line([p0, p1], fill=255, width=int(w))
        if anime:
            d.line([p0, p1], fill=line, width=int(w))
        d.line([p0, p1], fill=cloth, width=int(w) - 2 * ow)
    m.ellipse(torso, fill=255)
    d.ellipse(torso, fill=cloth, outline=line, width=ow)
    m.ellipse(head, fill=255)
    d.ellipse(head, fill=skin, outline=line, width=ow)
    hair = (head[0] - 6 * s, head[1] - 10 * s, head[2] + 6 * s, (head[1] + head[3]) / 2)
    hair_c = tuple(rng.randint(20, 255) for _ in range(3))
    m.chord(hair, 180, 360, fill=255)
    d.chord(hair, 180, 360, fill=hair_c, outline=line, width=ow)
    ex, ey = (head[0] + head[2]) / 2, head[1] + 0.6 * (head[3] - head[1])
    for dx in (-15 * s, 15 * s):
        d.ellipse((ex + dx - 6 * s, ey - 9 * s, ex + dx + 6 * s, ey + 9 * s), fill=(30, 30, 60))


def _background(rng: random.Random, anime: bool) -> Image.Image:
    top = np.array([rng.randint(60, 230) for _ in range(3)], np.float32)
    bot = np.array([rng.randint(60, 230) for _ in range(3)], np.float32)
    t = np.linspace(0, 1, H)[:, None, None]
    arr = np.broadcast_to(top * (1 - t) + bot * t, (H, W, 3)).copy()
    if not anime:
        nrng = np.random.default_rng(rng.randint(0, 2**31))
        arr += nrng.normal(0, 40, (H // 8 + 1, W // 8 + 1, 1)).repeat(8, 0).repeat(8, 1)[:H, :W]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(rng.randint(3, 7)):  # buildings / trees / clouds
        x, y = rng.uniform(0, W), rng.uniform(0.2, 1) * H
        bw, bh = rng.uniform(40, 200), rng.uniform(40, 250)
        c = tuple(rng.randint(40, 220) for _ in range(3))
        d.rectangle((x, y - bh, x + bw, H), fill=c, outline=(15, 15, 20) if anime else None, width=3)
    return img if anime else img.filter(ImageFilter.GaussianBlur(6))


def make_frame(i: int, anime: bool):
    rng = random.Random(i * 2 + anime)
    img = _background(rng, anime)
    fig = Image.new("RGB", (W, H))
    mask = Image.new("L", (W, H), 0)
    _draw_figure(fig, mask, rng, anime)
    if not anime:  # soft shading + film grain, like a camera
        shade = np.linspace(1.15, 0.75, W)[None, :, None]
        f = np.asarray(fig, np.float32) * shade
        fig = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    img.paste(fig, mask=mask)
    arr = np.asarray(img).astype(np.float32)
    if not anime:
        arr += np.random.default_rng(i).normal(0, 6, arr.shape)
    return np.clip(arr, 0, 255).astype(np.uint8), np.asarray(mask) > 127


def iou(pred: np.ndarray, gt: np.ndarray) -> float:
    return float((pred & gt).sum() / max((pred | gt).sum(), 1))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    styles = ["anime", "general"] + (["general_hq"] if "--hq" in sys.argv else [])
    if "--real" in sys.argv:
        sets = load_real()
        _score(sets, styles)
        return
    sets = {"anime": [make_frame(i, True) for i in range(N)], "live-action": [make_frame(i, False) for i in range(N)]}
    for name, frames in sets.items():
        for i, (img, gt) in enumerate(frames[:3]):  # a few samples to eyeball
            Image.fromarray(img).save(OUT / f"{name}_{i:02d}.png")
            Image.fromarray(gt.astype(np.uint8) * 255).save(OUT / f"{name}_{i:02d}_mask.png")
    _score(sets, styles)


def load_real():
    """Hand-labeled frames from evals/labels/<set>/{images,masks} (see LABELING.md)."""
    sets = {}
    for set_dir in sorted(LABELS.iterdir()) if LABELS.exists() else []:
        pairs = []
        for m in sorted((set_dir / "masks").glob("*.png")):
            img = set_dir / "images" / m.name
            if img.exists():
                pairs.append((np.asarray(Image.open(img).convert("RGB")), np.asarray(Image.open(m).convert("L")) > 127))
        if pairs:
            sets[set_dir.name] = pairs
    if not sets:
        sys.exit(f"No labeled masks under {LABELS}; see evals/LABELING.md")
    return sets


def _score(sets, styles) -> None:
    print("| set | model style | mean IoU | min IoU | s/frame |")
    print("|---|---|---|---|---|")
    for name, frames in sets.items():
        for style in styles:
            get_mask(frames[0][0], style=style)  # warm-up (model load)
            t0 = time.perf_counter()
            scores = [iou(get_mask(img, style=style) > 0.5, gt) for img, gt in frames]
            dt = (time.perf_counter() - t0) / len(frames)
            print(f"| {name} | {style} | {np.mean(scores):.3f} | {min(scores):.3f} | {dt:.2f} |")


if __name__ == "__main__":
    main()
