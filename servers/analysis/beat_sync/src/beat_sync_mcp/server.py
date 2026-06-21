import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from beat_sync_mcp import beat_sync

mcp = FastMCP("beat-sync-mcp")


@mcp.tool()
def detect_beats(music_path):
    """
    分析音乐文件，检测整体节拍速度(BPM)和每个节拍点的时间戳。可用于在调用
    generate_beat_synced_video 前预览节拍分布，或手动设计卡点剪辑方案。

    Input: music_path (str) - 音乐/音频文件路径。
    Output: {tempo (BPM), beat_times: [秒, ...], duration}
    Usage: detect_beats(music_path="D:\\...\\Sources\\music.mp3")
    """
    return beat_sync.detect_beats(music_path)


@mcp.tool()
def generate_beat_synced_video(clip_paths, music_path, output_path=None, beats_per_cut=1, max_duration=None):
    """
    自动生成"卡点视频": 检测音乐的节拍，按节拍位置切分时间轴，依次从给定的
    视频片段列表中循环截取对应长度的画面拼接起来，最终用音乐替换原始音频，
    使画面切换精确卡在节拍上。

    Input:
      clip_paths (List[str]) - 用作画面素材的视频文件路径列表(按顺序循环
        使用；建议至少 2-3 个不同片段，避免画面重复感)。
      music_path (str) - 背景音乐文件路径，将检测其节拍并作为最终输出的
        音轨。

    Optional params:
      beats_per_cut (int, 默认 1): 每隔多少个节拍切一次画面。1 = 每个节拍都
        切换(快节奏)，2-4 = 每 2-4 个节拍切换一次(更舒缓)。
      max_duration (number, 默认 None): 限制输出视频总时长(秒)。不传则使用
        整段音乐的时长。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<音乐名>\\<音乐名>_beat_synced.mp4

    Output: {output_path, tempo, cut_count, total_duration}
    Usage:
      generate_beat_synced_video(
        clip_paths=["D:\\...\\Sources\\clip1.mp4", "D:\\...\\Sources\\clip2.mp4"],
        music_path="D:\\...\\Sources\\music.mp3", beats_per_cut=2, max_duration=30)
    """
    return beat_sync.generate_beat_synced_video(clip_paths, music_path, output_path=output_path,
                                                  beats_per_cut=beats_per_cut, max_duration=max_duration)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
