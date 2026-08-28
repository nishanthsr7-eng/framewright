import os
import shlex
import shutil
import subprocess
import tempfile

from framewright_core import output_root as _get_output_root
from framewright_core import probe_video, video_codec_args

from text_overlay_mcp import renderer


def _run(cmd, timeout=600):
    proc = subprocess.run(
        shlex.split(cmd, posix=True),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout + "\n" + proc.stderr


def _burn_codec(lossless: bool) -> str:
    return " ".join(video_codec_args(True)) if lossless else "-c:v libx264 -crf 18 -pix_fmt yuv420p"


def create_text_overlay(
    video_path: str,
    text: str,
    output_folder: str | None = None,
    font: str = "anton",
    font_size: int | None = None,
    color: str = "#FFFFFF",
    outline_color: str = "#000000",
    outline_width: int = 0,
    shadow: bool = False,
    position: str = "center",
    start_time: float = 0.0,
    duration: float | None = None,
    animation: str = "word_by_word",
    fps: float | None = None,
    lossless: bool = False,
) -> tuple[int, str, str]:
    if not os.path.isfile(video_path):
        return -1, f"Input video not found: {video_path}", ""

    info = probe_video(video_path)
    width, height, src_fps, src_duration = info.width, info.height, info.fps, info.duration

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
                (width, height),
                text,
                font_name=font,
                font_size=font_size,
                color=color,
                outline_color=outline_color,
                outline_width=outline_width,
                shadow=shadow,
                position=position,
                progress=progress,
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
            return code, f"Rendering the transparent overlay failed:\n{log}", output_folder

        ext = os.path.splitext(video_path)[1] or ".mp4"
        burned_path = os.path.join(output_folder, f"output_burned{ext}")
        audio_map = "-map 0:a?" if info.has_audio else ""
        cmd = (
            f"ffmpeg -y -i {shlex.quote(video_path)} "
            f"-framerate {fps} -i {shlex.quote(os.path.join(tmp_dir, 'overlay_%04d.png'))} "
            f'-filter_complex "[1:v]format=rgba,setpts=PTS+{start_time}/TB[ov];'
            f"[0:v][ov]overlay=0:0:enable='between(t,{start_time},{end_time})'[v]\" "
            f'-map "[v]" {audio_map} {_burn_codec(lossless)} -c:a copy '
            f"{shlex.quote(burned_path)}"
        )
        code, log = _run(cmd, timeout=1200)
        if code != 0:
            return code, f"Rendering the burned-in video failed:\n{log}", output_folder

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
            chunk = words[i : i + max_words_per_line]
            lines.append(
                {
                    "start": chunk[0]["start"],
                    "end": chunk[-1]["end"],
                    "words": chunk,
                }
            )
    return lines


def create_karaoke_captions(
    video_path: str,
    segments: list[dict],
    output_folder: str | None = None,
    font: str = "anton",
    font_size: int | None = None,
    color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    outline_color: str = "#000000",
    outline_width: int = 6,
    shadow: bool = True,
    position: str = "bottom",
    max_words_per_line: int = 6,
    fps: float | None = None,
    lossless: bool = False,
) -> tuple[int, str, str]:
    if not os.path.isfile(video_path):
        return -1, f"Input video not found: {video_path}", ""

    info = probe_video(video_path)
    width, height, src_fps, src_duration = info.width, info.height, info.fps, info.duration

    if fps is None:
        fps = min(src_fps, 30.0)
    if font_size is None:
        font_size = max(int(height * 0.055), 20)

    lines = _group_lines(segments, max_words_per_line)
    if not lines:
        return -1, "segments have no word timings; run transcribe_audio(word_timestamps=True) first", ""

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
                    (width, height),
                    line["words"],
                    t,
                    font_name=font,
                    font_size=font_size,
                    color=color,
                    highlight_color=highlight_color,
                    outline_color=outline_color,
                    outline_width=outline_width,
                    shadow=shadow,
                    position=position,
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
            return code, f"Rendering the transparent overlay failed:\n{log}", output_folder

        ext = os.path.splitext(video_path)[1] or ".mp4"
        burned_path = os.path.join(output_folder, f"output_burned{ext}")
        audio_map = "-map 0:a?" if info.has_audio else ""
        cmd = (
            f"ffmpeg -y -i {shlex.quote(video_path)} "
            f"-framerate {fps} -i {shlex.quote(os.path.join(tmp_dir, 'karaoke_%04d.png'))} "
            f'-filter_complex "[1:v]format=rgba,setpts=PTS+0/TB[ov];'
            f"[0:v][ov]overlay=0:0:enable='between(t,0,{duration})'[v]\" "
            f'-map "[v]" {audio_map} {_burn_codec(lossless)} -c:a copy '
            f"{shlex.quote(burned_path)}"
        )
        code, log = _run(cmd, timeout=1200)
        if code != 0:
            return code, f"Rendering the burned-in video failed:\n{log}", output_folder

        msg = (
            f"已生成 {frame_count} 帧卡拉OK字幕 (fps={fps}, font={font}, size={font_size}, "
            f"{len(lines)} 行)\n"
            f"透明叠加层: {overlay_path}\n"
            f"合成视频: {burned_path}"
        )
        return 0, msg, output_folder
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
