import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from color_match_mcp import color_match

mcp = FastMCP("color-match-mcp")


@mcp.tool()
def get_color_profile(video_path, samples=5):
    """
    采样视频中的若干帧，计算 RGB 三通道的均值(亮度/色调)和标准差(对比度)，
    用于了解一个视频的整体色彩风格，或在 match_color 之前快速比较两个视频。

    Input: video_path (str) - 视频文件路径。
    Optional params: samples (int, 默认 5) - 均匀采样的帧数，越多越准确但越慢。

    Output: {mean_rgb: [R,G,B], std_rgb: [R,G,B], samples}
    Usage: get_color_profile(video_path="D:\\...\\Output\\clip_a.mp4")
    """
    return color_match.get_color_profile(video_path, samples=samples)


@mcp.tool()
def match_color(reference_path, target_path, output_path=None, samples=5, strength=1.0):
    """
    将 target_path 的色彩风格(整体亮度、对比度、色调)匹配到 reference_path，
    使多个不同来源/不同调色的镜头剪辑在一起时看起来风格一致。

    原理: 分别采样两个视频的若干帧，计算 RGB 三通道的均值和标准差，据此为
    target_path 的每个颜色通道计算线性增益(对比度)和偏移(亮度/色偏)，
    通过 ffmpeg lutrgb 滤镜应用。

    Input:
      reference_path (str): 参考视频(色彩风格的目标)。
      target_path (str): 需要被调整色彩的视频。

    Optional params:
      samples (int, 默认 5): 每个视频均匀采样的帧数。
      strength (float, 默认 1.0): 匹配强度 0~1。1.0 = 完全匹配参考视频的
        亮度/对比度统计特征；0.5 = 半程匹配(更自然，避免过度调色)；
        0.0 = 不做改变。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<target 名>\\<target 名>_color_matched.<ext>

    Output: {output_path, gains_rgb, offsets_rgb}
    Usage:
      match_color(reference_path="D:\\...\\Output\\clip_a.mp4",
                   target_path="D:\\...\\Output\\clip_b.mp4", strength=0.8)
    """
    return color_match.match_color(reference_path, target_path, output_path=output_path,
                                    samples=samples, strength=strength)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
