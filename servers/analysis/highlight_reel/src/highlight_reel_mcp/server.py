import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from highlight_reel_mcp import highlights

mcp = FastMCP("highlight-reel-mcp")


@mcp.tool()
def generate_highlights(video_path, target_duration=30.0, clip_duration=3.0,
                         min_gap=2.0, output_path=None):
    """
    自动分析视频的音频(响度 RMS + 冲击/瞬态强度)，挑选出最"精彩"的若干片段，
    按原始时间顺序拼接为一个集锦/预告片视频。适合从长视频(如直播录像、
    完整剪辑)中快速生成短预告或高光合集。

    Input: video_path (str) - 源视频文件路径(需包含音轨)。

    Optional params:
      target_duration (float, 默认 30.0): 集锦总时长目标(秒)。实际输出时长
        = 选中片段数 * clip_duration，可能略多于或少于目标值(因为片段是离散的)。
      clip_duration (float, 默认 3.0): 每个候选片段的长度(秒)。
      min_gap (float, 默认 2.0): 两个候选片段中心点之间的最小间隔(秒)，避免
        选出的片段彼此重叠或过于集中。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_highlights.<ext>

    Output: {output_path, segments: [{start, end, score}, ...], total_duration}
    Usage:
      generate_highlights(video_path="D:\\...\\Sources\\stream.mp4",
                           target_duration=60, clip_duration=4)
    """
    return highlights.generate_highlights(
        video_path, target_duration=target_duration, clip_duration=clip_duration,
        min_gap=min_gap, output_path=output_path,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
