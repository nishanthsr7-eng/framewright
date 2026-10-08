"""F1 demo v5 -> DaVinci Resolve: the same edit as f1_edit_v05.mp4, laid out as an editable timeline.

V1: one clip per section/cut (in the order of _work/segments/all.txt), with v5's unifying colour, beat pulses, LUT,
grain and vignette already applied, exactly as assemble() does before the titles.
V2: the "SIMPLY LOVELY" title, V3: the climax title, both transparent ProRes 4444 with their masks (behind Max).
A1: the song with v5's tiny loop fades.
Media goes to resolve_export/ (an older export is moved to _work/). Writes <repo>/output/framewright_plan.lua; then in Resolve (new project): Workspace > Scripts > Edit > Framewright >
framewright_build_plan.

Run from the repo root (needs v5's _work/segments/ and title frames from render_f1_v05.py):
  uv run --directory servers/render/overlay_fx python demos/f1/output/v05_loop_60fps/resolve_f1_v05.py
Add --plan-only to rewrite framewright_plan.lua for the existing resolve_export/ (e.g. after moving folders).
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_f1_v05 as v5  # noqa: E402

v4, FPS, HERE = v5.v4, v5.FPS, v5.HERE
OUT = HERE / "resolve_export"


def nframes(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                       timeout=300)
    return int(r.stdout.strip())


def finished_without_titles(parts):
    """assemble() + finish() from render_f1_v05.py, stopping before the titles."""
    sys.path[:0] = [str(v4.REPO / "servers/render/lut_grading/src"), str(v4.REPO / "servers/render/overlay_fx/src"),
                    str(v4.REPO / "servers/core/src")]
    from lut_grading_mcp.grading import apply_lut
    from overlay_fx_mcp.effects import add_film_grain, add_vignette

    lst = OUT / "all.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    pulse = v5.windows([b for b in v5.BEATS if b >= 6.4 or b < v5.S1_T], 0.067)
    graph = f"setpts=N/{FPS}/TB,setsar=1,{v5.UNIFY},eq=brightness=0.1:contrast=1.08:enable='{pulse}',{v5.rgb(14, pulse)}"
    pre = OUT / "_f0_assembled.mp4"
    v5.run(["-f", "concat", "-safe", "0", "-i", str(lst), "-vf", graph, *v5.enc(lossless=True), "-r", str(FPS),
            str(pre)])
    p = apply_lut(str(pre), "cinematic_teal_orange", intensity=0.2, output_path=str(OUT / "_f1_lut.mp4"),
                  lossless=True)["output_path"]
    p = add_film_grain(p, intensity=8, output_path=str(OUT / "_f2_grain.mp4"), lossless=True)["output_path"]
    return add_vignette(p, intensity=0.06, output_path=str(OUT / "_f3_vig.mp4"), lossless=True)["output_path"]


def title_layer(k, start, tdir, mdir):
    """The text layer exactly as finish() overlays it (text alpha x mask), as straight-alpha ProRes 4444."""
    n = min(len(list(tdir.glob("t_*.png"))), v5.N_TOTAL - start)
    out = OUT / f"title_{k + 1}.mov"
    v5.run(["-framerate", str(FPS), "-i", str(tdir / "t_%04d.png"), "-framerate", str(FPS), "-i",
            str(mdir / "m_%04d.png"), "-filter_complex",
            "[0:v]format=rgba,split[a][b];[b]alphaextract[c];[1:v]format=gray[m];[c][m]blend=all_mode=multiply[al];"
            "[a][al]alphamerge,format=yuva444p10le", "-frames:v", str(n), "-an", "-c:v", "prores_ks", "-profile:v",
            "4444", str(out)])
    return out, n


def _lua(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, dict):
        return "{" + ", ".join(f"[{json.dumps(str(k))}] = {_lua(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "{" + ", ".join(_lua(x) for x in v) + "}"
    return "nil"


def write_plan():
    """framewright_plan.lua for the media in resolve_export/: cuts back to back on V1, titles on V2/V3, music on A1."""
    clips, markers, start = [], [], 0
    for p in sorted(OUT.glob("[0-9][0-9]_*.mp4")):
        n = nframes(p)
        clips.append({"file": p.as_posix(), "in": 0, "out": n / FPS, "at": start / FPS, "track": 1})
        markers.append({"at": start / FPS, "color": "Blue", "name": p.stem[3:]})
        start += n
    if start != v5.N_TOTAL:
        raise RuntimeError(f"resolve_export holds {start} frames, v5 has {v5.N_TOTAL}: re-run without --plan-only")
    for k, (s, _, _) in enumerate(v5.TEXT_LAYERS):
        p = OUT / f"title_{k + 1}.mov"
        clips.append({"file": p.as_posix(), "in": 0, "out": nframes(p) / FPS, "at": s / FPS, "track": 2 + k,
                      "alpha": True})
    plan = {"source": (HERE / "f1_edit_v05.mp4").as_posix(), "exact": True,
            "project": {"name": "f1_edit_v05", "fps": FPS, "width": 1920, "height": 1080},
            "clips": clips, "music": {"file": (OUT / "music.wav").as_posix(), "start": 0}, "markers": markers}
    lua = v4.REPO / "output" / "framewright_plan.lua"
    lua.parent.mkdir(exist_ok=True)
    lua.write_text("return " + _lua(plan) + "\n", encoding="utf-8")
    return lua


def main():
    if "--plan-only" in sys.argv:
        print(write_plan())
        return
    if OUT.exists():  # Resolve caches media by path, so never overwrite files under an old export
        OUT.rename(v5.WORK / f"resolve_export_{time.strftime('%Y%m%d-%H%M%S')}")
    OUT.mkdir(parents=True)
    # all.txt holds absolute paths; read the names so the folder can move
    names = [line.split("'")[1].split("/")[-1] for line in (v4.SEG / "all.txt").read_text().splitlines() if line.strip()]
    parts = [v4.SEG / n for n in names]
    counts = [nframes(p) for p in parts]
    if sum(counts) != v5.N_TOTAL:
        raise RuntimeError(f"segments hold {sum(counts)} frames, v5 has {v5.N_TOTAL}: re-run render_f1_v05.py")
    full = finished_without_titles(parts)

    start = 0
    for i, (p, n) in enumerate(zip(parts, counts, strict=True)):
        out = OUT / f"{i + 1:02d}_{p.stem}.mp4"
        v5.run(["-i", full, "-vf", f"select='between(n,{start},{start + n - 1})',setpts=N/{FPS}/TB",
                "-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "10", "-preset", "slow", "-profile:v", "high",
                "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)])
        start += n
    for k, (s, tdir, mdir) in enumerate(v5.TEXT_LAYERS):
        title_layer(k, s, tdir, mdir)

    dur = v5.N_TOTAL / FPS
    v5.run(["-i", v4.AUDIO, "-vn", "-af", f"afade=t=in:d=0.008,afade=t=out:st={dur - 0.02:.3f}:d=0.02",
            "-t", f"{dur:.4f}", "-c:a", "pcm_s16le", str(OUT / "music.wav")])
    for f in OUT.glob("_f*.mp4"):
        f.unlink()
    (OUT / "all.txt").unlink()
    lua = write_plan()
    print(f"{len(parts)} cuts, {len(v5.TEXT_LAYERS)} titles, {v5.N_TOTAL} frames -> {OUT}\n{lua}")


if __name__ == "__main__":
    main()
