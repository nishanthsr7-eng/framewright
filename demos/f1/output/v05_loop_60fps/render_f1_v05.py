"""F1 demo v5: reference-style edit at 60 fps that loops seamlessly (the last frame flows into the first).

  0.000-0.733  hook: fist-pump cut-out (white outline, glow, ghost trails); continues from the end
  0.733-1.700  trophy cut-out over the flickering intro backgrounds (depth blur behind him)
  1.700-2.333  helmet-on cut-out (garage)
  2.333-3.000  split screen: three strips slide in
  3.000-3.267  strobe: full-frame shots alternating every 0.1 s, heavy RGB split, thin bars
  3.267-5.883  "Simply lovely." line: Max from behind (black and white cut-out); hollow SIMPLY / LOVELY type
               out behind him on the spoken syllables, drift and pulse on the beats, carry his shadow,
               then slice out as the bars squeeze to a strip
  5.883-6.367  build-up: cuts accelerate, white flash into the drop
  6.367-12.533 drop: a cut every 1-2 beats (snapped to the kick drum), emotion shots, cut-out hits, a second
               split, focus pulls
  12.533-13.500 climax: trophy freeze cut-out, MAX VERSTAPPEN / 4 TIMES WORLD CHAMPION types in, glitches out
  13.500-end   loop lead-in: the hook clip's preceding frames, so playback wraps without a seam

Full-frame shots are colour matched to the reference edit, graded and sharpened; one final colour layer
then unifies everything. Output: 1920x1080 (16:9), 60 fps.

Run from the repo root (finishing tools need the overlay_fx environment):
  uv run --directory servers/render/overlay_fx python demos/f1/output/v05_loop_60fps/render_f1_v05.py
"""
import importlib.util
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v4", HERE.parent / "v04_transitions_titles" / "render_f1_v04.py")
v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)

# route every v4 helper to the v5 folder
v4.OUT = HERE
WORK = HERE / "_work"
v4.SEG = WORK / "segments"
v4.SEG.mkdir(parents=True, exist_ok=True)
for f in ("impact.ttf", "arialbd.ttf"):
    if not (HERE / f).exists():
        shutil.copy(HERE.parent / "v04_transitions_titles" / f, HERE / f)
if not (HERE / "agencyb.ttf").exists():
    shutil.copy("C:/Windows/Fonts/AGENCYB.TTF", HERE / "agencyb.ttf")

# 60 fps everywhere (the footage is 1080p60); v4 helpers read these module globals at call time
FPS = 60
v4.FPS = FPS
v4.K = round(0.133 * FPS)  # transition length
v4.MBLUR = "tmix=frames=5"


def shake(amp=22):
    """v4's camera shake, with the same speed in seconds at any frame rate."""
    a, b = 2.3 * 30 / FPS, 3.1 * 30 / FPS
    return f"scale=2112:1188,crop=1920:1080:96+{amp}*sin(n*{a:.4f}):54+{amp * 0.7:.0f}*cos(n*{b:.4f})"


v4.shake = shake

A, B = v4.A, v4.B
rgb, zp, run, enc, shot, frames = v4.rgb, v4.zp, v4.run, v4.enc, v4.shot, v4.frames
REF = str(v4.ROOT / "input/reference_edit.mp4")
CUTS = WORK / "cutouts"


def fr(t):
    return round(t * FPS)


def s30(k):
    """A frame count that was tuned at 30 fps, at the current frame rate."""
    return k * FPS // 30


# beat grid snapped to the kick drum where a strong kick lands within 58 ms (drop only; the intro has none)
SNAP = {6.13: 6.133, 6.455: 6.473, 6.78: 6.821, 7.105: 7.134, 7.43: 7.448, 7.755: 7.761, 8.382: 8.423,
        9.033: 9.027, 9.358: 9.355, 10.286: 10.342, 10.635: 10.62, 10.96: 11.015, 11.262: 11.288, 11.587: 11.601}
BEATS = [SNAP.get(b, b) for b in v4.BEATS] + [13.514, 13.839]  # grid continues to the loop point
v4.BEATS = BEATS

# timeline (seconds)
S1_T, S2_T, S3_T, STROBE_T = 22 / 30, 51 / 30, 70 / 30, 3.0
LINE_IN, LINE_OUT = 3.274, 5.883  # beat before the line -> end of "lovely."
DROP_T, CLIMAX_T, LOOP_T = 6.367, 12.539, 13.5
N_TOTAL = fr(v4.END)

# intro/lovely backgrounds keep their look: crushed blacks, teal shadows, saturated reds, cool whites
GRADE = ("curves=all='0/0 0.12/0.04 0.5/0.48 0.85/0.9 1/1',"
         "eq=contrast=1.12:saturation=1.28,"
         "colorbalance=rs=-0.10:gs=0.01:bs=0.07:rm=-0.03:bm=0.03:rh=0.02:bh=0.02")
# full-frame shots: brighter, open shadows, punchy colour (applied after the colour match)
BRIGHT = ("curves=all='0/0.03 0.25/0.29 0.5/0.6 0.8/0.89 1/1',eq=contrast=1.05:saturation=1.25,"
          "colorbalance=rs=-0.05:bs=0.04:rh=0.03:bh=-0.02")
HIGHKEY = "eq=brightness=0.14:contrast=1.25:saturation=0.75,curves=preset=lighter,colorbalance=bh=0.04:rh=-0.02"
DARK = "eq=brightness=-0.12:contrast=1.2:saturation=0.9,gblur=sigma=2"
SHARP = "unsharp=5:5:0.6:5:5:0.0"  # light luma sharpening for full-frame shots
# one finish over the whole edit: gentle split tone and contrast so every source sits in the same look
UNIFY = ("colorbalance=rs=-0.03:bs=0.03:rm=0.01:bm=-0.01:rh=0.03:bh=-0.02,"
         "curves=all='0/0.01 0.5/0.51 1/0.99',eq=saturation=1.05")
v4.GRADE = BRIGHT  # v4.build_chain grades the drop shots
v4.HIGHKEY = HIGHKEY

# background pool: (file, source time)
POOL = [(A, 18.5), (A, 25.0), (A, 33.5), (A, 46.5), (A, 52.5), (A, 62.0), (A, 72.0), (A, 76.5), (A, 90.0),
        (A, 101.0), (A, 110.0), (A, 128.2), (A, 148.2), (B, 0.6), (B, 48.5), (B, 52.5), (B, 260.5), (B, 298.5),
        (B, 304.0), (B, 324.5), (B, 340.0), (B, 366.0), (B, 392.0), (A, 112.5), (A, 82.5)]
# unused race/crowd footage for the flickering backgrounds of the drop cut-outs and the climax
POOL2 = [(A, 19.5), (A, 26.0), (A, 31.5), (A, 35.5), (A, 53.5), (A, 58.5), (A, 63.0), (A, 91.0), (A, 96.0),
         (B, 2.0), (B, 6.0), (B, 36.5), (B, 47.0), (B, 50.5), (B, 60.5), (B, 300.5), (B, 309.0), (B, 386.5)]
rng = random.Random(33)


# ---- colour match ---------------------------------------------------------------
def _stats(src, t, dur):
    """Mean/std per RGB channel of a clip's middle band (skips letterbox bars)."""
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-t", f"{max(dur, 0.5):.3f}", "-i", src,
           "-vf", "fps=6,scale=192:108,crop=192:64:0:22", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, timeout=120, stdin=subprocess.DEVNULL).stdout
    px = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.float64)
    return px.mean(0), px.std(0)


_REF = None


def match_lut(src, t, dur, strength=1.0):
    """Per-channel gain/offset that pulls a shot toward the reference edit's look (color_match's method)."""
    global _REF
    if _REF is None:
        _REF = _stats(REF, 0.3, 13.5)
    (rm, rs), (tm, ts) = _REF, _stats(src, t, dur)
    exprs = []
    for c, ch in enumerate("rgb"):
        gain = float(np.clip(rs[c] / max(ts[c], 1e-6), 0.7, 1.5))
        off = float(np.clip(rm[c] - tm[c] * gain, -60, 60))
        gain, off = 1 + (gain - 1) * strength, off * strength
        exprs.append(f"{ch}='clip(val*{gain:.4f}+{off:.2f},0,255)'")
    return "lutrgb=" + ":".join(exprs)


def focus_in():
    """Focus pull: heavy blur that clears over the first 1/6 s."""
    k = round(FPS / 6)
    return ",".join(f"gblur=sigma={26 * (1 - i / k) ** 2 + 0.5:.2f}:enable='eq(n,{i})'" for i in range(k))


def local_beats(f0, n):
    return [b - f0 / FPS for b in BEATS if f0 / FPS <= b < (f0 + n) / FPS]


def windows(beats, width):
    return "+".join(f"between(t,{b:.3f},{b + width:.3f})" for b in beats) or "0"


# ---- flickering backgrounds -----------------------------------------------------
def bg_chunk(path, n, look, slices=False, pool=POOL):
    """n frames of one background (or 3 horizontal slices from different clips, offset sideways)."""
    looks = {"grade": "null", "high": HIGHKEY, "dark": DARK}  # GRADE is applied after compositing
    if not slices:
        src, t = rng.choice(pool)
        shot(path, src, t + rng.uniform(0, 1.5), 1.0, n, [looks[look], rgb(rng.choice((6, 10, 16))), "gblur=sigma=1.5"])
        return
    picks = rng.sample(pool, 3)
    hs = [360, 360, 360]
    args, parts = [], []
    for i, (src, t) in enumerate(picks):
        args += ["-ss", f"{t + rng.uniform(0, 1.5):.2f}", "-t", "1", "-i", src]
        dx = rng.choice((-160, -80, 80, 160))
        lk = rng.choice(("grade", "high", "dark"))
        cx, px = (dx, 0) if dx > 0 else (0, -dx)
        parts.append(f"[{i}:v]fps={FPS},{v4.BASE},{looks[lk]},crop={1920 - abs(dx)}:{hs[i]}:{cx}:{sum(hs[:i])},"
                     f"pad=1920:{hs[i]}:{px}:0,{rgb(14)}[s{i}]")
    graph = ";".join(parts) + ";[s0][s1][s2]vstack=3"
    run([*args, "-filter_complex", graph, *enc(n), str(path)])


def bg_track(name, t0, t1, chunk_frames, slice_every=3, pool=POOL):
    """Flickering background: a new image every `chunk_frames`, some chunks are slice glitches."""
    n_total = frames(t0, t1)
    lst = v4.SEG / f"{name}.txt"
    lines, done, k = [], 0, 0
    while done < n_total:
        n = min(chunk_frames if isinstance(chunk_frames, int) else rng.choice(chunk_frames), n_total - done)
        p = v4.SEG / f"{name}_{k:03d}.mp4"
        look = rng.choices(("grade", "high", "dark"), (5, 3, 2))[0]
        bg_chunk(p, n, look, slices=(k % slice_every == slice_every - 1), pool=pool)
        lines.append(f"file '{p.as_posix()}'\n")
        done += n
        k += 1
    lst.write_text("".join(lines))
    return lst


def beat_enable(t0, t1, width=0.1):
    return "+".join(f"between(t,{b - t0:.3f},{b - t0 + width:.3f})" for b in v4.BEATS if t0 <= b < t1) or "0"


def push_rgba(n, z1):
    """Centre zoom 1.0 -> z1 over n frames, alpha-safe (matches zp's push)."""
    s = f"(1+{z1 - 1:.3f}*min(1,n/{n}))"
    return (f"scale=w='trunc(1920*{s}/2)*2':h='trunc(1080*{s}/2)*2':eval=frame:flags=lanczos,"
            "crop=1920:1080:(iw-1920)/2:(ih-1080)/2")


# ---- cut-out hero shots ---------------------------------------------------------
# colour cut-outs: worked at 2x, tight mask edge, gentle contrast, vibrance, fine sharpening
HERO_LOOK = ("scale=3840:2160:flags=lanczos,lutrgb=a='clip((val-40)*1.3,0,255)',"
             "curves=all='0/0 0.1/0.06 0.5/0.54 0.9/0.96 1/1',vibrance=intensity=0.45,"
             "format=yuva444p,unsharp=9:9:1.0,unsharp=5:5:0.5,format=rgba")


def hero_section(name, f0, n, cut, first, place, *, bg_mp4=None, bg_start=0, push=1.06, freeze=False,
                 glow_always=False, beats=None, mask_dir=None, pool=POOL):
    """Max cut-out over flickering backgrounds (lifted and blurred so he pops), with a white outline,
    glow and red/cyan ghost trails on the beats. place = (scale, x, y) of the 1920x1080 cut-out frame."""
    sc, x, y = place
    W, H = round(1920 * sc / 2) * 2, round(1080 * sc / 2) * 2
    bl = local_beats(f0, n) if beats is None else beats
    ghost, flash = windows(bl, 0.2), windows(bl, 0.1)
    glow = "1" if glow_always else ghost
    if bg_mp4 is None:
        lst = bg_track(name + "_bg", 0, n / FPS, (s30(3), s30(4)), pool=pool)
        bg_in, trim = ["-f", "concat", "-safe", "0", "-i", str(lst)], ""
    else:
        bg_in, trim = ["-i", str(bg_mp4)], f"trim=start_frame={bg_start}:end_frame={bg_start + n},"
    cut_in = (["-loop", "1", "-framerate", str(FPS), "-i", str(cut / f"f_{first:04d}.png")] if freeze else
              ["-framerate", str(FPS), "-start_number", str(first), "-i", str(cut / "f_%04d.png")])
    d1, d2 = round(0.05 * FPS), round(0.1 * FPS)  # ghost delays

    def at(k):  # position of a copy scaled by k, centred on the main layer
        return f"x={x - W * (k - 1) / 2:.0f}:y={y - H * (k - 1) / 2:.0f}"

    graph = (
        f"[0:v]{trim}setpts=PTS-STARTPTS,{GRADE},{zp(0, n, base=1.0, push=(1.0, 1.06))},setpts=N/{FPS}/TB,"
        f"{rgb(7)},{rgb(18, flash)},eq=brightness=0.06:enable='{flash}',gblur=sigma=4,curves=preset=lighter,"
        f"eq=brightness=0.05:saturation=0.9[bg];"
        f"[1:v]format=rgba,setpts=PTS-STARTPTS,{HERO_LOOK},{push_rgba(n, push)},scale={W}:{H}:flags=lanczos,"
        f"split=5[m][r0][g0][k1][k2];"
        f"[r0]lutrgb=r=255:g=255:b=255,gblur=sigma=4,lutrgb=a='min(255,val*5)',split[rim][rm];"
        f"[g0]lutrgb=r=255:g=255:b=255,gblur=sigma=22,lutrgb=a='min(255,val*1.6)'[glow];"
        f"[k1]tpad=start={d1}:start_mode=clone,colorchannelmixer=gg=0.15:bb=0.35:aa=0.55,scale=iw*1.04:-2[gh1];"
        f"[k2]tpad=start={d2}:start_mode=clone,colorchannelmixer=rr=0.1:gg=0.85:aa=0.4,scale=iw*1.08:-2[gh2];"
        f"[bg][gh2]overlay={at(1.08)}:enable='{ghost}'[a1];[a1][gh1]overlay={at(1.04)}:enable='{ghost}'[a2];"
        f"[a2][glow]overlay=x={x}:y={y}:enable='{glow}'[a3];[a3][rim]overlay=x={x}:y={y}[a4];"
        f"[a4][m]overlay=x={x}:y={y},setpts=N/{FPS}/TB[v]"
    )
    out = v4.SEG / f"{name}.mp4"
    extra = []
    if mask_dir:  # text mask: white where Max (and his outline) isn't
        mask_dir.mkdir(exist_ok=True)
        graph += (f";color=c=black@0:s=1920x1080:r={FPS},format=rgba[cv];[cv][rm]overlay=x={x}:y={y},"
                  f"alphaextract,negate[mk]")
        extra = ["-map", "[mk]", "-frames:v", str(n), str(mask_dir / "m_%04d.png")]
    else:
        graph += ";[rm]nullsink"
    run([*bg_in, *cut_in, "-filter_complex", graph, "-map", "[v]", *enc(n), str(out), *extra])
    return out


def trim_clip(src, a, b, name):
    out = v4.SEG / f"{name}.mp4"
    run(["-i", str(src), "-vf", f"trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS", *enc(b - a), str(out)])
    return out


# ---- split screen ----------------------------------------------------------------
def split_section(name, f0, n, shots):
    """Three vertical strips sliding in one after another (alternating from below/above), flash on the beats.
    shots: [(file, source in, horizontal crop centre 0..1)]"""
    args = []
    for i, (src, t, _) in enumerate(shots):
        p = v4.SEG / f"{name}_{i}.mp4"
        shot(p, src, t, 1.0, n, [match_lut(src, t, n / FPS), BRIGHT, zp(0, n, base=1.04, push=(1.04, 1.14)), rgb(6),
                                 SHARP])
        args += ["-i", str(p)]
    flash = windows(local_beats(f0, n), 0.08)
    g = [f"color=c=black:s=1920x1080:r={FPS}[k0]"]
    for i, (_, _, cx) in enumerate(shots):
        a, d = i * 0.1, (1 if i % 2 == 0 else -1) * 1080
        y = f"if(lt(t,{a:.3f}),{d},{d}*pow(max(0,1-(t-{a:.3f})/0.133),2))"
        g.append(f"[{i}:v]crop=624:1080:(iw-624)*{cx}:0[s{i}]")
        g.append(f"[k{i}][s{i}]overlay=x={i * 648}:y='{y}'[k{i + 1}]")
    graph = ";".join(g) + f";[k{len(shots)}]setpts=N/{FPS}/TB,eq=brightness=0.12:enable='{flash}',{rgb(16, flash)}"
    out = v4.SEG / f"{name}.mp4"
    run([*args, "-filter_complex", graph, *enc(n), str(out)])
    return out


# ---- build-up ----------------------------------------------------------------------
def build_section(t0, t1):
    """Cuts accelerate into the drop (longest first, a single frame at the end); zoom, RGB split and shake grow;
    the last cut flashes white."""
    n = frames(t0, t1)
    weights = (5, 4, 4, 3, 3, 3, 3, 2, 2)
    chunks = [max(1, w * n // sum(weights)) for w in weights]
    chunks[0] += n - sum(chunks)
    srcs = [(B, 317.0), (B, 320.5), (B, 357.5), (B, 362.0), (B, 26.0), (B, 44.0), (A, 41.0), (B, 33.0), (B, 349.0)]
    parts = []
    for i, (k, (src, t)) in enumerate(zip(chunks, srcs)):
        chain = [match_lut(src, t, 0.5), BRIGHT, zp(0, k, base=1.04 + 0.03 * i), rgb(8 + 3 * i), shake(10 + 4 * i),
                 SHARP]
        if i == len(chunks) - 1:
            chain.append("eq=brightness=0.55")
        p = v4.SEG / f"build_{i}.mp4"
        shot(p, src, t, 1.0, k, chain)
        parts.append(p)
    return parts


# ---- typed titles ----------------------------------------------------------------
TITLE_FONT = "agencyb.ttf"  # tall condensed face, like the reference
CURSOR = (255, 28, 48)  # newest letter glows vibrant red while typing
TEXT_DIR, MASK_DIR, SHADOW_DIR = WORK / "lovely_text", WORK / "lovely_mask", WORK / "lovely_shadow"
TITLE_DIR, TITLE_MASK = WORK / "title_text", WORK / "title_mask"
POP_T, POP_K = (0, 1 / 30, 2 / 30, 3 / 30), (1.3, 1.14, 1.05, 1.0)  # landing pop: scale over the first 0.1 s

# Max layer in the lovely section: black and white, worked at 2x with punchy contrast and fine sharpening
MAX_LOOK = ("scale=3840:2160:flags=lanczos,lutrgb=a='clip((val-40)*1.3,0,255)',"
            "colorchannelmixer=.3:.59:.11:0:.3:.59:.11:0:.3:.59:.11:0,"
            "curves=all='0/0 0.1/0.03 0.5/0.55 0.85/0.98 1/1',"
            "format=yuva444p,unsharp=9:9:1.2,unsharp=5:5:0.6,format=rgba")


def _font(size):
    from PIL import ImageFont
    return ImageFont.truetype(str(HERE / TITLE_FONT), size)


def text_width(text, size):
    return _font(size).getlength(text)


def letter_sprites(font, ch, s, size):
    """White and red versions of one hollow letter (2x): white ring, dark see-through fill, dark outer edge, glow."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    k = size / 280
    pad, ring, edge = 40 * s, max(2, round(6 * k)) * s, max(2, round(5 * k)) * s
    dims = (int(font.getlength(ch)) + 2 * pad, int(font.size * 1.25) + 2 * pad)

    def mask(stroke=0):
        m = Image.new("L", dims, 0)
        ImageDraw.Draw(m).text((pad, pad), ch, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
        return m

    glyph, outer, rim = mask(), mask(ring), mask(ring + edge)
    inner = glyph.filter(ImageFilter.MinFilter(2 * max(1, round(k)) * s + 1))
    ring_m = ImageChops.subtract(outer, inner)
    edge_m = ImageChops.subtract(rim, outer)
    glow_m = ring_m.filter(ImageFilter.GaussianBlur(12 * s * max(k, 0.4)))

    def build(color, glow_amt):
        out = Image.new("RGBA", dims, (0, 0, 0, 0))
        for rgb_, m, a in ((color, glow_m, glow_amt), ((0, 0, 0), edge_m, 0.75), ((0, 0, 0), inner, 0.35),
                           (color, ring_m, 1.0)):
            layer = Image.new("RGBA", dims, (*rgb_, 255))
            layer.putalpha(m.point(lambda v: int(v * a)))
            out = Image.alpha_composite(out, layer)
        return out

    return build((255, 255, 255), 0.55), build(CURSOR, 0.9)


def _slice_out(img, p, seed=7):
    """Horizontal slices sliding sideways and fading as p goes 0 -> 1 (glitch exit)."""
    from PIL import Image
    r = random.Random(seed)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    for y in range(0, img.height, 14):
        band = img.crop((0, y, img.width, min(img.height, y + 14)))
        dx = round(r.choice((-1, 1)) * p * 160 * (0.4 + r.random()))
        out.alpha_composite(band, (max(0, dx), y), (max(0, -dx), 0))
    out.putalpha(out.getchannel("A").point(lambda v: int(v * (1 - p))))
    return out


def render_text_frames(items, t0, n, out_dir, *, out_t=None, drift=None, pulse=(), slice_t=None, shadow_dir=None,
                       s=2):
    """Typed title as RGBA PNGs, drawn at 2x and scaled down with lanczos. Each letter pops in red, then settles
    white. Times are in seconds on the edit's timeline.
    items: [(text, start or per-letter starts, left x, top y, size)]; (start, step) types at a fixed rate.
    out_t: letters glitch out from here (last letters first, flashing red).
    drift: px/s per item once it starts; pulse: beat times for a 2.5% scale pulse; slice_t: slice-out exit start;
    shadow_dir: per-frame grey masks (m_####.png) that darken the text where Max's shadow falls."""
    from PIL import Image
    out_dir.mkdir(exist_ok=True)
    letters, cache, centres = [], {}, []  # letters: (appear t, x, y, sprites, item)
    for j, (text, at, x0, y0, size) in enumerate(items):
        font = _font(size * s)
        chars = [i for i, ch in enumerate(text) if ch != " "]
        times = at if isinstance(at, list) else [at[0] + i * at[1] for i in chars]
        for i, ta in zip(chars, times):
            ch = text[i]
            if (size, ch) not in cache:
                cache[size, ch] = letter_sprites(font, ch, s, size)
            letters.append((ta, x0 * s + font.getlength(text[:i]), y0 * s, cache[size, ch], j))
        centres.append(((x0 + font.getlength(text) / s / 2) * s, (y0 + size * 0.7) * s, min(times)))
    pad, last = 40 * s, len(letters) - 1
    end_t = t0 + n / FPS
    for f in range(n):
        t = t0 + f / FPS
        canvas = Image.new("RGBA", (1920 * s, 1080 * s), (0, 0, 0, 0))
        S = 1 + 0.025 * max([max(0.0, 1 - (t - b) / 0.15) for b in pulse if b <= t] or [0])
        for idx, (ta, x, y, (white, red), j) in enumerate(letters):
            age = t - ta
            gone = out_t + (1 - idx / max(last, 1)) * 2 / 30 if out_t is not None else None
            if age < 0 or (gone is not None and t >= gone):
                continue
            k = float(np.interp(age, POP_T, POP_K)) * S
            g = 1.0 if age < 0.1 else max(0.0, 1 - (age * 30 - 2) / 4)  # red while typing, then fades
            if gone is not None and t >= gone - 1 / 30:
                g = 1.0  # flashes red just before it goes
            cx_i, cy_i, start_i = centres[j]
            dx = (drift[j] * s * max(0.0, t - start_i)) if drift else 0
            for sp, amt in ((white, 1 - g), (red, g)):
                if amt <= 0:
                    continue
                im = sp.resize((round(sp.width * k), round(sp.height * k)), Image.LANCZOS) if k != 1 else sp.copy()
                if amt < 1:
                    im.putalpha(im.getchannel("A").point(lambda v: int(v * amt)))
                lx, ly = x - pad + sp.width / 2, y - pad + sp.height / 2  # letter centre, then scale about the word
                lx, ly = cx_i + (lx - cx_i) * S + dx, cy_i + (ly - cy_i) * S
                canvas.alpha_composite(im, (max(0, round(lx - im.width / 2)), max(0, round(ly - im.height / 2))))
        img = canvas.resize((1920, 1080), Image.LANCZOS)
        if slice_t is not None and t >= slice_t:
            img = _slice_out(img, min(1.0, (t - slice_t) / max(end_t - slice_t, 1e-3)))
        if shadow_dir is not None:
            arr = np.asarray(img).astype(np.float32)
            sh = np.asarray(Image.open(shadow_dir / f"m_{f + 1:04d}.png").convert("L"), np.float32) / 255
            arr[..., :3] *= (1 - 0.55 * sh)[..., None]
            img = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
        img.save(out_dir / f"t_{f + 1:04d}.png")


def lovely_section(t0, t1, rgba_dir, first, items, drift, slice_t):
    """'Simply lovely' line, as in the reference: Max from behind over flickering backgrounds, bars closing to a strip.
    The words are laid on after the finishing pass through a mask that keeps them behind him, and his shadow
    (a blurred, offset copy of his matte) darkens them."""
    n = frames(t0, t1)
    lst = bg_track("lovely_bg", t0, t1, (s30(3), s30(4)))
    echo = beat_enable(t0, t1, 0.12)
    bars_ = v4.letterbox(n / FPS - 0.35, n / FPS - 0.05, h=400, steps=8)
    graph = (
        # background: same look as the other sections (grade, push, RGB split, beat flashes)
        f"[0:v]setpts=PTS-STARTPTS,{GRADE},{zp(t0, n, base=1.0, push=(1.0, 1.06))},setpts=N/{FPS}/TB,"
        f"{rgb(7)},{rgb(18, echo)},eq=brightness=0.06:enable='{echo}'[bg];"
        # Max: the 30 fps slow-motion cut-out, black and white, slow push, no glitch; head centred
        f"[1:v]format=rgba,setpts=PTS-STARTPTS,fps={FPS},{MAX_LOOK},{push_rgba(n, 1.05)},"
        f"scale=1536:864:flags=lanczos,split[fg][fm];"
        f"[bg][fg]overlay=72:216:eof_action=repeat,setpts=N/{FPS}/TB,{bars_}[v];"
        f"[fm]alphaextract,setpts=N/{FPS}/TB,split[fa][fb];"
        # text mask: white where Max isn't, black under him and under the bars
        f"[fa]pad=1920:1080:72:216:color=black,negate,format=yuv420p,{bars_},extractplanes=y[m];"
        # his shadow on the words: matte shifted right/down and blurred
        f"[fb]pad=1920:1100:112:236:color=black,crop=1920:1080:0:0,gblur=sigma=18,format=gray[sh]"
    )
    out = v4.SEG / "lovely.mp4"
    for d in (MASK_DIR, SHADOW_DIR):
        d.mkdir(exist_ok=True)
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-framerate", "30", "-start_number", str(first),
         "-i", str(rgba_dir / "f_%04d.png"), "-filter_complex", graph,
         "-map", "[v]", *enc(n), str(out), "-map", "[m]", "-frames:v", str(n), str(MASK_DIR / "m_%04d.png"),
         "-map", "[sh]", "-frames:v", str(n), str(SHADOW_DIR / "m_%04d.png")])
    pulse = [b for b in BEATS if t0 <= b < t1]
    render_text_frames(items, fr(t0) / FPS, n, TEXT_DIR, drift=drift, pulse=pulse, slice_t=slice_t,
                       shadow_dir=SHADOW_DIR)
    return out


def strobe_section(t0, t1):
    """Full-frame shots alternating every 0.1 s with heavy RGB split and thin bars."""
    n = frames(t0, t1)
    c = round(0.1 * FPS)
    srcs = [(A, 58.0), (A, 35.0), (A, 53.0), (A, 136.8)][:(n + c - 1) // c]
    paths = []
    for i, (src, t) in enumerate(srcs):
        p = v4.SEG / f"strobe_src{i}.mp4"
        shot(p, src, t, 0.5, n, [GRADE if i != 3 else HIGHKEY, zp(t0, n, base=1.05, push=(1.05, 1.18)), v4.GLOW,
                                 rgb(22), SHARP])
        paths.append(p)
    args = sum((["-i", str(p)] for p in paths), [])
    k = len(paths)
    # cut chunks round-robin with trim + concat (select/interleave scrambles frame order on concat)
    chunks = [(i * c, min(n, i * c + c)) for i in range((n + c - 1) // c)]
    uses = [sum(1 for i in range(len(chunks)) if i % k == j) for j in range(k)]
    sp = ";".join(f"[{i}:v]split={uses[i]}" + "".join(f"[i{i}_{j}]" for j in range(uses[i])) for i in range(k))
    seen = [0] * k
    cuts = []
    for ci, (a, b) in enumerate(chunks):
        i = ci % k
        cuts.append(f"[i{i}_{seen[i]}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[c{ci}]")
        seen[i] += 1
    graph = (sp + ";" + ";".join(cuts) + ";" + "".join(f"[c{ci}]" for ci in range(len(chunks))) +
             f"concat=n={len(chunks)}:v=1:a=0,setpts=N/{FPS}/TB,{v4.bars(26)},{v4.zoomblur(s1=1.02, s2=1.05)}")
    out = v4.SEG / "strobe.mp4"
    run([*args, "-filter_complex", graph, *enc(n), str(out)])
    return out


# ---- drop --------------------------------------------------------------------------
# (start, end, file, source in, speed, look, extras); extras as in v4.build_chain, plus focus (focus pull in).
# Cut times sit on the kick-snapped beats.
DROP = [
    (6.367, 7.134, A, 82.4, 0.5, "grade", dict(flash=0.12, zin=0.45, punch=0.07, glow=True, rgb=8, whip_out=1)),
    (7.134, 7.448, A, 68.6, 1.0, "grade", dict(whip_in=1, focus=True, punch=0.06, rgb=8)),  # cap + flag
    # 7.448-8.081 split screen, 8.081-8.707 fist-raised cut-out
    (8.707, 9.355, A, 63.5, 0.5, "grade", dict(zin=0.35, punch=0.08, glow=True, rgb=10)),  # fence, crowd
    (9.355, 9.660, A, 77.4, 1.0, "grade", dict(focus=True, punch=0.06, rgb=8)),  # champagne hug
    (9.660, 9.961, A, 110.8, 1.0, "grade", dict(whip_in=-1, punch=0.06, rgb=10, mblur=True)),  # crew celebration
    (9.961, 10.620, A, 19.0, 0.6, "grade", dict(flash=0.1, zin=0.4, punch=0.06, glow=True, rgb=8)),  # Max and Checo
    # 10.620-11.288 helmet-on cut-out, looking at camera
    (11.288, 11.601, A, 120.3, 1.0, "highkey", dict(flash=0.08, whip_in=1, punch=0.1, rgb=14, mblur=True,
                                                     zbfull=True, zout=0.3)),
    (11.601, 11.912, A, 148.3, 1.0, "highkey", dict(zin=0.3, punch=0.1, rgb=14, mblur=True, zbfull=True, zout=0.3)),
    (11.912, 12.214, A, 128.5, 1.0, "grade", dict(whip_in=-1, shake=22, rgb=12, zout=0.35, zb=True)),
    (12.214, 12.539, A, 25.5, 1.0, "grade", dict(zin=0.3, punch=0.08, rgb=8)),  # Max and Checo
]


def drop_shot(i, t0, t1, src, t_in, speed, look, x):
    n = frames(t0, t1)
    chain = [match_lut(src, t_in, n / FPS * speed)] + v4.build_chain(t0, n, look, x) + [SHARP]
    if x.get("focus"):
        chain.append(focus_in())
    p = v4.SEG / f"d{i:02d}.mp4"
    shot(p, src, t_in, speed, n, chain)
    return p


# ---- finishing ---------------------------------------------------------------------
TEXT_LAYERS = [(fr(LINE_IN), TEXT_DIR, MASK_DIR), (fr(CLIMAX_T), TITLE_DIR, TITLE_MASK)]


def finish(src):
    """Framewright finishing (light teal/orange LUT, grain, soft vignette), then the titles on top so they
    stay pure white and sharp, each through its mask so it sits behind Max."""
    sys.path[:0] = [str(v4.REPO / "servers/render/lut_grading/src"), str(v4.REPO / "servers/render/overlay_fx/src"),
                    str(v4.REPO / "servers/core/src")]
    from lut_grading_mcp.grading import apply_lut
    from overlay_fx_mcp.effects import add_film_grain, add_vignette

    p = apply_lut(str(src), "cinematic_teal_orange", intensity=0.2, output_path=str(HERE / "_f1_lut.mp4"),
                  lossless=True)["output_path"]
    p = add_film_grain(p, intensity=8, output_path=str(HERE / "_f2_grain.mp4"), lossless=True)["output_path"]
    p = add_vignette(p, intensity=0.06, output_path=str(HERE / "_f3_vig.mp4"), lossless=True)["output_path"]

    args, g, last = ["-i", p], [], "0:v"
    for k, (start, tdir, mdir) in enumerate(TEXT_LAYERS):
        args += ["-framerate", str(FPS), "-i", str(tdir / "t_%04d.png"), "-framerate", str(FPS), "-i",
                 str(mdir / "m_%04d.png")]
        t, m = 1 + 2 * k, 2 + 2 * k
        g.append(f"[{t}:v]format=rgba,split[t{k}a][t{k}b];[t{k}b]alphaextract[t{k}c];[{m}:v]format=gray[m{k}];"
                 f"[t{k}c][m{k}]blend=all_mode=multiply[a{k}];[t{k}a][a{k}]alphamerge,"
                 f"setpts=PTS-STARTPTS+{start}/{FPS}/TB[x{k}];[{last}][x{k}]overlay=eof_action=pass[o{k}]")
        last = f"o{k}"
    out = HERE / "_f4_text.mp4"
    run([*args, "-filter_complex", ";".join(g) + f";[{last}]format=yuv420p", *enc(lossless=True), str(out)])
    return out


def assemble(parts, final):
    """Concat, one unifying colour layer, beat pulses (drop plus the hook, so both sides of the loop point
    match), finishing, music. 1920x1080 at 60 fps."""
    lst = v4.SEG / "all.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    pulse = windows([b for b in BEATS if b >= 6.4 or b < S1_T], 0.067)
    # setsar=1: v4's 2040x1148 overscan is not exactly 16:9, so force square pixels (exact 16:9 display)
    graph = f"setpts=N/{FPS}/TB,setsar=1,{UNIFY},eq=brightness=0.1:contrast=1.08:enable='{pulse}',{rgb(14, pulse)}"
    pre = HERE / "_f0_assembled.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-vf", graph, *enc(lossless=True), "-r", str(FPS), str(pre)])
    fin = finish(pre)
    dur = N_TOTAL / FPS
    # tiny fades at both ends so the audio wraps without a click
    run(["-i", str(fin), "-i", v4.AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16",
         "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(FPS), "-vf", "setsar=1", "-af",
         f"afade=t=in:d=0.008,afade=t=out:st={dur - 0.02:.3f}:d=0.02",
         "-c:a", "aac", "-b:a", "320k", "-t", f"{dur:.4f}", "-movflags", "+faststart", str(final)])
    for f in HERE.glob("_f*.mp4"):
        f.unlink()
    print(final)


def main():
    # same render order as before for the intro and lovely backgrounds, so their random picks stay identical
    p1_bg = v4.SEG / "p1_bg.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(bg_track("p1_cut_bg", 0.0, STROBE_T, s30(3))), *enc(fr(STROBE_T)),
         str(p1_bg)])
    strobe = strobe_section(STROBE_T, LINE_IN)
    # letters land on the spoken syllables: SIM 4.57, PLY 4.88, LOVE 5.33, LY 5.70
    w = text_width("SIMPLY", 280)
    lovely = lovely_section(LINE_IN, LINE_OUT, v4.SUBJECT, 40,
                            [("SIMPLY", [4.57, 4.62, 4.67, 4.88, 4.95, 5.02], 960 - 180 - w, 334, 280),
                             ("LOVELY", [5.33, 5.39, 5.45, 5.51, 5.70, 5.76], 960 + 180, 334, 280)],
                            drift=[-14, 14], slice_t=5.80)

    # hook: one continuous fist-pump clip; its first frames end the video, the rest open it
    lead, opening = N_TOTAL - fr(LOOP_T), fr(S1_T)
    hook_beats = [b - LOOP_T for b in BEATS if b >= LOOP_T] + [lead / FPS + b for b in BEATS if b < S1_T]
    hook = hero_section("hook", 0, lead + opening, CUTS / "CA60_rgba", 1, (1.0, 240, 0), push=1.07, beats=hook_beats)
    hook_end, hook_start = trim_clip(hook, 0, lead, "hook_end"), trim_clip(hook, lead, lead + opening, "hook_start")

    f1, f2, f3, f4 = fr(S1_T), fr(S2_T), fr(S3_T), fr(STROBE_T)
    intro = [
        hook_start,
        hero_section("s1_trophy", f1, f2 - f1, CUTS / "CH60_rgba", 1, (1.0, 0, 0), bg_mp4=p1_bg, bg_start=f1),
        hero_section("s2_helmet", f2, f3 - f2, CUTS / "CG60_rgba", 1, (1.0, 0, 0), bg_mp4=p1_bg, bg_start=f2),
        split_section("s3_split", f3, f4 - f3, [(A, 95.5, 0.4), (B, 352.6, 0.5), (A, 47.0, 0.5)]),
        strobe, lovely, *build_section(LINE_OUT, DROP_T),
    ]
    a, b, c = fr(7.448), fr(8.081), fr(8.707)
    drop = [drop_shot(1, *DROP[0]), drop_shot(2, *DROP[1]),
            split_section("d_split", a, b - a, [(B, 386.0, 0.55), (B, 330.6, 0.62), (A, 50.4, 0.5)]),
            hero_section("d_fist", b, c - b, CUTS / "CI60_rgba", 1, (1.0, 70, 0), pool=POOL2)]
    drop += [drop_shot(i, *s) for i, s in enumerate(DROP[2:6], 3)]
    a, b = fr(10.62), fr(11.288)
    drop.append(hero_section("d_look", a, b - a, CUTS / "CJ60_rgba", 1, (1.0, 70, 0), pool=POOL2))
    drop += [drop_shot(i, *s) for i, s in enumerate(DROP[6:], 7)]

    # climax: trophy freeze, title typed beside him (masked behind his outline), glitches out before the loop
    cf, lf = fr(CLIMAX_T), fr(LOOP_T)
    climax = hero_section("climax", cf, lf - cf, CUTS / "CC_rgba", 1, (1.0, 330, 0), push=1.08, freeze=True,
                          glow_always=True, mask_dir=TITLE_MASK, pool=POOL2)
    render_text_frames([("MAX", (12.58, 0.05), 90, 230, 300), ("VERSTAPPEN", (12.78, 0.03), 90, 520, 175),
                        ("4 TIMES WORLD CHAMPION", (12.98, 0.01), 96, 745, 66)],
                       cf / FPS, lf - cf, TITLE_DIR, out_t=cf / FPS + 26 / 30)

    assemble([*intro, *drop, climax, hook_end], HERE / "f1_edit_v05.mp4")


if __name__ == "__main__":
    main()
