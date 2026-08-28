import os
import tempfile

import librosa
import numpy as np
from framewright_core import default_output_path, probe_video
from framewright_core import run_ffmpeg as _run_ffmpeg


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


def generate_highlights(
    video_path: str,
    target_duration: float = 30.0,
    clip_duration: float = 3.0,
    min_gap: float = 2.0,
    output_path: str | None = None,
) -> dict:
    """
    根据音频能量(RMS)和冲击强度(onset strength)自动挑选视频中最"精彩"的若干
    片段，按时间顺序拼接生成一个集锦/预告片。

    target_duration: 集锦总时长目标(秒)，实际可能因片段去重而略短。
    clip_duration: 每个候选片段的长度(秒)。
    min_gap: 两个候选片段中心点之间的最小间隔(秒)，避免选中的片段互相重叠
      或过于集中在同一段。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")

    info = probe_video(video_path)
    duration = info.duration
    if not info.has_audio:
        raise RuntimeError(f"Video has no audio track to analyse: {video_path}")
    if duration <= clip_duration:
        raise ValueError("Video is too short for a highlight reel; lower clip_duration")

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
            raise RuntimeError("No highlight moments found; lower target_duration or clip_duration")

        selected.sort(key=lambda c: c[0])

        segment_files = []
        for i, (start, end, s) in enumerate(selected):
            seg_path = os.path.join(tmp, f"seg_{i:03d}.mp4")
            _run_ffmpeg(
                [
                    "-ss",
                    f"{start}",
                    "-i",
                    video_path,
                    "-t",
                    f"{clip_duration}",
                    "-vf",
                    f"fps={info.fps}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-ar",
                    "44100",
                    seg_path,
                ]
            )
            segment_files.append(seg_path)

        if output_path is None:
            output_path = default_output_path(video_path, "highlights")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        _run_ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                output_path,
            ]
        )

    return {
        "output_path": output_path,
        "segments": [
            {"start": round(start, 2), "end": round(end, 2), "score": round(s, 3)} for start, end, s in selected
        ],
        "total_duration": round(len(selected) * clip_duration, 2),
    }
