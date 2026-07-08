import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from stabilization_mcp import stabilize

mcp = FastMCP("stabilization-mcp")


@mcp.tool()
def stabilize_video(input_path, smoothing=10, shakiness=5, zoom=0, output_path=None):
    """
    使用 ffmpeg 的 vidstab 两遍稳像算法消除手持拍摄的抖动/晃动，输出更平稳的
    视频，并叠加轻微锐化以补偿稳像导致的轻微模糊。

    Input: input_path (str) - 源视频文件路径。

    Optional params:
      smoothing (int, 默认 10): 平滑窗口大小(前后参考的帧数)，越大画面越
        平稳但响应越"飘"，越小则保留更多原始运动。
      shakiness (int, 1-10, 默认 5): 输入视频抖动程度估计，越大表示画面越
        抖，分析时会查找更大范围的运动。
      zoom (number, 默认 0): 额外放大百分比(0-100)，用于裁掉稳像后画面边缘
        出现的黑边/抖动残留。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_stabilized.<ext>

    Output: {output_path, smoothing, shakiness, zoom}
    Usage: stabilize_video(input_path="D:\\...\\Sources\\handheld.mp4", smoothing=15, zoom=5)
    """
    return stabilize.stabilize_video(input_path, smoothing=smoothing, shakiness=shakiness,
                                      zoom=zoom, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
