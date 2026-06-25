import json
import os
import shlex
import shutil
import subprocess
import tempfile

from text_overlay_mcp import renderer


def _find_tools_dir():
    """向上查找名为 "servers" 的目录并返回其路径，找不到返回 None。"""
    path = os.path.abspath(os.path.dirname(__file__))
    while True:
        parent, name = os.path.split(path)
        if name == "servers":
            return path
        if parent == path:
            return None
        path = parent


def _get_output_root():
    """返回项目根目录下的 Output 文件夹路径（与 Frame_Extractor_MCP 保持一致）。"""
    tools_dir = _find_tools_dir()
    if tools_dir is not None:
        return os.path.join(os.path.dirname(tools_dir), "output")
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "output")


def _run(cmd, timeout=600):
    proc = subprocess.run(
        shlex.split(cmd, posix=True),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout + "\n" + proc.stderr


def _probe_video(video_path):
    cmd = (
        f"ffprobe -v error -print_format json -show_format -show_streams "
        f"{shlex.quote(video_path)}"
    )
    proc = subprocess.run(
        shlex.split(cmd, posix=True),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {proc.stderr}")
    data = json.loads(proc.stdout)
    v_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if v_stream is None:
        raise RuntimeError("未找到视频流")

    width = int(v_stream["width"])
    height = int(v_stream["height"])

    fps_str = v_stream.get("r_frame_rate", "30/1")
    num, den = fps_str.split("/")
    fps = float(num) / float(den) if float(den) != 0 else 30.0

    duration = float(data["format"].get("duration", v_stream.get("duration", 0)))

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "has_audio": a_stream is not None,
    }


def create_text_overlay(
    video_path,
    text,
    output_folder=None,
    font="anton",
    font_size=None,
    color="#FFFFFF",
    outline_color="#000000",
    outline_width=0,
    shadow=False,
    position="center",
    start_time=0.0,
    duration=None,
    animation="word_by_word",
    fps=None,
):
    if not os.path.isfile(video_path):
        return -1, f"输入视频不存在: {video_path}", ""

    info = _probe_video(video_path)
    width, height, src_fps, src_duration = info["width"], info["height"], info["fps"], info["duration"]

    if fps is None:
        fps = min(src_fps, 30.0)
    if font_size is None:
        font_size = max(int(height * 0.09), 24)
    if duration is None:
        duration = max(src_duration - start_time, 1.0)
    end_time = min(start_time + duration, src_duration)
    duration = max(end_time - start_time, 1.0 / fps)

    if output_folder is None:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_folder = os.path.join(_get_output_root(), f"{video_name}_text_overlay")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    frame_count = max(int(round(duration * fps)), 1)

    tmp_dir = tempfile.mkdtemp(prefix="text_overlay_frames_")
    try:
        for i in range(frame_count):
            progress = i / max(frame_count - 1, 1)
            frame = renderer.render_frame(
                (width, height), text,
                font_name=font, font_size=font_size, color=color,
                outline_color=outline_color, outline_width=outline_width,
                shadow=shadow, position=position, progress=progress,
                animation=animation,
            )
            frame.save(os.path.join(tmp_dir, f"overlay_{i + 1:04d}.png"))

        overlay_path = os.path.join(output_folder, "overlay.webm")
        cmd = (
            f"ffmpeg -y -framerate {fps} -i {shlex.quote(os.path.join(tmp_dir, 'overlay_%04d.png'))} "
            f"-c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 {shlex.quote(overlay_path)}"
        )
        code, log = _run(cmd, timeout=600)
        if code != 0:
            return code, f"生成透明叠加层失败:\n{log}", output_folder

        ext = os.path.splitext(video_path)[1] or ".mp4"
        burned_path = os.path.join(output_folder, f"output_burned{ext}")
        audio_map = "-map 0:a?" if info["has_audio"] else ""
        cmd = (
            f"ffmpeg -y -i {shlex.quote(video_path)} "
            f"-framerate {fps} -i {shlex.quote(os.path.join(tmp_dir, 'overlay_%04d.png'))} "
            f"-filter_complex \"[1:v]format=rgba,setpts=PTS+{start_time}/TB[ov];"
            f"[0:v][ov]overlay=0:0:enable='between(t,{start_time},{end_time})'[v]\" "
            f"-map \"[v]\" {audio_map} -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "
            f"{shlex.quote(burned_path)}"
        )
        code, log = _run(cmd, timeout=1200)
        if code != 0:
            return code, f"生成合成视频失败:\n{log}", output_folder

        msg = (
            f"已生成 {frame_count} 帧文字动画 (fps={fps}, font={font}, "
            f"size={font_size}, animation={animation})\n"
            f"透明叠加层: {overlay_path}\n"
            f"合成视频: {burned_path}"
        )
        return 0, msg, output_folder
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _group_lines(segments, max_words_per_line):
    """将 transcribe_audio 返回的 segments 按 max_words_per_line 切分为字幕行。"""
    lines = []
    for seg in segments:
        words = seg.get("words") or []
        if not words:
            continue
        for i in range(0, len(words), max_words_per_line):
            chunk = words[i:i + max_words_per_line]
            lines.append({
                "start": chunk[0]["start"],
                "end": chunk[-1]["end"],
                "words": chunk,
            })
    return lines


def create_karaoke_captions(
    video_path,
    segments,
    output_folder=None,
    font="anton",
    font_size=None,
    color="#FFFFFF",
    highlight_color="#FFD700",
    outline_color="#000000",
    outline_width=6,
    shadow=True,
    position="bottom",
    max_words_per_line=6,
    fps=None,
):
    if not os.path.isfile(video_path):
        return -1, f"输入视频不存在: {video_path}", ""

    info = _probe_video(video_path)
    width, height, src_fps, src_duration = info["width"], info["height"], info["fps"], info["duration"]

    if fps is None:
        fps = min(src_fps, 30.0)
    if font_size is None:
        font_size = max(int(height * 0.055), 20)

    lines = _group_lines(segments, max_words_per_line)
    if not lines:
        return -1, "segments 中没有可用的词级时间戳 (words)，请先用 transcribe_audio(word_timestamps=True) 获取", ""

    if output_folder is None:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_folder = os.path.join(_get_output_root(), f"{video_name}_karaoke")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    duration = min(lines[-1]["end"] + 0.5, src_duration)
    frame_count = max(int(round(duration * fps)), 1)

    tmp_dir = tempfile.mkdtemp(prefix="karaoke_frames_")
    try:
        line_idx = 0
        for i in range(frame_count):
            t = i / fps
            while line_idx + 1 < len(lines) and t > lines[line_idx]["end"] + 0.15:
                line_idx += 1
            line = lines[line_idx]
            if line["start"] - 0.1 <= t <= line["end"] + 0.15:
                frame = renderer.render_karaoke_frame(
                    (width, height), line["words"], t,
                    font_name=font, font_size=font_size, color=color,
                    highlight_color=highlight_color, outline_color=outline_color,
                    outline_width=outline_width, shadow=shadow, position=position,
                )
            else:
                frame = renderer.render_karaoke_frame((width, height), [], t)
            frame.save(os.path.join(tmp_dir, f"karaoke_{i + 1:04d}.png"))

        overlay_path = os.path.join(output_folder, "overlay.webm")
        cmd = (
            f"ffmpeg -y -framerate {fps} -i {shlex.quote(os.path.join(tmp_dir, 'karaoke_%04d.png'))} "
            f"-c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 {shlex.quote(overlay_path)}"
        )
        code, log = _run(cmd, timeout=600)
        if code != 0:
            return code, f"生成透明叠加层失败:\n{log}", output_folder

        ext = os.path.splitext(video_path)[1] or ".mp4"
        burned_path = os.path.join(output_folder, f"output_burned{ext}")
        audio_map = "-map 0:a?" if info["has_audio"] else ""
        cmd = (
            f"ffmpeg -y -i {shlex.quote(video_path)} "
            f"-framerate {fps} -i {shlex.quote(os.path.join(tmp_dir, 'karaoke_%04d.png'))} "
            f"-filter_complex \"[1:v]format=rgba,setpts=PTS+0/TB[ov];"
            f"[0:v][ov]overlay=0:0:enable='between(t,0,{duration})'[v]\" "
            f"-map \"[v]\" {audio_map} -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "
            f"{shlex.quote(burned_path)}"
        )
        code, log = _run(cmd, timeout=1200)
        if code != 0:
            return code, f"生成合成视频失败:\n{log}", output_folder

        msg = (
            f"已生成 {frame_count} 帧卡拉OK字幕 (fps={fps}, font={font}, size={font_size}, "
            f"{len(lines)} 行)\n"
            f"透明叠加层: {overlay_path}\n"
            f"合成视频: {burned_path}"
        )
        return 0, msg, output_folder
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
