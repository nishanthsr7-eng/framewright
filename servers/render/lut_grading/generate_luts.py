"""One-off script: generates the bundled .cube LUT files in src/lut_grading_mcp/luts/.
Run with: python generate_luts.py
"""
import os
import numpy as np

SIZE = 17
OUT_DIR = os.path.join(os.path.dirname(__file__), "src", "lut_grading_mcp", "luts")


def write_cube(name, transform):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.cube")
    lines = [f"LUT_3D_SIZE {SIZE}"]
    vals = np.linspace(0.0, 1.0, SIZE)
    for b in vals:
        for g in vals:
            for r in vals:
                nr, ng, nb = transform(r, g, b)
                nr = min(max(nr, 0.0), 1.0)
                ng = min(max(ng, 0.0), 1.0)
                nb = min(max(nb, 0.0), 1.0)
                lines.append(f"{nr:.6f} {ng:.6f} {nb:.6f}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}")


def cinematic_teal_orange(r, g, b):
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    shadow_w = max(0.0, (0.5 - lum) * 2.0)
    highlight_w = max(0.0, (lum - 0.5) * 2.0)
    nr = r + highlight_w * 0.15 - shadow_w * 0.05
    ng = g + shadow_w * 0.02
    nb = b + shadow_w * 0.15 - highlight_w * 0.06
    return nr, ng, nb


def warm_vintage(r, g, b):
    # lift blacks
    r2, g2, b2 = r * 0.9 + 0.06, g * 0.9 + 0.05, b * 0.9 + 0.04
    # warm tint
    r2 += 0.07
    b2 -= 0.05
    # desaturate slightly toward gray
    lum = 0.299 * r2 + 0.587 * g2 + 0.114 * b2
    sat = 0.85
    r2 = lum + (r2 - lum) * sat
    g2 = lum + (g2 - lum) * sat
    b2 = lum + (b2 - lum) * sat
    return r2, g2, b2


def cool_blue(r, g, b):
    nr = r - 0.04
    ng = g
    nb = b + 0.08
    # slight desaturate highlights
    lum = 0.299 * nr + 0.587 * ng + 0.114 * nb
    if lum > 0.6:
        sat = 0.9
        nr = lum + (nr - lum) * sat
        ng = lum + (ng - lum) * sat
        nb = lum + (nb - lum) * sat
    return nr, ng, nb


def high_contrast_bw(r, g, b):
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    lum2 = 0.5 + (lum - 0.5) * 1.4
    return lum2, lum2, lum2


def faded_film(r, g, b):
    # lift blacks + compress highlights
    r2, g2, b2 = r * 0.82 + 0.09, g * 0.82 + 0.085, b * 0.82 + 0.08
    # desaturate
    lum = 0.299 * r2 + 0.587 * g2 + 0.114 * b2
    sat = 0.75
    r2 = lum + (r2 - lum) * sat
    g2 = lum + (g2 - lum) * sat
    b2 = lum + (b2 - lum) * sat
    # slight warm tint
    r2 += 0.025
    return r2, g2, b2


def moody_green(r, g, b):
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    nr = r - 0.03
    ng = g + 0.05
    nb = b - 0.02
    # crush shadows
    shadow_w = max(0.0, (0.4 - lum) * 1.5)
    nr -= shadow_w * 0.05
    ng -= shadow_w * 0.02
    nb -= shadow_w * 0.05
    return nr, ng, nb


def bleach_bypass(r, g, b):
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = 0.4
    nr = lum + (r - lum) * sat
    ng = lum + (g - lum) * sat
    nb = lum + (b - lum) * sat
    # boost contrast
    nr = 0.5 + (nr - 0.5) * 1.3
    ng = 0.5 + (ng - 0.5) * 1.3
    nb = 0.5 + (nb - 0.5) * 1.3
    return nr, ng, nb


PRESETS = {
    "cinematic_teal_orange": cinematic_teal_orange,
    "warm_vintage": warm_vintage,
    "cool_blue": cool_blue,
    "high_contrast_bw": high_contrast_bw,
    "faded_film": faded_film,
    "moody_green": moody_green,
    "bleach_bypass": bleach_bypass,
}


if __name__ == "__main__":
    for name, fn in PRESETS.items():
        write_cube(name, fn)
