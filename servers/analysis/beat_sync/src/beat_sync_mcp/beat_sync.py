import json
import os
import subprocess
import tempfile

import librosa
import numpy as np


def _find_tools_dir():
    path = os.path.abspath(os.path.dirname(__file__))
    while True:
        parent, name = os.path.split(path)
        if name == "servers":
            return path
        if parent == path:
            return None
        path = parent


def _get_output_root():
    tools_dir = _find_tools_dir()
    if tools_dir is not None:
        return os.path.join(os.path.dirname(tools_dir), "output")
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "output")


def _default_output_path(music_path):
    base = os.path.splitext(os.path.basename(music_path))[0]
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_beat_synced.mp4")


def _probe(path):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    width = int(vstream["width"]) if vstream else None
    height = int(vstream["height"]) if vstream else None
    duration = float(data["format"].get("duration") or 0.0)
    if vstream:
        num, den = (vstream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = 30.0
    return {"width": width, "height": height, "duration": duration, "fps": fps}


def _run_ffmpeg(args, timeout=1800):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def detect_beats(music_path):
    y, sr = librosa.load(music_path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)
    return {"tempo": round(float(np.atleast_1d(tempo)[0]), 2),
            "beat_times": [round(float(t), 3) for t in beat_times],
            "duration": round(float(duration), 3)}


def generate_beat_synced_video(clip_paths, music_path, output_path=None, beats_per_cut=1, max_duration=None):
    if not clip_paths:
        raise ValueError("clip_paths 不能为空")
    for p in clip_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"找不到视频文件: {p}")
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"找不到音乐文件: {music_path}")

    beats_per_cut = max(1, int(beats_per_cut))

    y, sr = librosa.load(music_path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < 2:
        raise RuntimeError("未能从音乐中检测到足够的节拍")

    cut_times = beat_times[::beats_per_cut]
    if cut_times[0] > 0.01:
        cut_times = np.insert(cut_times, 0, 0.0)

    music_duration = librosa.get_duration(y=y, sr=sr)
    if max_duration:
        max_duration = float(max_duration)
        cut_times = cut_times[cut_times <= max_duration]
        if len(cut_times) < 2 or cut_times[-1] < max_duration:
            cut_times = np.append(cut_times, max_duration)
    else:
        if cut_times[-1] < music_duration:
            cut_times = np.append(cut_times, music_duration)

    segment_durations = np.diff(cut_times)
    segment_durations = segment_durations[segment_durations > 0.05]
    if len(segment_durations) == 0:
        raise RuntimeError("未能生成任何有效片段")

    infos = [_probe(p) for p in clip_paths]
    w, h = infos[0]["width"], infos[0]["height"]
    fps = infos[0]["fps"] or 30

    if output_path is None:
        output_path = _default_output_path(music_path)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cursors = [0.0] * len(clip_paths)

    with tempfile.TemporaryDirectory() as tmp:
        seg_files = []
        for i, dur in enumerate(segment_durations):
            ci = i % len(clip_paths)
            clip_dur = infos[ci]["duration"]
            dur = min(float(dur), clip_dur)
            start = cursors[ci]
            if start + dur > clip_dur:
                start = 0.0
            cursors[ci] = start + dur

            seg_path = os.path.join(tmp, f"seg_{i:03d}.mp4")
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1"
            _run_ffmpeg(["-ss", f"{start}", "-i", clip_paths[ci], "-t", f"{dur}",
                         "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast",
                         "-pix_fmt", "yuv420p", seg_path])
            seg_files.append(seg_path)

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in seg_files:
                f.write(f"file '{seg}'\n")
        concatenated = os.path.join(tmp, "concatenated.mp4")
        _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", concatenated])

        total_duration = float(sum(segment_durations))
        _run_ffmpeg(["-i", concatenated, "-i", music_path, "-map", "0:v", "-map", "1:a",
                     "-c:v", "copy", "-c:a", "aac", "-t", f"{total_duration}", "-shortest", output_path])

    return {"output_path": output_path, "tempo": round(float(np.atleast_1d(tempo)[0]), 2),
            "cut_count": len(segment_durations),
            "total_duration": round(float(sum(segment_durations)), 3)}
