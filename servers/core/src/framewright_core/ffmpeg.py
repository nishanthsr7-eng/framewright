import subprocess


def run_ffmpeg(args, timeout=1800, cwd=None):
    """Run `ffmpeg -y <args>`. Raises RuntimeError with the stderr tail on failure; returns stderr."""
    cmd = ["ffmpeg", "-y"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1500:]}")
    return result.stderr
