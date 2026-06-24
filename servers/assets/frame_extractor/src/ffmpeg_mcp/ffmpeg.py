import subprocess
import shlex
import sys
import threading
import os
import platform
import shutil
import ffmpeg_mcp.utils as utils
import ffmpeg_mcp.typedef as typedef
def check_os_architecture():
    # 获取当前操作系统
    system = platform.system()
    # 获取处理器架构
    machine = platform.machine()
    return system, machine
        
def run_command(command, timeout=300):
    """
    运行FFmpeg命令并捕获相关信息。

    参数:
        command (str): 要执行的FFmpeg命令行字符串。
        timeout (int): 命令执行的超时时间（以秒为单位），默认300秒。

    返回:
        tuple: 包含以下元素的元组：
            - return_code (int): 命令执行后的返回状态码。
            - output_log (str): 命令执行过程中的标准输出日志。
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
            # 处理文件关闭时的异常
            pass
    try:
        # 使用subprocess.run执行FFmpeg命令
        # Commands are built using shlex.quote() which always emits POSIX-style
        # quoting, so they must be split with posix=True on every platform
        # (including Windows) to strip those quotes back off correctly.
        args = shlex.split(command, posix=True)
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        thread = threading.Thread(target=read_output, args=(proc,))
        thread.start()
        return_code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print("command timed out", file=sys.stderr)
        return_code = -1
        append_msg = "Timeout expired"
    except Exception as e:
        return_code = -1
        append_msg = f"An error occurred: {e}"
        # 捕获所有其他异常
    finally:
        # 确保清理资源
        if proc is not None and proc.poll() is None:  # 如果进程仍在运行
            proc.kill()
        if thread is not None:
            thread.join()  #
        logs.append(append_msg)
        return return_code, '\n'.join(logs), append_msg
    
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
    code, log, append_msg = run_command(cmd,timeout)
    logs.append(log)
    logs.append(append_msg)
    return code, '\n'.join(logs)

def run_ffprobe(cmd, timeout = 60):
    binary = resolve_binary("ffprobe")
    if binary is None:
        return -1, "ffmpeg/ffprobe/ffplay not found on PATH"
    cmd = f"{shlex.quote(binary)} {cmd}"
    code, log, append_msg = run_command(cmd,timeout)
    logs = []
    if (code != 0):
        logs.append(cmd)
        logs.append(log)
        logs.append(append_msg)
        return code,cmd,'\n'.join(logs)
    return code, cmd, log

def run_ffplay(cmd, timeout = 60):
    binary = resolve_binary("ffplay")
    if binary is None:
        return -1, "ffmpeg/ffprobe/ffplay not found on PATH"
    cmd = f"{shlex.quote(binary)} {cmd}"
    code, log, append_msg = run_command(cmd,timeout)
    logs = []
    if (code != 0):
        logs.append(cmd)
        logs.append(log)
        logs.append(append_msg)
        return code,cmd,'\n'.join(logs)
    return code, cmd, log
    
def media_format_ctx(path):
    cmd = f" -show_streams -of json -v error -i {shlex.quote(path)}"
    code, cmd, log = run_ffprobe(cmd)
    if (code == 0):
        return typedef.FormatContext(log)
    return None