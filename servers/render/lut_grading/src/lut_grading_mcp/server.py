import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from lut_grading_mcp import grading

mcp = FastMCP("lut-grading-mcp")


@mcp.tool()
def list_luts():
    """
    列出所有内置的电影级 3D LUT 色彩分级预设及其说明。

    Output: {lut_name: {description, path}, ...}
    Usage: list_luts()
    """
    return grading.list_luts()


@mcp.tool()
def apply_lut(input_path, lut, intensity=1.0, output_path=None):
    """
    将一个 3D LUT 色彩分级预设应用到视频上，模拟电影调色效果(类似 Premiere/
    DaVinci Resolve 的 LUT 应用)。

    Input:
      input_path (str) - 源视频文件路径。
      lut (str) - 内置 LUT 名称(见 list_luts()，例如 "cinematic_teal_orange"、
        "warm_vintage"、"cool_blue"、"high_contrast_bw"、"faded_film"、
        "moody_green"、"bleach_bypass")，或一个自定义 .cube 文件的路径。

    Optional params:
      intensity (float, 默认 1.0): LUT 效果强度(0-1)，0 表示不变，1 表示完全
        应用 LUT，中间值与原始画面混合。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_graded.<ext>

    Output: {output_path, lut, intensity}
    Usage:
      apply_lut(input_path="D:\\...\\Output\\clip.mp4", lut="cinematic_teal_orange")
      apply_lut(input_path="D:\\...\\Output\\clip.mp4", lut="D:\\...\\my_lut.cube", intensity=0.6)
    """
    return grading.apply_lut(input_path, lut, intensity=intensity, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
