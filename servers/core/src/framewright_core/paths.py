import os


def servers_dir(start: str | None = None) -> str | None:
    """Walk up from `start` (default: this file) to the `servers` folder; None if not found."""
    path = os.path.abspath(start or os.path.dirname(__file__))
    while True:
        parent, name = os.path.split(path)
        if name == "servers":
            return path
        if parent == path:
            return None
        path = parent


def output_root(start: str | None = None) -> str:
    """`<repo>/output`, or `./output` next to `start` when not inside the repo."""
    tools_dir = servers_dir(start)
    if tools_dir is not None:
        return os.path.join(os.path.dirname(tools_dir), "output")
    return os.path.join(os.path.abspath(start or os.getcwd()), "output")


def default_output_path(input_path: str, suffix: str, ext: str | None = None, default_ext: str = ".mp4") -> str:
    """`<output>/<base>/<base>_<suffix><ext>`; creates the folder.

    ext defaults to the input's extension, then `default_ext`.
    """
    base, in_ext = os.path.splitext(os.path.basename(input_path))
    out_dir = os.path.join(output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_{suffix}{ext or in_ext or default_ext}")
