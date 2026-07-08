import os
import subprocess

PAN_DIRECTIONS = {
    "center", "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top",
}


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


def _default_output_path(input_path, suffix="ken_burns"):
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_{suffix}.mp4")


def _run_ffmpeg(args, timeout=1800):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def create_ken_burns(image_path, duration=5.0, zoom_start=1.0, zoom_end=1.3, pan="center",
                      width=1920, height=1080, fps=30, output_path=None):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"找不到图片: {image_path}")
    if pan not in PAN_DIRECTIONS:
        raise ValueError(f"pan 必须是: {', '.join(sorted(PAN_DIRECTIONS))}")

    duration = float(duration)
    fps = int(fps)
    d = max(2, int(round(duration * fps)))

    z_expr = f"{zoom_start}+({zoom_end}-{zoom_start})*on/{d - 1}"

    if pan == "left_to_right":
        x_expr = f"(iw-iw/zoom)*(on/{d - 1})"
    elif pan == "right_to_left":
        x_expr = f"(iw-iw/zoom)*(1-on/{d - 1})"
    else:
        x_expr = "(iw-iw/zoom)/2"

    if pan == "top_to_bottom":
        y_expr = f"(ih-ih/zoom)*(on/{d - 1})"
    elif pan == "bottom_to_top":
        y_expr = f"(ih-ih/zoom)*(1-on/{d - 1})"
    else:
        y_expr = "(ih-ih/zoom)/2"

    vf = (
        f"scale=3840:-2,"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={d}:s={width}x{height}:fps={fps},"
        f"format=yuv420p"
    )

    if output_path is None:
        output_path = _default_output_path(image_path)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-loop", "1", "-i", image_path, "-vf", vf, "-t", f"{duration}",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", output_path]
    _run_ffmpeg(args)

    return {"output_path": output_path, "duration": duration, "zoom_start": zoom_start,
            "zoom_end": zoom_end, "pan": pan, "width": width, "height": height, "fps": fps}
