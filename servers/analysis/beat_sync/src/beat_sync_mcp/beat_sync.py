import os
import tempfile

import librosa
import numpy as np
from framewright_core import default_output_path, probe_video
from framewright_core import run_ffmpeg as _run_ffmpeg


def detect_beats(music_path: str) -> dict:
    y, sr = librosa.load(music_path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)
    return {
        "tempo": round(float(np.atleast_1d(tempo)[0]), 2),
        "beat_times": [round(float(t), 3) for t in beat_times],
        "duration": round(float(duration), 3),
    }


def _refine_to_onsets(y, sr, beat_times, window=0.07):
    """Move each beat to the nearest fine-grained onset (5.8 ms hop) within `window` seconds."""
    hop = 128
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, units="time")
    if len(onsets) == 0:
        return beat_times
    refined = []
    for t in beat_times:
        o = onsets[np.argmin(np.abs(onsets - t))]
        refined.append(o if abs(o - t) <= window else t)
    return np.array(refined)


def generate_beat_synced_video(
    clip_paths: list[str],
    music_path: str,
    output_path: str | None = None,
    beats_per_cut: int = 1,
    max_duration: float | None = None,
) -> dict:
    if not clip_paths:
        raise ValueError("clip_paths is empty")
    for p in clip_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Video not found: {p}")
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"Music file not found: {music_path}")

    beats_per_cut = max(1, int(beats_per_cut))

    y, sr = librosa.load(music_path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < 2:
        raise RuntimeError("Not enough beats found in the music; try a track with a clearer rhythm")
    beat_times = _refine_to_onsets(y, sr, beat_times)

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

    infos = [probe_video(p, require_video=False) for p in clip_paths]
    w, h = infos[0].width, infos[0].height
    fps = infos[0].fps or 30

    # Snap absolute cut times to frame numbers so rounding never accumulates.
    cut_frames = np.unique(np.round(cut_times * fps).astype(int))
    segment_frames = np.diff(cut_frames)
    if len(segment_frames) == 0:
        raise RuntimeError("No usable segments were produced; check the clips are long enough")
    segment_durations = segment_frames / fps

    if output_path is None:
        output_path = default_output_path(music_path, "beat_synced", ext=".mp4")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cursors = [0.0] * len(clip_paths)

    with tempfile.TemporaryDirectory() as tmp:
        seg_files = []
        for i, (n_frames, dur) in enumerate(zip(segment_frames, segment_durations, strict=True)):
            ci = i % len(clip_paths)
            clip_dur = infos[ci].duration
            start = cursors[ci]
            if start + dur > clip_dur:
                start = 0.0
            cursors[ci] = start + dur

            seg_path = os.path.join(tmp, f"seg_{i:03d}.mp4")
            # tpad clones the last frame if the clip is shorter than the segment.
            vf = (
                f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1,"
                f"tpad=stop_mode=clone:stop_duration={dur:.3f}"
            )
            _run_ffmpeg(
                [
                    "-ss",
                    f"{start}",
                    "-i",
                    clip_paths[ci],
                    "-frames:v",
                    str(int(n_frames)),
                    "-vf",
                    vf,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-pix_fmt",
                    "yuv420p",
                    seg_path,
                ]
            )
            seg_files.append(seg_path)

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in seg_files:
                f.write(f"file '{seg}'\n")
        concatenated = os.path.join(tmp, "concatenated.mp4")
        _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", concatenated])

        total_duration = float(sum(segment_durations))
        _run_ffmpeg(
            [
                "-i",
                concatenated,
                "-i",
                music_path,
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-t",
                f"{total_duration}",
                "-shortest",
                output_path,
            ]
        )

    return {
        "output_path": output_path,
        "tempo": round(float(np.atleast_1d(tempo)[0]), 2),
        "cut_count": len(segment_durations),
        "total_duration": round(float(sum(segment_durations)), 3),
    }
