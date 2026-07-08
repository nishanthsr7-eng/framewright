import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from audio_mastering_mcp import mastering

mcp = FastMCP("audio-mastering-mcp")


@mcp.tool()
def normalize_loudness(input_path, target_lufs=-14.0, output_path=None):
    """
    对音频或视频文件的音轨进行响度归一化(EBU R128 loudnorm)，把整体音量
    调整到目标 LUFS，避免忽大忽小或过轻/过响。

    Input: input_path (str) - 音频或视频文件路径。

    Optional params:
      target_lufs (float): 目标响度，默认 -14(适合 YouTube/大多数流媒体平台)。
        常见参考值: -14 (YouTube/Spotify), -16 (播客), -23 (广播标准)。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<文件名>\\<文件名>_normalized.<ext>

    Output: {output_path, target_lufs}
    Usage: normalize_loudness(input_path="D:\\...\\Sources\\clip.mp4", target_lufs=-14)
    """
    return mastering.normalize_loudness(input_path, target_lufs=target_lufs, output_path=output_path)


@mcp.tool()
def reduce_noise(input_path, amount=12, output_path=None):
    """
    对音频或视频文件的音轨进行降噪(ffmpeg afftdn)，去除背景嘶嘶声/嗡嗡声等
    平稳噪声。

    Input: input_path (str) - 音频或视频文件路径。

    Optional params:
      amount (float): 降噪强度(dB)，范围约 0.01~97，默认 12。值越大降噪越强，
        但过大可能损失人声细节/产生水声感伪音。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<文件名>\\<文件名>_denoised.<ext>

    Output: {output_path, amount}
    Usage: reduce_noise(input_path="D:\\...\\Sources\\clip.mp4", amount=15)
    """
    return mastering.reduce_noise(input_path, amount=amount, output_path=output_path)


@mcp.tool()
def add_background_music(video_path, music_path, music_volume_db=-20.0, duck=True,
                          duck_threshold_db=-30.0, duck_ratio=8.0, loop=True, output_path=None):
    """
    为视频添加背景音乐，与视频原有音轨混合。可选自动"闪避"(ducking)：
    当视频原音轨(如人声/对白)响起时自动压低背景音乐音量，安静时恢复。

    Input:
      video_path (str): 源视频文件路径。
      music_path (str): 背景音乐音频文件路径。

    Optional params:
      music_volume_db (float): 背景音乐整体音量调整(dB)，默认 -20(显著降低，
        作为背景音乐)。
      duck (bool): 是否启用自动闪避，默认 True。视频没有音轨时此参数无效。
      duck_threshold_db (float): 闪避触发阈值(dB)，默认 -30。原音轨音量超过
        该阈值时开始压低音乐。
      duck_ratio (float): 闪避压缩比，默认 8(即超过阈值部分按 8:1 压缩)。
      loop (bool): 若背景音乐比视频短，是否循环播放铺满整段视频，默认 True。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_with_music.<ext>

    Output: {output_path, music_volume_db, duck}
    Usage:
      add_background_music(video_path="D:\\...\\Output\\clip.mp4",
                            music_path="D:\\...\\Sources\\song.mp3",
                            music_volume_db=-18, duck=True)
    """
    return mastering.add_background_music(
        video_path=video_path, music_path=music_path,
        music_volume_db=music_volume_db, duck=duck,
        duck_threshold_db=duck_threshold_db, duck_ratio=duck_ratio,
        loop=loop, output_path=output_path,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
