import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from chroma_key_mcp import chroma

mcp = FastMCP("chroma-key-mcp")


@mcp.tool()
def remove_background(input_path, color="0x00FF00", similarity=0.18, blend=0.05, output_path=None):
    """
    对绿幕/蓝幕视频抠像，将指定颜色变为透明，输出带 alpha 通道的 webm 视频。
    输出文件可以直接作为 compositor-mcp / timeline-project-mcp 的叠加层使用。

    Input: input_path (str) - 绿幕(或其他纯色背景)视频文件路径。

    Optional params:
      color (str, 默认 "0x00FF00"): 要去除的背景颜色(十六进制 RGB，
        0x00FF00=绿幕，0x0000FF=蓝幕)。
      similarity (float, 默认 0.18): 颜色匹配的容差(0-1)，越大去除范围越广，
        但可能误伤主体颜色相近的部分。
      blend (float, 默认 0.05): 边缘羽化程度(0-1)，越大边缘越柔和。
      output_path (str, 默认 None): 输出文件路径(.webm)。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_keyed.webm

    Output: {output_path, color, similarity, blend}
    Usage: remove_background(input_path="D:\\...\\Sources\\greenscreen.mp4")
    """
    return chroma.remove_background(input_path, color=color, similarity=similarity,
                                     blend=blend, output_path=output_path)


@mcp.tool()
def replace_background(foreground_path, background_path, color="0x00FF00", similarity=0.18,
                        blend=0.05, output_path=None):
    """
    对绿幕/蓝幕视频抠像，并将抠出的主体合成到一个新的背景(图片或视频)上，
    一步完成"换背景"。

    Input:
      foreground_path (str) - 绿幕(或其他纯色背景)视频文件路径，决定输出
        分辨率、帧率和时长。
      background_path (str) - 新背景，图片或视频文件路径。如果是视频且比
        前景短则自动循环；图片会自动按前景画面比例裁剪填充。

    Optional params:
      color (str, 默认 "0x00FF00"): 要去除的背景颜色(十六进制 RGB)。
      similarity (float, 默认 0.18): 颜色匹配容差(0-1)。
      blend (float, 默认 0.05): 边缘羽化程度(0-1)。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<前景视频名>\\<前景视频名>_bg_replaced.<ext>

    Output: {output_path, color, similarity, blend}
    Usage:
      replace_background(foreground_path="D:\\...\\Sources\\greenscreen.mp4",
                          background_path="D:\\...\\Sources\\city.mp4")
    """
    return chroma.replace_background(foreground_path, background_path, color=color,
                                      similarity=similarity, blend=blend, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
