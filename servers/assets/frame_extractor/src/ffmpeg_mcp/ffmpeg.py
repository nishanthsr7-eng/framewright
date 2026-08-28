import logging
import os
import platform
import shlex
import shutil
import subprocess
import threading

import ffmpeg_mcp.typedef as typedef

logger = logging.getLogger(__name__)


def check_os_architecture():
    system = platform.system()
    machine = platform.machine()
    return system, machine


def run_command(command, timeout=300):
    """Run a command line, capturing stdout+stderr, and kill it on timeout.

    Returns (return_code, output_log, append_msg); return_code is -1 on timeout or launch error.
    """
    logs = []
    proc = None
    thread = None
    return_code = 0
    append_msg = ""

    def read_output(proc):
        try:
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    logs.append(line)
        except ValueError:
            # The pipe was closed under us.
            pass

    try:
        # Commands are built using shlex.quote() which always emits POSIX-style
        # quoting, so they must be split with posix=True on every platform
        # (including Windows) to strip those quotes back off correctly.
        args = shlex.split(command, posix=True)
        proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
        thread = threading.Thread(target=read_output, args=(proc,))
        thread.start()
        return_code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning("command timed out after %ss", timeout)
        return_code = -1
        append_msg = "Timeout expired"
    except Exception as e:
        return_code = -1
        append_msg = f"An error occurred: {e}"
    finally:
        # Kill the process if it is still running, then join the reader thread.
        if proc is not None and proc.poll() is None:
            proc.kill()
        if thread is not None:
            thread.join()
        logs.append(append_msg)
    return return_code, "\n".join(logs), append_msg


def is_file_and_exists(file_path):
    return os.path.isfile(file_path) and os.path.exists(file_path)


def resolve_binary(name):
    """Return the full path to an ffmpeg-family binary found on PATH."""
    return shutil.which(name)


def run_ffmpeg(cmd, timeout=300):
    binary = resolve_binary("ffmpeg")
    if binary is None:
        return -1, "ffmpeg/ffprobe/ffplay not found on PATH"
    cmd = f"{shlex.quote(binary)} {cmd}"
    logs = []
    logs.append(cmd)
    code, log, append_msg = run_command(cmd, timeout)
    logs.append(log)
    logs.append(append_msg)
    return code, "\n".join(logs)


def run_ffprobe(cmd, timeout=60):
    binary = resolve_binary("ffprobe")
    if binary is None:
        return -1, "ffmpeg/ffprobe/ffplay not found on PATH"
    cmd = f"{shlex.quote(binary)} {cmd}"
    code, log, append_msg = run_command(cmd, timeout)
    logs = []
    if code != 0:
        logs.append(cmd)
        logs.append(log)
        logs.append(append_msg)
        return code, cmd, "\n".join(logs)
    return code, cmd, log


def run_ffplay(cmd, timeout=60):
    binary = resolve_binary("ffplay")
    if binary is None:
        return -1, "ffmpeg/ffprobe/ffplay not found on PATH"
    cmd = f"{shlex.quote(binary)} {cmd}"
    code, log, append_msg = run_command(cmd, timeout)
    logs = []
    if code != 0:
        logs.append(cmd)
        logs.append(log)
        logs.append(append_msg)
        return code, cmd, "\n".join(logs)
    return code, cmd, log


def media_format_ctx(path):
    cmd = f" -show_streams -of json -v error -i {shlex.quote(path)}"
    code, cmd, log = run_ffprobe(cmd)
    if code == 0:
        return typedef.FormatContext(log)
    return None
