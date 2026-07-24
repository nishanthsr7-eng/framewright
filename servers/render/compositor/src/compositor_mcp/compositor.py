import json
import os
import subprocess
from functools import partial

from framewright_core import output_root as _get_output_root
from framewright_core import run_ffmpeg

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


def _probe(path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    width = int(vstream["width"]) if vstream else None
    height = int(vstream["height"]) if vstream else None
    duration = float(
        data["format"].get("duration")
        or (vstream.get("duration") if vstream else 0)
        or 0.0
    )
    return {"width": width, "height": height, "duration": duration, "has_audio": has_audio}


_run_ffmpeg = partial(run_ffmpeg, timeout=900)


def _video_codec(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=60,
    )
    return result.stdout.strip()


def _is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def _default_output_path(base_video):
    base, ext = os.path.splitext(os.path.basename(base_video))
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_composite{ext if ext else '.mp4'}")


def compose_layers(base_video, layers, output_path=None):
    """
    将多个图层(图片/视频, 含 alpha 透明通道)按位置/时间区间叠加合成到 base_video 上。

    layers 为按从下到上的顺序排列的层级列表，每层为一个 dict:
      - file (str, 必填): 图层文件路径(图片或视频/webm)。
      - x, y (str|int, 默认 0): 叠加位置(像素或 ffmpeg overlay 表达式，例如
        "(W-w)/2" 表示水平居中, "W-w-20" 表示右对齐留20px边距)。
      - width, height (int, 可选): 缩放该层到指定尺寸(给一个为-1则按比例缩放)。
      - opacity (float, 默认 1.0): 不透明度 0~1。
      - start_time, end_time (float, 可选): 该层在主视频时间轴上可见的区间(秒)，
        默认整段可见。
      - audio (bool, 默认 False): 仅对视频层有效；为 True 时将该层自身的音频
        (从 start_time 开始)与主视频音频混合。
    """
    if not os.path.exists(base_video):
        raise FileNotFoundError(f"File not found: {base_video}")
    if not layers:
        raise ValueError("layers is empty")

    base_info = _probe(base_video)
    total = base_info["duration"]

    input_args = ["-i", base_video]
    filter_parts = []
    last_label = "0:v"

    audio_inputs = []
    if base_info["has_audio"]:
        audio_inputs.append((0, 0.0))

    for i, layer in enumerate(layers):
        idx = i + 1
        file_path = layer["file"]
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Layer file not found: {file_path}")

        start = max(0.0, float(layer.get("start_time", 0.0)))
        end = float(layer["end_time"]) if layer.get("end_time") is not None else total
        end = min(end, total)
        if end <= start:
            raise ValueError(f"layer {i}: end_time must be greater than start_time")
        layer_dur = end - start

        is_image = _is_image(file_path)
        if is_image:
            input_args += ["-loop", "1", "-t", f"{layer_dur}", "-i", file_path]
            chain = [f"[{idx}:v]format=rgba"]
        else:
            # ffmpeg's native VP9 decoder drops alpha; libvpx keeps it (overlay.webm, subject.webm)
            codec = _video_codec(file_path)
            decoder = {"vp9": ["-c:v", "libvpx-vp9"], "vp8": ["-c:v", "libvpx"]}.get(codec, [])
            input_args += decoder + ["-i", file_path]
            chain = [f"[{idx}:v]trim=duration={layer_dur},setpts=PTS-STARTPTS,format=rgba"]

        width = layer.get("width")
        height = layer.get("height")
        if width or height:
            w = width if width else -1
            h = height if height else -1
            chain.append(f"scale={w}:{h}")

        opacity = float(layer.get("opacity", 1.0))
        if opacity < 1.0:
            chain.append(f"colorchannelmixer=aa={opacity}")

        if start > 0:
            chain.append(f"tpad=start_duration={start}:start_mode=clone")
        pad_after = total - end
        if pad_after > 0:
            chain.append(f"tpad=stop_duration={pad_after}:stop_mode=clone")

        layer_label = f"lyr{idx}"
        filter_parts.append(",".join(chain) + f"[{layer_label}]")

        x = layer.get("x", 0)
        y = layer.get("y", 0)
        out_label = f"v{idx}"
        filter_parts.append(
            f"[{last_label}][{layer_label}]overlay=x={x}:y={y}:"
            f"enable='between(t,{start},{end})'[{out_label}]"
        )
        last_label = out_label

        if layer.get("audio") and not is_image:
            audio_inputs.append((idx, start))

    final_video_label = last_label

    if not audio_inputs:
        audio_label = None
    elif len(audio_inputs) == 1 and audio_inputs[0] == (0, 0.0):
        audio_label = "0:a"
    else:
        mix_labels = []
        for input_idx, delay in audio_inputs:
            if delay > 0:
                lbl = f"a{input_idx}"
                ms = int(round(delay * 1000))
                filter_parts.append(f"[{input_idx}:a]adelay=delays={ms}:all=1[{lbl}]")
                mix_labels.append(lbl)
            else:
                mix_labels.append(f"{input_idx}:a")
        labels_str = "".join(f"[{l}]" for l in mix_labels)
        filter_parts.append(
            f"{labels_str}amix=inputs={len(mix_labels)}:duration=first:dropout_transition=0[aout]"
        )
        audio_label = "aout"

    filter_complex = ";".join(filter_parts)

    if output_path is None:
        output_path = _default_output_path(base_video)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = input_args + ["-filter_complex", filter_complex, "-map", f"[{final_video_label}]"]
    if audio_label is not None:
        args += ["-map", "0:a" if audio_label == "0:a" else f"[{audio_label}]"]
    args += [output_path]

    _run_ffmpeg(args)
    return {"output_path": output_path, "layer_count": len(layers), "duration": total}
