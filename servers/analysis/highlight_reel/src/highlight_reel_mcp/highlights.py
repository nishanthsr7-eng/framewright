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


def _probe(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if vstream is None:
        raise RuntimeError(f"未找到视频流: {video_path}")
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    duration = float(data["format"].get("duration") or vstream.get("duration") or 0.0)
    num, den = (vstream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) != 0 else 30.0
    return {
        "duration": duration, "has_audio": has_audio,
        "width": int(vstream["width"]), "height": int(vstream["height"]), "fps": fps,
    }


def _run_ffmpeg(args, timeout=1800):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def _default_output_path(video_path):
    base, ext = os.path.splitext(os.path.basename(video_path))
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_highlights{ext if ext else '.mp4'}")


def _score_track(audio_path, sr=22050, hop_length=512):
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    n = min(len(rms), len(onset))
    rms, onset = rms[:n], onset[:n]
    times = librosa.frames_to_time(np.arange(n), sr=sr, hop_length=hop_length)

    def _normalize(a):
        lo, hi = a.min(), a.max()
        return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)

    score = 0.5 * _normalize(rms) + 0.5 * _normalize(onset)
    return times, score


def generate_highlights(video_path, target_duration=30.0, clip_duration=3.0,
                         min_gap=2.0, output_path=None):
    """
    根据音频能量(RMS)和冲击强度(onset strength)自动挑选视频中最"精彩"的若干
    片段，按时间顺序拼接生成一个集锦/预告片。

    target_duration: 集锦总时长目标(秒)，实际可能因片段去重而略短。
    clip_duration: 每个候选片段的长度(秒)。
    min_gap: 两个候选片段中心点之间的最小间隔(秒)，避免选中的片段互相重叠
      或过于集中在同一段。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"找不到文件: {video_path}")

    info = _probe(video_path)
    duration = info["duration"]
    if not info["has_audio"]:
        raise RuntimeError(f"视频没有音轨，无法分析: {video_path}")
    if duration <= clip_duration:
        raise ValueError("视频时长太短，无法生成集锦")

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "audio.wav")
        _run_ffmpeg(["-i", video_path, "-vn", "-ac", "1", "-ar", "22050", audio_path])

        times, score = _score_track(audio_path)

        step = max(0.5, clip_duration / 2)
        candidates = []
        t = 0.0
        while t + clip_duration <= duration:
            mask = (times >= t) & (times < t + clip_duration)
            s = float(score[mask].mean()) if mask.any() else 0.0
            candidates.append((t, t + clip_duration, s))
            t += step

        candidates.sort(key=lambda c: c[2], reverse=True)

        selected = []
        total = 0.0
        for start, end, s in candidates:
            center = (start + end) / 2
            if any(abs(center - (a + b) / 2) < min_gap for a, b, _ in selected):
                continue
            selected.append((start, end, s))
            total += clip_duration
            if total >= target_duration:
                break

        if not selected:
            raise RuntimeError("未能选出任何高光片段")

        selected.sort(key=lambda c: c[0])

        segment_files = []
        for i, (start, end, s) in enumerate(selected):
            seg_path = os.path.join(tmp, f"seg_{i:03d}.mp4")
            _run_ffmpeg([
                "-ss", f"{start}", "-i", video_path, "-t", f"{clip_duration}",
                "-vf", f"fps={info['fps']}",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "44100",
                seg_path,
            ])
            segment_files.append(seg_path)

        if output_path is None:
            output_path = _default_output_path(video_path)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        _run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", output_path,
        ])

    return {
        "output_path": output_path,
        "segments": [
            {"start": round(start, 2), "end": round(end, 2), "score": round(s, 3)}
            for start, end, s in selected
        ],
        "total_duration": round(len(selected) * clip_duration, 2),
    }
