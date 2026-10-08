"""F1 demo v4: v3's reference structure plus transitions, beat pulses, cut-out glow,
zoom blur, kinetic title, and a Framewright finishing pass (LUT, light leak, grain, vignette).

Run from the repo root:  python demos/f1/output/v04_transitions_titles/render_f1_v04.py
Everything is written to demos/f1/output/v04_transitions_titles/ (intermediates in _work/).
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ROOT = REPO / "demos" / "f1"
OUT = ROOT / "output" / "v04_transitions_titles"
SEG = OUT / "_work" / "segments"
SEG.mkdir(parents=True, exist_ok=True)
A = str(ROOT / "input/footage/f1_footage_1.mp4")
B = str(ROOT / "input/footage/f1_footage_2.mp4")
AUDIO = str(ROOT / "output/shared/f1_audio.wav")
SUBJECT = ROOT / "output/v03_reference_recreate/_work/subject_rgba"
FPS = 30
BEAT = 60 / 184.57
FIRST_BEAT = 0.093
END = 14.07
BEATS = [0.093, 0.395, 0.72, 1.045, 1.37, 1.695, 1.997, 2.322, 2.647, 2.972, 3.274, 3.599, 3.924, 4.249, 4.574,
         4.899, 5.224, 5.526, 5.828, 6.13, 6.455, 6.78, 7.105, 7.43, 7.755, 8.081, 8.382, 8.707, 9.033, 9.358,
         9.66, 9.961, 10.286, 10.635, 10.96, 11.262, 11.587, 11.912, 12.214, 12.539, 12.864, 13.189]
DOWNBEATS = [6.13, 7.43, 8.707, 9.961, 11.262, 12.539]
K = 4  # transition length in frames

# fonts are copied next to the outputs so ffmpeg can use a plain relative path
for f in ("impact.ttf", "arialbd.ttf"):
    if not (OUT / f).exists():
        shutil.copy(Path("C:/Windows/Fonts") / f, OUT / f)

# ---- looks -------------------------------------------------------------
GRADE = "eq=contrast=1.14:saturation=1.22:gamma=0.95,colorbalance=rs=-0.04:gs=0.01:bs=0.05:rh=0.05:gh=0.02:bh=-0.04"
HIGHKEY = "eq=brightness=0.08:contrast=1.4:saturation=0.85,curves=preset=lighter"
BASE = "scale=2040:1148,crop=1920:1080"  # overscan hides corner logos
MBLUR = "tmix=frames=3"
# blend in RGB: a screen blend on YUV chroma planes tints everything magenta
GLOW = ("format=gbrp,split[ga][gb];[gb]gblur=sigma=20,eq=brightness=-0.04[gc];"
        "[ga][gc]blend=all_mode=screen:all_opacity=0.38,format=yuv420p")


def rgb(px, enable=None):
    en = f":enable='{enable}'" if enable else ""
    return f"rgbashift=rh=-{px}:bh={px}:gv={px // 3}{en}"


def zoomblur(enable=None, s1=1.05, s2=1.11):
    """Radial zoom blur: average the frame with two centred enlargements."""
    en = f":enable='{enable}'" if enable else ""
    return (f"split=3[za][zb][zc];[zb]scale=iw*{s1}:-1,crop=1920:1080[zb2];[zc]scale=iw*{s2}:-1,crop=1920:1080[zc2];"
            f"[za][zb2]blend=all_mode=average{en}[zab];[zab][zc2]blend=all_mode=average{en}")


def shake(amp=22):
    return f"scale=2112:1188,crop=1920:1080:96+{amp}*sin(n*2.3):54+{amp * 0.7:.0f}*cos(n*3.1)"


def edge(n, k=K):
    """ffmpeg expression true on the first and last k frames of an n-frame shot."""
    return f"lt(n,{k})+gte(n,{n - k})"


def zp(seg_start, n, base=1.04, punch=0.0, zin=0.0, zout=0.0, push=None, k=K):
    """One zoompan: base zoom, optional slow push, beat punches, zoom-through in/out transitions."""
    z = str(base)
    if push:
        z = f"{push[0]}+({push[1]}-{push[0]})*min(1,on/{n})"
    if punch:
        ph = f"mod(on/{FPS}+{seg_start}-{FIRST_BEAT},{BEAT:.5f})"
        z += f"+{punch}*max(0,1-{ph}/0.12)"
    if zin:
        z += f"+{zin}*max(0,1-on/{k})"
    if zout:
        z += f"+{zout}*max(0,(on-{n - k})/{k})"
    return f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps={FPS}"


def whip(n, din=0, dout=0, k=K):
    """Horizontal whip pan in (din) and/or out (dout); direction -1 left, +1 right."""
    x = f"192+192*({din}*max(0,1-n/{k})+{dout}*max(0,(n-{n - k})/{k}))"
    en = []
    if din:
        en.append(f"lt(n,{k})")
    if dout:
        en.append(f"gte(n,{n - k})")
    return f"scale=2304:1296,crop=1920:1080:'{x}':108,avgblur=sizeX=48:sizeY=1:enable='{'+'.join(en)}'"


def glitch(n, k=2):
    e = edge(n, k)
    return f"{rgb(36, e)},noise=alls=45:allf=t:enable='{e}',{shake(40)}"


def flash_in(d=0.1):
    return f"fade=t=in:st=0:d={d}:color=white"


# ---- shots after the intro -------------------------------------------------
# (start, end, file, source in, speed, look, extras)
#   extras: punch, push, zin, zout, whip_in, whip_out, glitch, flash, zb (zoom blur on edges), shake
SHOTS = [
    (5.833, 6.033, A, 130.5, 1.0, "grade", dict(glitch=True, shake=30, rgb=16, bars=200, zb=True)),
    (6.033, 6.233, A, 30.5, 1.0, "grade", dict(glitch=True, shake=30, rgb=18, bars=200, zb=True)),
    (6.233, 6.367, A, 132.5, 1.0, "grade", dict(glitch=True, shake=36, rgb=22, bars=200, zout=0.5, zb=True)),
    (6.367, 8.433, A, 82.4, 0.5, "grade", dict(flash=0.12, zin=0.45, punch=0.07, glow=True, rgb=8, whip_out=1)),
    (8.433, 8.633, B, 330.0, 1.0, "grade", dict(whip_in=1, shake=22, rgb=12, zout=0.35, zb=True)),
    (8.633, 8.967, A, 52.0, 1.0, "grade", dict(zin=0.35, whip_out=-1, rgb=10, mblur=True, zb=True)),
    (8.967, 9.167, A, 128.5, 1.0, "grade", dict(whip_in=-1, shake=22, rgb=12, zout=0.35, zb=True)),
    (9.167, 9.733, A, 136.0, 0.5, "grade", dict(zin=0.35, punch=0.08, glow=True, rgb=10, glitch=True)),
    (9.733, 9.933, B, 298.0, 1.0, "grade", dict(glitch=True, shake=28, rgb=14, mblur=True, zout=0.5, zb=True)),
    (9.933, 12.133, A, 112.0, 0.6, "grade", dict(flash=0.12, zin=0.45, punch=0.06, glow=True, rgb=8, whip_out=1)),
    (12.133, 12.467, A, 120.3, 1.0, "highkey", dict(flash=0.08, whip_in=1, punch=0.1, rgb=14, mblur=True,
                                                     zbfull=True, zout=0.3)),
    (12.467, 12.767, A, 136.5, 1.0, "highkey", dict(zin=0.3, punch=0.1, rgb=14, mblur=True, zbfull=True, zout=0.3)),
    (12.767, 13.067, A, 148.3, 1.0, "highkey", dict(zin=0.3, punch=0.1, rgb=14, mblur=True, zbfull=True,
                                                     zout=0.6)),
    (13.067, END, A, 128.2, 0.5, "grade", dict(flash=0.08, push=(1.0, 1.32), glow=True, rgb=6)),
]

# intro backgrounds, swapped every two beats behind the cut-out driver
BG_CUTS = [0.0, 0.72, 1.37, 1.997, 2.647, 3.274, 3.924, 4.574, 5.224, 5.833]
BGS = [(A, 33.5), (A, 52.5), (B, 0.6), (B, 48.5), (B, 298.5), (A, 30.8), (A, 34.5), (B, 50.5), (B, 52.5)]


def frames(t0, t1):
    return round(t1 * FPS) - round(t0 * FPS)


def run(args):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=1800, cwd=OUT)
    if r.returncode:
        raise RuntimeError(r.stderr[-2500:])


def enc(n=None, lossless=False):
    q = ["-qp", "0", "-preset", "ultrafast"] if lossless else ["-crf", "14", "-preset", "medium"]
    fr = ["-frames:v", str(n)] if n else []
    return [*fr, "-an", "-c:v", "libx264", *q, "-pix_fmt", "yuv420p"]


def letterbox(t0, t1, h=200, steps=6):
    f0, f1 = round(t0 * FPS), round(t1 * FPS)
    out = []
    for k in range(1, steps + 1):
        hk = round(h * k / steps)
        a = f0 + (f1 - f0) * (k - 1) // steps
        b = f0 + (f1 - f0) * k // steps
        en = f"gte(n,{a})" if k == steps else f"between(n,{a},{b - 1})"
        for y in ("0", f"ih-{hk}"):
            out.append(f"drawbox=x=0:y={y}:w=iw:h={hk}:c=black:t=fill:enable='{en}'")
    return ",".join(out)


def bars(h):
    return f"drawbox=x=0:y=0:w=iw:h={h}:c=black:t=fill,drawbox=x=0:y=ih-{h}:w=iw:h={h}:c=black:t=fill"


def build_chain(t0, n, look, x):
    k = min(K, max(1, n // 2))
    c = [GRADE if look == "grade" else HIGHKEY]
    if x.get("whip_in") or x.get("whip_out"):
        c.append(whip(n, x.get("whip_in", 0), x.get("whip_out", 0), k))
    c.append(zp(t0, n, punch=x.get("punch", 0), zin=x.get("zin", 0), zout=x.get("zout", 0),
                push=x.get("push"), k=k))
    if x.get("shake"):
        c.append(shake(x["shake"]))
    if x.get("mblur"):
        c.append(MBLUR)
    if x.get("zbfull"):
        c.append(zoomblur(s1=1.03, s2=1.07))
    elif x.get("zb"):
        c.append(zoomblur(edge(n, k)))
    if x.get("glow"):
        c.append(GLOW)
    c.append(rgb(x.get("rgb", 8)))
    if x.get("glitch"):
        c.append(glitch(n))
    if x.get("bars"):
        c.append(bars(x["bars"]))
    if x.get("flash"):
        c.append(flash_in(x["flash"]))
    return c


def shot(path, src, t_in, speed, n, chain):
    dur = n / FPS * speed + 0.25
    vf = ",".join([f"setpts=(PTS-STARTPTS)/{speed}", f"fps={FPS}", BASE, *chain])
    run(["-ss", str(t_in), "-t", f"{dur:.3f}", "-i", src, "-filter_complex", vf, *enc(n), str(path)])


def render_intro():
    bg_list = SEG / "bg.txt"
    with open(bg_list, "w") as f:
        for i, (src, t_in) in enumerate(BGS):
            p = SEG / f"bg_{i:02d}.mp4"
            n = frames(BG_CUTS[i], BG_CUTS[i + 1])
            # background zooms OUT against the driver's push-in: parallax depth
            chain = [GRADE, zp(BG_CUTS[i], n, base=1.0, push=(1.16, 1.02)), "gblur=sigma=3",
                     "eq=brightness=-0.1", rgb(6), flash_in(0.06) if i else "null"]
            shot(p, src, t_in, 1.0, n, chain)
            f.write(f"file '{p.as_posix()}'\n")
    n = frames(0, 5.833)
    beat_en = "+".join(f"between(t,{b:.3f},{b + 0.07:.3f})" for b in BEATS if b < 5.8)
    graph = (
        "[0:v]setpts=PTS-STARTPTS[bg];"
        "[1:v]format=rgba,setpts=PTS-STARTPTS,scale=1536:864,pad=1920:1080:192:200:color=black@0[fg];"
        "[fg]split[f1][f2];"
        # white rim glow behind the cut-out
        "[f2]lutrgb=r=255:g=255:b=255,scale=1570:883,pad=1920:1080:175:191:color=black@0,gblur=sigma=7[rim];"
        "[bg][rim]overlay=0:0[b1];[b1][f1]overlay=0:0,"
        f"{GRADE},{zp(0, n, base=1.0, push=(1.0, 1.1))},{GLOW},{rgb(6)},"
        f"setpts=N/{FPS}/TB,{rgb(18, beat_en)},eq=brightness=0.08:enable='{beat_en}',"
        f"{letterbox(5.4, 5.833)}"
    )
    out = SEG / "s00_intro.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(bg_list), "-framerate", str(FPS),
         "-i", str(SUBJECT / "f_%04d.png"), "-filter_complex", graph, *enc(n), str(out)])
    return out


def finishing(src):
    """Framewright tools: teal/orange LUT, film grain, light vignette."""
    sys.path[:0] = [str(REPO / "servers/render/lut_grading/src"), str(REPO / "servers/render/overlay_fx/src"),
                    str(REPO / "servers/core/src")]
    from lut_grading_mcp.grading import apply_lut
    from overlay_fx_mcp.effects import add_film_grain, add_vignette

    p = apply_lut(str(src), "cinematic_teal_orange", intensity=0.3, output_path=str(OUT / "_f1_lut.mp4"),
                  lossless=True)["output_path"]
    p = add_film_grain(p, intensity=10, output_path=str(OUT / "_f3_grain.mp4"), lossless=True)["output_path"]
    p = add_vignette(p, intensity=0.12, output_path=str(OUT / "_f4_vig.mp4"), lossless=True)["output_path"]
    return Path(p)


def main():
    parts = [render_intro()]
    for i, (t0, t1, src, t_in, speed, look, x) in enumerate(SHOTS, 1):
        n = frames(t0, t1)
        p = SEG / f"s{i:02d}.mp4"
        shot(p, src, t_in, speed, n, build_chain(t0, n, look, x))
        parts.append(p)

    lst = SEG / "all.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    assemble_and_finish(lst, OUT / "f1_edit_v04.mp4")


def assemble_and_finish(lst, final, titles=True):
    """Concat the segments, add beat pulses + kinetic title, run the finishing tools, mux the music."""
    drop = [b for b in BEATS if b >= 6.4]
    pulse = "+".join(f"between(t,{b:.3f},{b + 0.067:.3f})" for b in drop)
    title = (
        # animated fontsize crashes ffmpeg's drawtext: use two fixed sizes for the slam-in
        "drawtext=fontfile=impact.ttf:text='MAX':fontsize=300:fontcolor=white:"
        "x=(w-tw)/2:y=(h-th)/2-80:enable='between(t,13.189,13.32)',"
        "drawtext=fontfile=impact.ttf:text='MAX':fontsize=220:fontcolor=white:"
        "x=(w-tw)/2:y=(h-th)/2-80:enable='gt(t,13.32)',"
        "drawtext=fontfile=impact.ttf:text='VERSTAPPEN':fontsize=130:fontcolor=white:"
        "x=(w-tw)/2:y=(h/2)+70:enable='gte(t,13.42)',"
        "drawtext=fontfile=arialbd.ttf:text='2021 WORLD CHAMPION':fontsize=38:fontcolor=white@0.85:"
        "x=(w-tw)/2:y=(h/2)+215:enable='gte(t,13.62)',"
        f"{rgb(10, 'gte(t,13.189)')}"
    )
    graph = f"setpts=N/{FPS}/TB,eq=brightness=0.1:contrast=1.08:enable='{pulse}',{rgb(14, pulse)}"
    if titles:
        graph += f",{title}"
    pre = OUT / "_f0_assembled.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-vf", graph, *enc(lossless=True), "-r", str(FPS), str(pre)])

    fin = finishing(pre)
    run(["-i", str(fin), "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16",
         "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-t", str(END),
         "-movflags", "+faststart", str(final)])
    for f in OUT.glob("_f*.mp4"):
        f.unlink()
    print(final)


if __name__ == "__main__":
    main()
