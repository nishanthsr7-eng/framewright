import os
import tempfile
from functools import partial

import numpy as np
from framewright_core import default_output_path, probe_video, run_ffmpeg, video_codec_args
from PIL import Image

_run_ffmpeg = partial(run_ffmpeg, timeout=900)


def _sample_pixels(video_path, samples=5):
    info = probe_video(video_path)
    duration = max(info.duration, 0.1)
    pixels = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(samples):
            t = duration * (i + 1) / (samples + 1)
            frame_path = os.path.join(tmp, f"frame_{i}.png")
            args = ["-ss", f"{t}", "-i", video_path, "-frames:v", "1", frame_path]
            _run_ffmpeg(args)
            img = Image.open(frame_path).convert("RGB")
            arr = np.asarray(img, dtype=np.float64).reshape(-1, 3)
            pixels.append(arr)
    return np.concatenate(pixels, axis=0)


def get_color_profile(video_path: str, samples: int = 5) -> dict:
    """
    采样视频中的若干帧，计算 RGB 三通道的均值和标准差，用于了解视频的整体
    亮度/色调/对比度风格。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")

    pixels = _sample_pixels(video_path, samples=samples)
    mean = pixels.mean(axis=0)
    std = pixels.std(axis=0)
    return {
        "mean_rgb": [round(float(v), 2) for v in mean],
        "std_rgb": [round(float(v), 2) for v in std],
        "samples": samples,
    }


def match_color(
    reference_path: str,
    target_path: str,
    output_path: str | None = None,
    samples: int = 5,
    strength: float = 1.0,
    lossless: bool = False,
) -> dict:
    """
    将 target_path 的色彩风格(亮度/对比度/色调)匹配到 reference_path，
    通过采样两个视频的帧、比较 RGB 通道的均值和标准差，计算每个通道的
    线性增益和偏移，并应用到 target_path 上。

    strength: 匹配强度 0~1，1.0 = 完全匹配参考视频的统计特征，
      0.0 = 不做改变。默认 1.0。
    """
    if not os.path.exists(reference_path):
        raise FileNotFoundError(f"File not found: {reference_path}")
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"File not found: {target_path}")

    ref_pixels = _sample_pixels(reference_path, samples=samples)
    tgt_pixels = _sample_pixels(target_path, samples=samples)

    ref_mean, ref_std = ref_pixels.mean(axis=0), ref_pixels.std(axis=0)
    tgt_mean, tgt_std = tgt_pixels.mean(axis=0), tgt_pixels.std(axis=0)

    gains = []
    offsets = []
    for c in range(3):
        gain = ref_std[c] / tgt_std[c] if tgt_std[c] > 1e-6 else 1.0
        gain = float(np.clip(gain, 0.5, 2.0))
        offset = ref_mean[c] - tgt_mean[c] * gain
        offset = float(np.clip(offset, -150.0, 150.0))

        gain = 1.0 + (gain - 1.0) * strength
        offset = offset * strength

        gains.append(gain)
        offsets.append(offset)

    info = probe_video(target_path)

    if output_path is None:
        output_path = default_output_path(target_path, "color_matched")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    channels = ["r", "g", "b"]
    exprs = []
    for c, ch in enumerate(channels):
        exprs.append(f"{ch}='clip(val*{gains[c]}+{offsets[c]},0,255)'")
    vf = "lutrgb=" + ":".join(exprs)

    args = ["-i", target_path, "-vf", vf]
    if info.has_audio:
        args += ["-c:a", "copy"]
    args += (video_codec_args(True) if lossless else []) + [output_path]

    _run_ffmpeg(args)
    return {
        "output_path": output_path,
        "gains_rgb": [round(g, 4) for g in gains],
        "offsets_rgb": [round(o, 2) for o in offsets],
    }
