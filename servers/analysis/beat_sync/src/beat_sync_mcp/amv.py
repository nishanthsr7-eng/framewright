"""Auto AMV: analyze music + clips, pick shots by motion, and write a beat-cut edit plan (docs/edit-plan.md)."""

import json
import logging
import os
import re
import subprocess

import librosa
import numpy as np
from framewright_core import output_root as _get_output_root

from beat_sync_mcp.plan import PLAN_VERSION, _media_info, _repo_root, write_plan_lua

# Beats per cut in each section label; None = no cuts inside the section (the previous shot holds).
PACES: dict[str, dict[str, int]] = {
    "hype": {"intro": 4, "verse": 2, "build": 2, "drop": 1, "chorus": 1, "outro": 4},
    "steady": {"intro": 4, "verse": 2, "build": 2, "drop": 2, "chorus": 2, "outro": 4},
    "chill": {"intro": 8, "verse": 4, "build": 4, "drop": 2, "chorus": 2, "outro": 8},
}
HIGH_ENERGY = ("drop", "chorus")
# anime: hard cuts and held frames -> lower scene threshold; live footage has motion that looks like cuts.
STYLE = {"anime": {"scene": 0.3, "min_shot": 0.5}, "general": {"scene": 0.4, "min_shot": 0.7}}
MW, MH, MFPS = 64, 36, 12  # motion analysis grid


def _analyze_music(path, beats_per_bar=4):
    """Beats, downbeats and energy-labelled sections, same method as audio_analyzer."""
    y, sr = librosa.load(path, sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    beats = librosa.frames_to_time(frames, sr=sr)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    if len(frames) < 2:
        raise RuntimeError("Not enough beats found in the music; try a track with a clearer rhythm")
    strength = np.array([onset[f] if f < len(onset) else 0.0 for f in frames])
    phase = int(np.argmax([strength[p::beats_per_bar].mean() for p in range(min(beats_per_bar, len(frames)))]))
    downbeats = beats[phase::beats_per_bar]

    total = float(librosa.get_duration(y=y, sr=sr))
    n_sec = int(np.clip(round(total / 8.0), 2, 8))
    hop = 512
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    n = min(mfcc.shape[1], chroma.shape[1], len(rms))
    try:
        bounds = librosa.segment.agglomerative(np.vstack([mfcc[:, :n], chroma[:, :n]]), n_sec)
    except (librosa.util.exceptions.ParameterError, ValueError) as e:  # too few frames to cluster
        logging.warning("Section clustering failed, using even splits: %s", e)
        bounds = np.linspace(0, n, n_sec, endpoint=False, dtype=int)
    bounds = sorted(set(int(b) for b in bounds) | {0, n})
    times = librosa.frames_to_time(bounds, sr=sr, hop_length=hop)
    raw = [
        (float(times[i]), float(times[i + 1]), float(rms[bounds[i] : bounds[i + 1]].mean()))
        for i in range(len(bounds) - 1)
        if bounds[i + 1] > bounds[i]
    ]
    energies = np.array([r[2] for r in raw])
    drop = int(np.argmax(energies))
    sections = []
    for i, (a, b, e) in enumerate(raw):
        if i == 0:
            label = "intro"
        elif i == len(raw) - 1:
            label = "outro"
        elif i == drop:
            label = "drop"
        elif e >= energies.mean():
            label = "build" if i < drop else "chorus"
        else:
            label = "verse"
        sections.append({"label": label, "start": round(a, 3), "end": round(b, 3)})
    return {
        "tempo": round(tempo, 2),
        "duration": total,
        "beats": [round(float(t), 3) for t in beats],
        "downbeats": [round(float(t), 3) for t in downbeats],
        "sections": sections,
    }


def _analyze_clip(path, scene_threshold):
    """One ffmpeg pass: scene-cut times (scene filter) + per-frame motion and brightness at 12 fps."""
    graph = (
        f"[0:v]fps={MFPS},scale={MW}:{MH},format=gray,split[m][s];[s]select='gt(scene,{scene_threshold})',showinfo[o]"
    )
    r = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            path,
            "-filter_complex",
            graph,
            "-map",
            "[m]",
            "-f",
            "rawvideo",
            "-",
            "-map",
            "[o]",
            "-f",
            "null",
            os.devnull,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=1800,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg could not analyze {path}: {r.stderr.decode(errors='replace')[-500:]}")
    fr = np.frombuffer(r.stdout, np.uint8)
    fr = fr[: len(fr) // (MW * MH) * MW * MH].reshape(-1, MH, MW).astype(np.float32)
    if len(fr) < 2:
        raise RuntimeError(f"No video frames decoded from {path}")
    cuts = [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr.decode(errors="replace"))]
    motion = np.r_[0, np.abs(np.diff(fr, axis=0)).mean((1, 2))]
    return cuts, motion, fr.mean((1, 2))


def _rel(path):
    root = _repo_root()
    full = os.path.abspath(path)
    try:
        rel = os.path.relpath(full, root)
    except ValueError:  # other drive on Windows
        return full.replace("\\", "/")
    return full.replace("\\", "/") if rel.startswith("..") else rel.replace("\\", "/")


def auto_amv_plan(
    clip_paths: list[str],
    music_path: str,
    output_path: str | None = None,
    end_time: float | None = None,
    style: str = "anime",
    pace: str = "hype",
    fps: float = 24.0,
    title: str | None = None,
    project_name: str | None = None,
) -> dict:
    _media_info(music_path)
    infos = [_media_info(p) for p in clip_paths]
    if any(i["fps"] is None for i in infos):
        bad = [p for p, i in zip(clip_paths, infos, strict=True) if i["fps"] is None]
        raise ValueError(f"No video stream in {bad}; pass video files as clip_paths")
    cfg = STYLE[style]
    audio = _analyze_music(music_path)
    end = min(float(end_time), audio["duration"]) if end_time else audio["duration"]
    beats = [b for b in audio["beats"] if b < end]
    down = [d for d in audio["downbeats"] if d < end]
    sections: list[dict] = [dict(s, end=min(s["end"], end)) for s in audio["sections"] if s["start"] < end]

    # shot pool
    shots, motion_by_clip = [], []
    for k, path in enumerate(clip_paths):
        cuts, motion, bright = _analyze_clip(path, cfg["scene"])
        motion_by_clip.append(motion)
        edges = [0.0] + [c for c in cuts if 0 < c < infos[k]["duration"]] + [infos[k]["duration"]]
        for a, b in zip(edges, edges[1:], strict=False):
            fa, fb = int(a * MFPS), int(b * MFPS)
            if b - a < cfg["min_shot"] or fb - fa < 3 or bright[fa:fb].mean() < 25:  # too short or too dark
                continue
            shots.append(
                {
                    "clip": k,
                    "start": a,
                    "end": b,
                    "motion": float(np.percentile(motion[fa + 1 : fb], 75)),
                    "used": False,
                }
            )
    if not shots:
        raise RuntimeError("No usable shots (all too short or too dark); try style='anime' or brighter clips")
    rank = np.argsort([-s["motion"] for s in shots])
    logging.info("auto_amv_plan: %d usable shots", len(shots))

    steps = PACES[pace]
    grid = [0.0]
    for sec in sections:
        step = steps.get(sec["label"], 2)
        sb = [b for b in beats if sec["start"] <= b < sec["end"]]
        grid += sb[::step] if step else []
    grid = sorted(set(round(c, 3) for c in grid if c < end - 0.2)) + [round(end, 3)]

    def section_at(t):
        return next((s["label"] for s in sections if s["start"] <= t < s["end"]), "verse")

    def pick(energy, length):
        order = {"hi": rank, "mid": rank[len(rank) // 5 :], "calm": rank[::-1]}[energy]
        for need_len in (True, False):  # second pass allows shorter shots (slowed down)
            for i in order:
                s = shots[i]
                if not s["used"] and (not need_len or s["end"] - s["start"] >= length):
                    s["used"] = True
                    return s
        for s in shots:  # pool exhausted: reuse
            s["used"] = False
        return pick(energy, length)

    clips = []
    for at, nxt in zip(grid, grid[1:], strict=False):
        length = nxt - at
        label = section_at(at)
        s = pick({"drop": "hi", "chorus": "hi", "intro": "calm", "outro": "calm"}.get(label, "mid"), length)
        span = s["end"] - s["start"] - 1 / fps
        speed = 1.0 if span >= length else max(0.25, round(span / length, 3))
        use = length * speed
        prof = motion_by_clip[s["clip"]]
        a, b = int(s["start"] * MFPS), int(s["end"] * MFPS)
        win = max(1, int(use * MFPS))
        start = s["start"]
        if b - a > win:  # slide to the most active window
            start += int(np.argmax(np.convolve(prof[a:b], np.ones(win), "valid"))) / MFPS
        start = max(s["start"], min(start, s["end"] - use - 1 / fps)) + 1 / fps  # skip the cut frame
        c = {
            "file": _rel(clip_paths[s["clip"]]),
            "in": round(start, 3),
            "out": round(start + use, 3),
            "track": 1,
            "at": round(at, 3),
            "speed": speed,
            "section": label,
        }
        if label in HIGH_ENERGY and any(abs(at - d) < 0.05 for d in down):
            c["transition_in"] = {"type": "Flash White", "frames": 3}
            c["effects"] = ["Screen Shake"]
        clips.append(c)

    titles = []
    if title:
        first_hit = next((c["at"] for c in clips if "transition_in" in c), clips[0]["at"])
        titles.append({"text": title, "at": first_hit, "duration": 1.5, "track": 2, "template": "Center Title"})
    stem = os.path.splitext(os.path.basename(music_path))[0]
    w, h = infos[0]["width"] or 1920, infos[0]["height"] or 1080
    plan = {
        "version": PLAN_VERSION,
        "project": {"name": project_name or f"{stem}_amv", "width": w, "height": h, "fps": fps},
        "music": {"file": _rel(music_path), "start": 0.0, "gain_db": 0},
        "beat_grid": {"bpm": audio["tempo"], "beats": beats, "downbeats": down, "sections": sections},
        "clips": clips,
        "titles": titles,
        "markers": [
            {"at": s["start"], "color": "Red" if s["label"] in HIGH_ENERGY else "Blue", "name": s["label"]}
            for s in sections
        ],
        "notes": f"auto_amv_plan: style={style}, pace={pace}. Flash White + Screen Shake mark drop/chorus downbeats.",
    }
    if output_path is None:
        out_dir = os.path.join(_get_output_root(), stem)
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "amv_plan.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1)
    lua_path = write_plan_lua(plan, output_path)
    return {
        "output_path": output_path,
        "resolve_lua": lua_path,
        "clip_count": len(clips),
        "duration": round(end, 3),
        "bpm": audio["tempo"],
        "flashes": sum("transition_in" in c for c in clips),
        "slowed": sum(c["speed"] < 1 for c in clips),
        "shots_available": len(shots),
        "sections": [f"{s['label']} {s['start']}-{s['end']}" for s in sections],
    }
