import os
from functools import partial

from framewright_core import default_output_path, probe_video, run_ffmpeg

_run_ffmpeg = partial(run_ffmpeg, timeout=900)


def _make_output_path(output_path, input_path, suffix):
    if output_path is None:
        return default_output_path(input_path, suffix, default_ext=".wav")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    return output_path


def normalize_loudness(input_path: str, target_lufs: float = -14.0, output_path: str | None = None) -> dict:
    """
    对音频/视频的音轨进行响度归一化(EBU R128 loudnorm)，使整体音量
    达到目标 LUFS(常见目标: -14 适合 YouTube/流媒体, -16 适合播客, -23 适合广播)。
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    info = probe_video(input_path, require_video=False)
    if not info.has_audio:
        raise RuntimeError(f"File has no audio track: {input_path}")

    out = _make_output_path(output_path, input_path, "normalized")
    af = f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"

    args = ["-i", input_path, "-af", af]
    if info.has_video:
        args += ["-c:v", "copy"]
    args += [out]

    _run_ffmpeg(args)
    return {"output_path": out, "target_lufs": target_lufs}


def reduce_noise(input_path: str, amount: int = 12, output_path: str | None = None) -> dict:
    """
    使用 ffmpeg afftdn 对音频/视频的音轨进行降噪。

    amount: 降噪强度(dB)，范围约 0.01~97，默认 12，越大降噪越强但可能损失细节。
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    info = probe_video(input_path, require_video=False)
    if not info.has_audio:
        raise RuntimeError(f"File has no audio track: {input_path}")

    out = _make_output_path(output_path, input_path, "denoised")
    af = f"afftdn=nr={amount}"

    args = ["-i", input_path, "-af", af]
    if info.has_video:
        args += ["-c:v", "copy"]
    args += [out]

    _run_ffmpeg(args)
    return {"output_path": out, "amount": amount}


def add_background_music(
    video_path: str,
    music_path: str,
    music_volume_db: float = -20.0,
    duck: bool = True,
    duck_threshold_db: float = -30.0,
    duck_ratio: float = 8.0,
    loop: bool = True,
    output_path: str | None = None,
) -> dict:
    """
    为视频添加背景音乐，与原始音轨混合。

    music_volume_db: 背景音乐的音量调整(dB)，默认 -20(明显降低，作为背景)。
    duck: 是否在原始音轨有声音时自动压低背景音乐音量(side-chain ducking)，
      默认 True，适合有对白/人声的视频。
    duck_threshold_db / duck_ratio: ducking 灵敏度/压缩比，默认 -30dB / 8:1。
    loop: 若背景音乐比视频短，是否循环播放以覆盖整段视频，默认 True。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")
    if not os.path.exists(music_path):
        raise FileNotFoundError(f"File not found: {music_path}")

    video_info = probe_video(video_path, require_video=False)
    if not video_info.has_video:
        raise RuntimeError(f"Not a video file: {video_path}")

    out = _make_output_path(output_path, video_path, "with_music")

    input_args = ["-i", video_path]
    if loop:
        input_args += ["-stream_loop", "-1"]
    input_args += ["-i", music_path]

    music_dur = video_info.duration
    threshold = 10 ** (duck_threshold_db / 20.0)

    if video_info.has_audio:
        music_chain = f"[1:a]volume={music_volume_db}dB,atrim=duration={music_dur}[music]"
        if duck:
            duck_chain = (
                f"[music][0:a]sidechaincompress=threshold={threshold}:ratio={duck_ratio}:attack=20:release=300[ducked]"
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
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        f"[{audio_label}]",
        "-c:v",
        "copy",
        out,
    ]

    _run_ffmpeg(args)
    return {"output_path": out, "music_volume_db": music_volume_db, "duck": duck}
