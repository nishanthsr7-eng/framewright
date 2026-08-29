import os
import shutil
import tempfile

from framewright_core import run_ffmpeg


def frames_to_alpha_video(
    input_folder: str,
    fps: float = 24.0,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    """Encode a folder of RGBA PNGs (sorted by name) as a VP9 webm with an alpha channel."""
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    files = sorted(f for f in os.listdir(input_folder) if f.lower().endswith(".png"))
    if not files:
        raise ValueError(f"No PNG files in {input_folder}; run extract_subject first")

    if output_path is None:
        output_path = input_folder.rstrip("/\\") + ".webm"
    elif not output_path.lower().endswith(".webm"):
        raise ValueError("output_path must end in .webm (the format that keeps alpha)")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    quality = ["-lossless", "1"] if lossless else ["-b:v", "0", "-crf", "30"]
    with tempfile.TemporaryDirectory() as tmp:
        # Renumber so gaps or odd names don't break ffmpeg's %06d pattern; hard links avoid copying.
        for i, name in enumerate(files):
            src, dst = os.path.join(input_folder, name), os.path.join(tmp, f"{i:06d}.png")
            try:
                os.link(src, dst)
            except OSError:
                shutil.copyfile(src, dst)
        run_ffmpeg(
            ["-framerate", f"{fps}", "-i", os.path.join(tmp, "%06d.png")]
            + ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", *quality, "-auto-alt-ref", "0", output_path]
        )
    return {"output_path": output_path, "frame_count": len(files), "fps": fps, "duration": round(len(files) / fps, 3)}
