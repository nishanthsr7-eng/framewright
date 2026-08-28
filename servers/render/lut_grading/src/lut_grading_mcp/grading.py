import os

from framewright_core import default_output_path, probe_video, video_codec_args
from framewright_core import run_ffmpeg as _run_ffmpeg

LUTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "luts")

BUILTIN_LUTS = {
    "cinematic_teal_orange": "teal shadows, orange highlights",
    "warm_vintage": "lifted blacks, warm, slightly desaturated",
    "cool_blue": "blue cast for night or tech scenes",
    "high_contrast_bw": "high-contrast black and white",
    "faded_film": "lifted blacks, soft highlights, low saturation",
    "moody_green": "dark green shadows for suspense",
    "bleach_bypass": "desaturated, high contrast, gritty",
    "anime_vibrant": "punchier cel colours for animation",
}


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def list_luts() -> dict:
    return {
        name: {"description": desc, "path": os.path.join(LUTS_DIR, f"{name}.cube")}
        for name, desc in BUILTIN_LUTS.items()
    }


def _resolve_lut_path(lut):
    if lut in BUILTIN_LUTS:
        return os.path.join(LUTS_DIR, f"{lut}.cube")
    if os.path.exists(lut):
        return lut
    raise FileNotFoundError(
        f"未找到 LUT: {lut}。可用内置 LUT: {', '.join(BUILTIN_LUTS.keys())}，或提供一个存在的 .cube 文件路径。"
    )


def apply_lut(
    input_path: str,
    lut: str,
    intensity: float = 1.0,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    info = probe_video(input_path, require_video=False)
    if not info.has_video:
        raise RuntimeError(f"File has no video stream: {input_path}")

    lut_path = _resolve_lut_path(lut)
    lut_escaped = _escape_filter_path(lut_path)

    intensity = max(0.0, min(1.0, float(intensity)))
    if output_path is None:
        output_path = default_output_path(input_path, "graded")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-i", input_path]
    if intensity >= 0.999:
        args += ["-vf", f"lut3d=file='{lut_escaped}'"]
    else:
        filter_complex = (
            f"[0:v]split[orig][toL];"
            f"[toL]lut3d=file='{lut_escaped}'[graded];"
            f"[orig][graded]blend=all_mode=normal:all_opacity={intensity}[vout]"
        )
        args += ["-filter_complex", filter_complex, "-map", "[vout]"]
        if info.has_audio:
            args += ["-map", "0:a"]

    if info.has_audio:
        args += ["-c:a", "copy"]
    args += (video_codec_args(True) if lossless else []) + [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "lut": lut, "intensity": intensity}
