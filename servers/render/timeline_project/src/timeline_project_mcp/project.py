import json
import os
import shutil
import subprocess
import tempfile

from framewright_core import output_root as _get_output_root
from framewright_core import run_ffmpeg as _run_ffmpeg

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
    if vstream:
        num, den = (vstream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = 30.0
    return {"width": width, "height": height, "duration": duration, "fps": fps, "has_audio": has_audio}


def _is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def _load_project(project_path):
    if not os.path.exists(project_path):
        raise FileNotFoundError(f"Project file not found: {project_path}")
    with open(project_path, encoding="utf-8") as f:
        return json.load(f)


def _save_project(project_path, project):
    os.makedirs(os.path.dirname(os.path.abspath(project_path)), exist_ok=True)
    with open(project_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)


def create_project(project_path, width=1920, height=1080, fps=30):
    """
    创建一个新的剪辑项目(JSON 文件)，包含空的片段列表和叠加层列表。
    """
    project = {"width": int(width), "height": int(height), "fps": float(fps), "clips": [], "overlays": []}
    _save_project(project_path, project)
    return project


def add_clip(project_path, file, start=0.0, end=None, transition_in=None, transition_in_duration=0.5):
    """
    向项目的主时间轴末尾追加一个片段(视频或图片，按顺序播放)。

    transition_in: 与上一个片段之间的转场名称(参考 effects-mcp 的
      list_transitions()，例如 "fade"/"dissolve"/"wipeleft" 等)。对第一个
      片段无效(没有"上一个片段")。
    transition_in_duration: 转场持续时间(秒)，默认 0.5。
    """
    if not os.path.exists(file):
        raise FileNotFoundError(f"File not found: {file}")

    project = _load_project(project_path)

    if end is None:
        info = _probe(file)
        end = info["duration"] if info["duration"] > 0 else (start + 5.0)

    clip = {"file": file, "start": float(start), "end": float(end)}
    if transition_in:
        clip["transition_in"] = transition_in
        clip["transition_in_duration"] = float(transition_in_duration)

    project["clips"].append(clip)
    _save_project(project_path, project)
    return {"index": len(project["clips"]) - 1, "clip": clip, "clip_count": len(project["clips"])}


def remove_clip(project_path, index):
    """
    删除项目中第 index 个片段(从 0 开始计数)。
    """
    project = _load_project(project_path)
    if index < 0 or index >= len(project["clips"]):
        raise IndexError(f"Index {index} out of range; there are {len(project['clips'])} clips")
    removed = project["clips"].pop(index)
    _save_project(project_path, project)
    return {"removed": removed, "clip_count": len(project["clips"])}


def add_overlay(project_path, file, x=0, y=0, width=None, height=None, opacity=1.0,
                start_time=0.0, end_time=None, audio=False):
    """
    向项目添加一个叠加层(图片或透明视频/webm)，叠加在最终渲染的合成画面上。
    时间区间 start_time/end_time 是相对于最终渲染出的整段视频的时间轴。
    """
    if not os.path.exists(file):
        raise FileNotFoundError(f"File not found: {file}")

    project = _load_project(project_path)
    overlay = {
        "file": file, "x": x, "y": y, "opacity": float(opacity),
        "start_time": float(start_time), "audio": bool(audio),
    }
    if width is not None:
        overlay["width"] = width
    if height is not None:
        overlay["height"] = height
    if end_time is not None:
        overlay["end_time"] = float(end_time)

    project["overlays"].append(overlay)
    _save_project(project_path, project)
    return {"index": len(project["overlays"]) - 1, "overlay": overlay, "overlay_count": len(project["overlays"])}


def remove_overlay(project_path, index):
    """
    删除项目中第 index 个叠加层(从 0 开始计数)。
    """
    project = _load_project(project_path)
    if index < 0 or index >= len(project["overlays"]):
        raise IndexError(f"Index {index} out of range; there are {len(project['overlays'])} overlays")
    removed = project["overlays"].pop(index)
    _save_project(project_path, project)
    return {"removed": removed, "overlay_count": len(project["overlays"])}


def get_project(project_path):
    """
    返回项目的完整内容(片段、叠加层、画布尺寸/帧率)，以及根据片段时长和
    转场估算的总时长。
    """
    project = _load_project(project_path)
    total = 0.0
    for i, clip in enumerate(project["clips"]):
        dur = clip["end"] - clip["start"]
        if i > 0 and clip.get("transition_in"):
            dur -= clip.get("transition_in_duration", 0.5)
        total += max(dur, 0.0)
    project["estimated_duration"] = round(total, 3)
    return project


def _normalize_clip(clip, index, w, h, fps, tmp):
    file_path = clip["file"]
    start, end = clip["start"], clip["end"]
    dur = max(end - start, 0.05)
    seg_path = os.path.join(tmp, f"norm_{index:03d}.mp4")
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},setsar=1"
    )

    if _is_image(file_path):
        args = ["-loop", "1", "-t", f"{dur}", "-i", file_path,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        args += ["-t", f"{dur}", "-map", "0:v", "-map", "1:a"]
    else:
        info = _probe(file_path)
        args = ["-ss", f"{start}", "-i", file_path]
        if not info["has_audio"]:
            args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            args += ["-t", f"{dur}", "-map", "0:v", "-map", "1:a"]
        else:
            args += ["-t", f"{dur}"]

    args += ["-vf", vf, "-ar", "44100", "-ac", "2",
             "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", seg_path]
    _run_ffmpeg(args)
    return seg_path


def _merge_clips(normalized, project_clips, tmp):
    running = normalized[0]
    running_dur = project_clips[0]["end"] - project_clips[0]["start"]

    for i in range(1, len(normalized)):
        clip_dur = project_clips[i]["end"] - project_clips[i]["start"]
        transition = project_clips[i].get("transition_in")
        seg = normalized[i]
        out_path = os.path.join(tmp, f"merge_{i:03d}.mp4")

        if transition:
            t_dur = project_clips[i].get("transition_in_duration", 0.5)
            t_dur = max(0.05, min(t_dur, running_dur, clip_dur))
            offset = max(0.0, running_dur - t_dur)
            vfilter = (
                f"[1:v]setsar=1,settb=AVTB[v1];"
                f"[0:v]setsar=1,settb=AVTB[v0];"
                f"[v0][v1]xfade=transition={transition}:duration={t_dur}:offset={offset}[v]"
            )
            afilter = f"[0:a][1:a]acrossfade=d={t_dur}[a]"
            args = ["-i", running, "-i", seg, "-filter_complex", vfilter + ";" + afilter,
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", out_path]
            _run_ffmpeg(args)
            running_dur = running_dur + clip_dur - t_dur
        else:
            concat_list = os.path.join(tmp, f"concat_{i:03d}.txt")
            with open(concat_list, "w", encoding="utf-8") as f:
                f.write(f"file '{running}'\n")
                f.write(f"file '{seg}'\n")
            args = ["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", out_path]
            _run_ffmpeg(args)
            running_dur += clip_dur

        running = out_path

    return running


def _apply_overlays(base_path, overlays, tmp):
    base_info = _probe(base_path)
    total = base_info["duration"]

    input_args = ["-i", base_path]
    filter_parts = []
    last_label = "0:v"
    audio_inputs = [(0, 0.0)] if base_info["has_audio"] else []

    for j, layer in enumerate(overlays):
        idx = j + 1
        file_path = layer["file"]
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Overlay file not found: {file_path}")

        start = max(0.0, float(layer.get("start_time", 0.0)))
        end = float(layer["end_time"]) if layer.get("end_time") is not None else total
        end = min(end, total)
        if end <= start:
            continue
        layer_dur = end - start

        is_image = _is_image(file_path)
        if is_image:
            input_args += ["-loop", "1", "-t", f"{layer_dur}", "-i", file_path]
            chain = [f"[{idx}:v]format=rgba"]
        else:
            input_args += ["-i", file_path]
            chain = [f"[{idx}:v]trim=duration={layer_dur},setpts=PTS-STARTPTS,format=rgba"]

        width = layer.get("width")
        height = layer.get("height")
        if width or height:
            wv = width if width else -1
            hv = height if height else -1
            chain.append(f"scale={wv}:{hv}")

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
    composited = os.path.join(tmp, "composited.mp4")
    args = input_args + ["-filter_complex", filter_complex, "-map", f"[{final_video_label}]"]
    if audio_label is not None:
        args += ["-map", "0:a" if audio_label == "0:a" else f"[{audio_label}]"]
    args += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", composited]
    _run_ffmpeg(args)
    return composited


def render_project(project_path, output_path=None):
    """
    渲染整个项目: 按顺序裁剪/缩放每个片段到统一画布尺寸和帧率，应用片段间的
    转场，再叠加所有叠加层，输出最终视频文件。
    """
    project = _load_project(project_path)
    if not project["clips"]:
        raise ValueError("The timeline has no clips")

    w, h, fps = project["width"], project["height"], project["fps"]

    with tempfile.TemporaryDirectory() as tmp:
        normalized = [
            _normalize_clip(clip, i, w, h, fps, tmp)
            for i, clip in enumerate(project["clips"])
        ]

        base = _merge_clips(normalized, project["clips"], tmp)

        if project.get("overlays"):
            base = _apply_overlays(base, project["overlays"], tmp)

        if output_path is None:
            base_name = os.path.splitext(os.path.basename(project_path))[0]
            out_dir = os.path.join(_get_output_root(), base_name)
            os.makedirs(out_dir, exist_ok=True)
            output_path = os.path.join(out_dir, f"{base_name}_render.mp4")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        shutil.copy(base, output_path)

    info = _probe(output_path)
    return {
        "output_path": output_path,
        "duration": round(info["duration"], 3),
        "clip_count": len(project["clips"]),
        "overlay_count": len(project.get("overlays", [])),
    }
