"""One-off script: generates the bundled light-leak PNG assets in
src/overlay_fx_mcp/assets/. Run with: python generate_overlays.py
"""
import os
import numpy as np
from PIL import Image

W, H = 3840, 1080
OUT_DIR = os.path.join(os.path.dirname(__file__), "src", "overlay_fx_mcp", "assets")


def _blob(cx, cy, sigma, color, canvas):
    yy, xx = np.mgrid[0:H, 0:W]
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    intensity = np.exp(-d2 / (2.0 * sigma ** 2))
    for c in range(3):
        canvas[:, :, c] += intensity * color[c]


def make(name, blobs):
    canvas = np.zeros((H, W, 3), dtype=np.float64)
    for cx, cy, sigma, color in blobs:
        _blob(cx, cy, sigma, color, canvas)
    canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.png")
    Image.fromarray(canvas, "RGB").save(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    make("warm", [
        (W * 0.18, H * 0.3, H * 0.6, (255, 170, 60)),
        (W * 0.35, H * 0.6, H * 0.45, (255, 110, 40)),
    ])
    make("golden", [
        (W * 0.2, H * 0.35, H * 0.7, (255, 210, 110)),
        (W * 0.4, H * 0.55, H * 0.5, (255, 235, 160)),
    ])
    make("cool", [
        (W * 0.18, H * 0.3, H * 0.6, (90, 170, 255)),
        (W * 0.35, H * 0.6, H * 0.45, (60, 210, 255)),
    ])
    make("white", [
        (W * 0.2, H * 0.35, H * 0.5, (255, 255, 255)),
        (W * 0.38, H * 0.55, H * 0.35, (230, 240, 255)),
    ])
