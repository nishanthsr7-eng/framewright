import json
import os
import subprocess


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


def _probe(path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    has_video = any(s["codec_type"] == "video" for s in data["streams"])
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    duration = float(data["format"].get("duration") or 0.0)
    return {"has_video": has_video, "has_audio": has_audio, "duration": duration}


def _run_ffmpeg(args, timeout=900):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")
    return result.stderr


def _default_output_path(input_path, suffix, ext=None):
    base, in_ext = os.path.splitext(os.path.basename(input_path))
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    use_ext = ext if ext else (in_ext if in_ext else ".wav")
    return os.path.join(out_dir, f"{base}_{suffix}{use_ext}")


def _make_output_path(output_path, input_path, suffix):
    if output_path is None:
        return _default_output_path(input_path, suffix)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    return output_path


def normalize_loudness(input_path, target_lufs=-14.0, output_path=None):
    """
    对音频/视频的音轨进行响度归一化(EBU R128 loudnorm)，使整体音量
    达到目标 LUFS(常见目标: -14 适合 YouTube/流媒体, -16 适合播客, -23 适合广播)。
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    info = _probe(input_path)
    if not info["has_audio"]:
        raise RuntimeError(f"文件没有音轨: {input_path}")

    out = _make_output_path(output_path, input_path, "normalized")
    af = f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"

    args = ["-i", input_path, "-af", af]
    if info["has_video"]:
        args += ["-c:v", "copy"]
    args += [out]

    _run_ffmpeg(args)
    return {"output_path": out, "target_lufs": target_lufs}


def reduce_noise(input_path, amount=12, output_path=None):
    """
    使用 ffmpeg afftdn 对音频/视频的音轨进行降噪。

    amount: 降噪强度(dB)，范围约 0.01~97，默认 12，越大降噪越强但可能损失细节。
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    info = _probe(input_path)
    if not info["has_audio"]:
        raise RuntimeError(f"文件没有音轨: {input_path}")

    out = _make_output_path(output_path, input_path, "denoised")
    af = f"afftdn=nr={amount}"

    args = ["-i", input_path, "-af", af]
    if info["has_video"]:
        args += ["-c:v", "copy"]
    args += [out]

    _run_ffmpeg(args)
    return {"output_path": out, "amount": amount}


def add_background_music(video_path, music_path, music_volume_db=-20.0, duck=True,
                          duck_threshold_db=-30.0, duck_ratio=8.0, loop=True, output_path=None):
    """
    为视频添加背景音乐，与原始音轨混合。

    music_volume_db: 背景音乐的音量调整(dB)，默认 -20(明显降低，作为背景)。
    duck: 是否在原始音轨有声音时自动压低背景音乐音量(side-chain ducking)，
      默认 True，适合有对白/人声的视频。
    duck_threshold_db / duck_ratio: ducking 灵敏度/压缩比，默认 -30dB / 8:1。
    loop: 若背景音乐比视频短，是否循环播放以覆盖整段视频，默认 True。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"找不到文件: {video_path}")
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"找不到文件: {music_path}")

    video_info = _probe(video_path)
    if not video_info["has_video"]:
        raise RuntimeError(f"不是视频文件: {video_path}")

    out = _make_output_path(output_path, video_path, "with_music")

    input_args = ["-i", video_path]
    if loop:
        input_args += ["-stream_loop", "-1"]
    input_args += ["-i", music_path]

    music_dur = video_info["duration"]
    threshold = 10 ** (duck_threshold_db / 20.0)

    if video_info["has_audio"]:
        music_chain = f"[1:a]volume={music_volume_db}dB,atrim=duration={music_dur}[music]"
        if duck:
            duck_chain = (
                f"[music][0:a]sidechaincompress=threshold={threshold}:ratio={duck_ratio}:"
                f"attack=20:release=300[ducked]"
            )
            mix_chain = "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            filter_complex = ";".join([music_chain, duck_chain, mix_chain])
        else:
            mix_chain = "[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            filter_complex = ";".join([music_chain, mix_chain])
        audio_label = "aout"
    else:
        filter_complex = f"[1:a]volume={music_volume_db}dB,atrim=duration={music_dur}[aout]"
        audio_label = "aout"

    args = input_args + [
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", f"[{audio_label}]",
        "-c:v", "copy",
        out,
    ]

    _run_ffmpeg(args)
    return {"output_path": out, "music_volume_db": music_volume_db, "duck": duck}
