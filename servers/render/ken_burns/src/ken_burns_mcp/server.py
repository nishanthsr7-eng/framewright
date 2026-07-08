import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from ken_burns_mcp import ken_burns

mcp = FastMCP("ken-burns-mcp")


@mcp.tool()
def create_ken_burns(image_path, duration=5.0, zoom_start=1.0, zoom_end=1.3, pan="center",
                      width=1920, height=1080, fps=30, output_path=None):
    """
    将一张静态图片转换为带有缓慢缩放(zoom)和平移(pan)效果的视频片段
    (Ken Burns 效果)，常用于幻灯片、纪录片风格的照片展示。

    Input: image_path (str) - 源图片文件路径。

    Optional params:
      duration (number, 默认 5.0): 输出视频时长(秒)。
      zoom_start/zoom_end (number, 默认 1.0/1.3): 起始/结束缩放倍数。
        zoom_end > zoom_start 表示缓慢放大；zoom_end < zoom_start 表示缓慢
        缩小。
      pan (str, 默认 "center"): 平移方向，可选:
        "center" (居中缩放，无平移)、"left_to_right"、"right_to_left"、
        "top_to_bottom"、"bottom_to_top"。
      width/height (int, 默认 1920x1080): 输出视频分辨率。
      fps (int, 默认 30): 输出帧率。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<图片名>\\<图片名>_ken_burns.mp4

    Output: {output_path, duration, zoom_start, zoom_end, pan, width, height, fps}
    Usage:
      create_ken_burns(image_path="D:\\...\\Sources\\photo.jpg", duration=6,
                        zoom_start=1.0, zoom_end=1.25, pan="left_to_right")
    """
    return ken_burns.create_ken_burns(image_path, duration=duration, zoom_start=zoom_start,
                                       zoom_end=zoom_end, pan=pan, width=width, height=height,
                                       fps=fps, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
