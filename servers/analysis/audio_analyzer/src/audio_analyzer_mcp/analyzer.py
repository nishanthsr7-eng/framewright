import logging
import os
import subprocess
import tempfile
from typing import Any

import librosa
import numpy as np

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv"}
SOUNDFILE_EXTS = {".wav", ".flac", ".ogg", ".aiff", ".aif"}


def _load_audio(audio_path, sr: Any = 22050, offset=0.0, duration=None) -> tuple[np.ndarray, int]:
    """
    加载音频文件（或视频文件中的音轨）为单声道波形数据。
    若输入是视频文件，先用 ffmpeg 提取音轨为临时 wav。
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File not found: {audio_path}")

    ext = os.path.splitext(audio_path)[1].lower()
    src_path = audio_path
    tmp_path = None
    # Decode anything soundfile can't read with our own ffmpeg call: librosa's audioread
    # fallback spawns ffmpeg with the MCP stdin attached and can hang.
    if ext in VIDEO_EXTS or ext not in SOUNDFILE_EXTS:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        tmp_path = tmp.name
        ffmpeg_sr = sr if sr else 44100
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            audio_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(ffmpeg_sr),
            tmp_path,
        ]
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            os.remove(tmp_path)
            raise RuntimeError(f"ffmpeg could not extract the audio: {result.stderr[-1000:]}")
        src_path = tmp_path

    try:
        y, sr = librosa.load(src_path, sr=sr, mono=True, offset=offset, duration=duration)
    finally:
        if tmp_path is not None:
            os.remove(tmp_path)

    return y, int(sr)


def get_audio_info(audio_path: str) -> dict:
    """
    返回音频/视频文件的基本信息：时长、采样率、整体响度(RMS)、估计的响度范围。
    """
    y, sr = _load_audio(audio_path, sr=None)
    duration = float(librosa.get_duration(y=y, sr=sr))
    rms = librosa.feature.rms(y=y)[0]
    return {
        "duration": round(duration, 3),
        "sample_rate": int(sr),
        "rms_mean": round(float(np.mean(rms)), 5),
        "rms_max": round(float(np.max(rms)), 5),
    }


def detect_beats(audio_path: str, start_time: float = 0.0, duration: float | None = None) -> dict:
    """
    检测节拍/速度(BPM)以及每个节拍点的时间戳，可用于按节奏剪辑/卡点。
    """
    y, sr = _load_audio(audio_path, offset=start_time, duration=duration)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr) + start_time
    tempo_val = float(np.atleast_1d(tempo)[0])
    return {
        "tempo_bpm": round(tempo_val, 2),
        "beat_times": [round(float(t), 3) for t in beat_times],
        "beat_count": len(beat_times),
    }


def detect_downbeats(
    audio_path: str,
    start_time: float = 0.0,
    duration: float | None = None,
    beats_per_bar: int = 4,
) -> dict:
    """
    在节拍的基础上估计"重拍"(downbeat，每个小节的第一拍)的时间点，适合用作大段落/
    转场/最强特效的卡点（比单纯的节拍点更稀疏、更重）。

    原理：对节拍按 beats_per_bar 分组(相位 0..beats_per_bar-1)，选择平均 onset 强度
    最大的相位作为重拍相位。

    Optional params:
      beats_per_bar (int): 每小节的拍数，默认 4 (4/4 拍，最常见)。
    """
    y, sr = _load_audio(audio_path, offset=start_time, duration=duration)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])

    if len(beat_frames) == 0:
        return {"tempo_bpm": round(tempo_val, 2), "downbeat_times": [], "downbeat_count": 0}

    strengths = np.array([onset_env[f] if f < len(onset_env) else 0.0 for f in beat_frames])
    best_phase = 0
    best_score = -1.0
    for phase in range(min(beats_per_bar, len(beat_frames))):
        score = float(np.mean(strengths[phase::beats_per_bar]))
        if score > best_score:
            best_score = score
            best_phase = phase

    downbeat_frames = beat_frames[best_phase::beats_per_bar]
    downbeat_times = librosa.frames_to_time(downbeat_frames, sr=sr) + start_time
    return {
        "tempo_bpm": round(tempo_val, 2),
        "beats_per_bar": beats_per_bar,
        "downbeat_times": [round(float(t), 3) for t in downbeat_times],
        "downbeat_count": len(downbeat_times),
    }


def detect_sections(
    audio_path: str,
    start_time: float = 0.0,
    duration: float | None = None,
    n_sections: int | None = None,
) -> dict:
    """
    将音频分割为若干结构性段落(如 intro/build/drop/outro)，并按相对能量给出标签，
    适合定位"高潮/drop"位置以放置最强的特效/文字。

    标签规则(基于每段平均 RMS 能量的相对大小，启发式，非音乐理论上的精确分段):
      - "intro": 第一段
      - "outro": 最后一段
      - "drop": 能量最高的段落 (若不是 intro/outro)
      - "build": 能量介于平均值和最高值之间、且出现在 drop 之前的段落
      - "verse": 其余低于平均能量的段落
      - "chorus": 其余高于平均能量的段落

    Optional params:
      n_sections (int): 段落数量。不传则按时长自动估计 (时长/8秒，限制在 2~8 之间)。
    """
    y, sr = _load_audio(audio_path, offset=start_time, duration=duration)
    total_duration = float(librosa.get_duration(y=y, sr=sr))

    if n_sections is None:
        n_sections = int(np.clip(round(total_duration / 8.0), 2, 8))
    n_sections = max(2, min(n_sections, max(2, int(total_duration // 1) or 2)))

    hop_length = 512
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    n = min(mfcc.shape[1], chroma.shape[1], len(rms))
    mfcc, chroma, rms = mfcc[:, :n], chroma[:, :n], rms[:n]
    features = np.vstack([mfcc, chroma])

    try:
        bound_frames = librosa.segment.agglomerative(features, n_sections)
    except (librosa.util.exceptions.ParameterError, ValueError) as e:  # too few frames to cluster
        logging.warning("Section clustering failed, using even splits: %s", e)
        bound_frames = np.linspace(0, n, n_sections, endpoint=False, dtype=int)

    bound_frames = sorted(set(int(b) for b in bound_frames) | {0, n})
    bound_times = librosa.frames_to_time(bound_frames, sr=sr, hop_length=hop_length)

    raw_sections = []
    for i in range(len(bound_frames) - 1):
        a, b = bound_frames[i], bound_frames[i + 1]
        if b <= a:
            continue
        raw_sections.append(
            {
                "start": float(bound_times[i]),
                "end": float(bound_times[i + 1]),
                "energy": float(np.mean(rms[a:b])),
            }
        )

    if not raw_sections:
        return {"sections": []}

    energies = np.array([s["energy"] for s in raw_sections])
    mean_e, max_e = float(np.mean(energies)), float(np.max(energies))
    drop_idx = int(np.argmax(energies))

    sections = []
    for i, s in enumerate(raw_sections):
        if i == 0:
            label = "intro"
        elif i == len(raw_sections) - 1:
            label = "outro"
        elif i == drop_idx:
            label = "drop"
        elif s["energy"] >= mean_e:
            label = "build" if i < drop_idx else "chorus"
        else:
            label = "verse"
        sections.append(
            {
                "label": label,
                "start": round(s["start"] + start_time, 3),
                "end": round(s["end"] + start_time, 3),
                "energy": round(s["energy"] / max_e, 3) if max_e > 0 else 0.0,
            }
        )

    return {"sections": sections}


def detect_impacts(
    audio_path: str,
    start_time: float = 0.0,
    duration: float | None = None,
    sensitivity: float = 1.0,
) -> dict:
    """
    检测音频中的"冲击/瞬态"时刻（鼓点、打击、突然的响度变化等），
    适合用作卡点/转场/特效触发的时间点。

    sensitivity: 越大检测到越多的瞬态点 (传给 librosa onset_detect 的 delta 的反比因子)。
    """
    y, sr = _load_audio(audio_path, offset=start_time, duration=duration)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    delta = max(0.01, 0.07 / max(sensitivity, 0.01))
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, backtrack=True, delta=delta)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr) + start_time

    # 每个瞬态点的相对强度 (0~1，相对于本片段最大值归一化)
    max_strength = float(np.max(onset_env)) if len(onset_env) > 0 and np.max(onset_env) > 0 else 1.0
    impacts = []
    for frame, t in zip(onset_frames, onset_times, strict=True):
        strength = float(onset_env[frame]) / max_strength if frame < len(onset_env) else 0.0
        impacts.append({"time": round(float(t), 3), "strength": round(strength, 3)})

    return {
        "impact_count": len(impacts),
        "impacts": impacts,
    }


def analyze_audio_features(
    audio_path: str,
    start_time: float = 0.0,
    duration: float | None = None,
    window: float = 1.0,
) -> dict:
    """
    按固定时间窗口分析音频的频谱/能量特征，输出每个窗口的:
      - rms (能量/响度)
      - spectral_centroid (频谱中心，越高听感越"明亮/尖锐")
      - zero_crossing_rate (过零率，噪音/打击乐成分越高越大)
    以及整段的均值/最大值汇总，可用于识别整体最有"冲击力"或最安静的片段。
    """
    y, sr = _load_audio(audio_path, offset=start_time, duration=duration)

    hop_length = 512
    frame_length = 2048
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    zcr = librosa.feature.zero_crossing_rate(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    win_frames = max(1, int(round(window * sr / hop_length)))
    n_windows = max(1, int(np.ceil(len(rms) / win_frames)))

    windows = []
    for i in range(n_windows):
        a, b = i * win_frames, min((i + 1) * win_frames, len(rms))
        if a >= b:
            break
        windows.append(
            {
                "time": round(float(times[a] + start_time), 3),
                "rms": round(float(np.mean(rms[a:b])), 5),
                "spectral_centroid": round(float(np.mean(centroid[a:b])), 2),
                "zero_crossing_rate": round(float(np.mean(zcr[a:b])), 5),
            }
        )

    return {
        "window_seconds": window,
        "windows": windows,
        "summary": {
            "rms_mean": round(float(np.mean(rms)), 5),
            "rms_max": round(float(np.max(rms)), 5),
            "spectral_centroid_mean": round(float(np.mean(centroid)), 2),
            "zero_crossing_rate_mean": round(float(np.mean(zcr)), 5),
        },
    }


_WHISPER_MODELS = {}


def _get_whisper_model(model_size):
    if model_size not in _WHISPER_MODELS:
        import ctranslate2
        from faster_whisper import WhisperModel

        model = None
        # GPU first (CUDA float16); fall back to CPU int8 if CUDA libs are missing
        if ctranslate2.get_cuda_device_count() > 0:
            try:
                model = WhisperModel(model_size, device="cuda", compute_type="float16")
                # cuBLAS/cuDNN load lazily on the first encode; warm up so a missing DLL falls back here
                list(model.transcribe(np.zeros(16000, dtype=np.float32), language="en")[0])
            except Exception as e:
                model = None
                logging.warning("CUDA Whisper load failed, using CPU: %s", e)
        if model is None:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
        _WHISPER_MODELS[model_size] = model
    return _WHISPER_MODELS[model_size]


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    language: str | None = None,
    word_timestamps: bool = True,
) -> dict:
    """
    使用 faster-whisper 将音频/视频中的语音转录为文字，支持词级时间戳。
    首次调用某个 model_size 时会从 huggingface 自动下载模型权重（需要联网，之后会缓存）。
    """
    ext = os.path.splitext(audio_path)[1].lower()
    src_path = audio_path
    tmp_path = None
    # Decode anything soundfile can't read with our own ffmpeg call: librosa's audioread
    # fallback spawns ffmpeg with the MCP stdin attached and can hang.
    if ext in VIDEO_EXTS or ext not in SOUNDFILE_EXTS:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        tmp_path = tmp.name
        cmd = ["ffmpeg", "-y", "-i", audio_path, "-vn", "-ac", "1", "-ar", "16000", tmp_path]
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            os.remove(tmp_path)
            raise RuntimeError(f"ffmpeg could not extract the audio: {result.stderr[-1000:]}")
        src_path = tmp_path

    try:
        model = _get_whisper_model(model_size)
        segments_iter, info = model.transcribe(src_path, language=language, word_timestamps=word_timestamps)

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            words = []
            if word_timestamps and seg.words:
                for w in seg.words:
                    words.append(
                        {
                            "word": w.word.strip(),
                            "start": round(float(w.start), 3),
                            "end": round(float(w.end), 3),
                        }
                    )
            segments.append(
                {
                    "start": round(float(seg.start), 3),
                    "end": round(float(seg.end), 3),
                    "text": seg.text.strip(),
                    "words": words,
                }
            )
            full_text_parts.append(seg.text.strip())
    finally:
        if tmp_path is not None:
            os.remove(tmp_path)

    return {
        "language": info.language,
        "language_probability": round(float(info.language_probability), 3),
        "text": " ".join(full_text_parts).strip(),
        "segments": segments,
    }
