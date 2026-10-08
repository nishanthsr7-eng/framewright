"""F1 demo v3: recreate the reference edit's structure and look with ffmpeg.

Cut times are copied from the reference (same song). Everything is written to demos/f1/output/v03_reference_recreate/ (intermediates in _work/).
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # demos/f1
OUT = ROOT / "output" / "v03_reference_recreate"
SEG = OUT / "_work" / "segments"
SEG.mkdir(parents=True, exist_ok=True)
A = str(ROOT / "input/footage/f1_footage_1.mp4")
B = str(ROOT / "input/footage/f1_footage_2.mp4")
AUDIO = str(ROOT / "output/shared/f1_audio.wav")
FPS = 30
BEAT = 60 / 184.57
FIRST_BEAT = 0.093
END = 14.07

# ---- looks -------------------------------------------------------------
GRADE = "eq=contrast=1.12:saturation=1.25:gamma=0.95,colorbalance=bs=0.06:bm=0.03:rh=0.03"
BASE = "scale=2040:1148,crop=1920:1080"  # slight overscan: hides corner logos, room for shake


def rgb(px):
    return f"rgbashift=rh=-{px}:bh={px}:gv={px // 3}"


GLOW = "split[ga][gb];[gb]gblur=sigma=18,eq=brightness=-0.05[gc];[ga][gc]blend=all_mode=screen:all_opacity=0.35"
SHAKE = "scale=2112:1188,crop=1920:1080:96+22*sin(n*2.3):54+16*cos(n*3.1)"
MBLUR = "tmix=frames=3"
HIGHKEY = "eq=brightness=0.10:contrast=1.35:saturation=0.9,curves=preset=lighter"


def letterbox(t0, t1, h=270, steps=6):
    """Black bars that close in `steps` frame-stepped increments between t0 and t1 (segment time)."""
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


def punch(seg_start, amp=0.07, base=1.04, decay=0.12):
    """Zoom kick on every beat, decaying over `decay` s."""
    ph = f"mod(on/{FPS}+{seg_start}-{FIRST_BEAT},{BEAT:.5f})"
    z = f"{base}+{amp}*max(0,1-{ph}/{decay})"
    return f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps={FPS}"


def push(z0, z1, dur):
    z = f"{z0}+({z1}-{z0})*min(1,on/{dur * FPS:.1f})"
    return f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps={FPS}"


def flash_in(d=0.1):
    return f"fade=t=in:st=0:d={d}:color=white"


# ---- shots after the intro: (start, end, file, source in, speed, effects) ----
SHOTS = [
    # build: three hits, heavy RGB + shake + bars
    (5.833, 6.033, A, 130.5, 1.0, [GRADE, SHAKE, MBLUR, rgb(14), letterbox(-1, 0, 200)]),
    (6.033, 6.233, A, 30.5, 1.0, [GRADE, SHAKE, MBLUR, rgb(16), letterbox(-1, 0, 200)]),
    (6.233, 6.367, A, 132.5, 1.0, [GRADE, SHAKE, MBLUR, rgb(18), letterbox(-1, 0, 200)]),
    # drop hero 1: helmet wave, half speed, beat punches
    (6.367, 8.433, A, 82.0, 0.5, [GRADE, punch(6.367), GLOW, rgb(8), flash_in()]),
    # quick cuts
    (8.433, 8.633, B, 330.0, 1.0, [GRADE, SHAKE, rgb(12), flash_in(0.07)]),
    (8.633, 8.967, A, 52.0, 1.0, [GRADE, SHAKE, MBLUR, rgb(10)]),
    (8.967, 9.167, A, 128.5, 1.0, [GRADE, SHAKE, rgb(12)]),
    (9.167, 9.733, A, 136.0, 0.5, [GRADE, punch(9.167), GLOW, rgb(10)]),
    (9.733, 9.933, B, 298.0, 1.0, [GRADE, SHAKE, MBLUR, rgb(14)]),
    # drop hero 2: smile, slowed, beat punches
    (9.933, 12.133, A, 112.0, 0.6, [GRADE, punch(9.933, amp=0.06), GLOW, rgb(8), flash_in()]),
    # high-key run
    (12.133, 12.467, A, 120.3, 1.0, [HIGHKEY, punch(12.133, amp=0.1), MBLUR, rgb(14), flash_in(0.08)]),
    (12.467, 12.767, A, 136.5, 1.0, [HIGHKEY, punch(12.467, amp=0.1), MBLUR, rgb(14)]),
    (12.767, 13.067, A, 148.3, 1.0, [HIGHKEY, punch(12.767, amp=0.1), MBLUR, rgb(14)]),
    # ending: low car push-in
    (13.067, END, A, 128.2, 0.5, [GRADE, push(1.0, 1.3, END - 13.067), GLOW, rgb(6), flash_in(0.08)]),
]

# intro backgrounds, swapped every two beats behind the cut-out driver
BG_CUTS = [0.0, 0.72, 1.37, 1.997, 2.647, 3.274, 3.924, 4.574, 5.224, 5.833]
BGS = [(A, 18.5), (A, 52.5), (B, 0.6), (B, 48.5), (B, 298.5), (A, 30.8), (A, 34.5), (B, 50.5), (B, 52.5)]


def frames(t0, t1):
    return round(t1 * FPS) - round(t0 * FPS)


def run(args):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])


def enc(n):
    return ["-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p"]


def shot(path, src, t_in, speed, n, chain):
    dur = n / FPS * speed + 0.2
    vf = ",".join([f"setpts=(PTS-STARTPTS)/{speed}", f"fps={FPS}", BASE, *chain])
    run(["-ss", str(t_in), "-t", f"{dur:.3f}", "-i", src, "-filter_complex", vf, *enc(n), str(path)])


def main():
    parts = []
    # intro: background pieces, then the cut-out on top
    bg_list = SEG / "bg.txt"
    with open(bg_list, "w") as f:
        for i, (src, t_in) in enumerate(BGS):
            p = SEG / f"bg_{i:02d}.mp4"
            shot(p, src, t_in, 1.0, frames(BG_CUTS[i], BG_CUTS[i + 1]),
                 [GRADE, "gblur=sigma=4", "eq=brightness=-0.08", rgb(6)])
            f.write(f"file '{p.as_posix()}'\n")
    n_intro = frames(0, 5.833)
    intro = SEG / "s00_intro.mp4"
    graph = (f"[0:v]setpts=PTS-STARTPTS[bg];[1:v]format=rgba,setpts=PTS-STARTPTS,scale=1536:864,pad=1920:1080:192:200:color=black@0[fg];"
             f"[bg][fg]overlay=0:0,{rgb(6)},{GRADE},{push(1.0, 1.08, 5.833)},{GLOW},"
             f"{letterbox(5.4, 5.833, 200)}")
    run(["-f", "concat", "-safe", "0", "-i", str(bg_list),
         "-framerate", str(FPS), "-i", str(OUT / "_work" / "subject_rgba" / "f_%04d.png"),
         "-filter_complex", graph, *enc(n_intro), str(intro)])
    parts.append(intro)

    for i, (t0, t1, src, t_in, speed, chain) in enumerate(SHOTS, 1):
        p = SEG / f"s{i:02d}.mp4"
        shot(p, src, t_in, speed, frames(t0, t1), chain)
        parts.append(p)

    lst = SEG / "all.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    final = OUT / "f1_edit_v03.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-i", AUDIO, "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "320k", "-t", str(END), "-movflags", "+faststart", str(final)])
    print(final)


if __name__ == "__main__":
    main()
