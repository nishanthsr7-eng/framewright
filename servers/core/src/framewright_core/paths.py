import os


def servers_dir(start=None):
    """Walk up from `start` (default: this file) to the `servers` folder; None if not found."""
    path = os.path.abspath(start or os.path.dirname(__file__))
    while True:
        parent, name = os.path.split(path)
        if name == "servers":
            return path
        if parent == path:
            return None
        path = parent


def output_root(start=None):
    """`<repo>/output`, or `./output` next to `start` when not inside the repo."""
    tools_dir = servers_dir(start)
    if tools_dir is not None:
        return os.path.join(os.path.dirname(tools_dir), "output")
    return os.path.join(os.path.abspath(start or os.getcwd()), "output")
