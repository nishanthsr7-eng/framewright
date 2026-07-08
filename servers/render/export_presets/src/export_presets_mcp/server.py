import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from export_presets_mcp import exporter

mcp = FastMCP("export-presets-mcp")


@mcp.tool()
def list_platform_presets():
    """
    列出可用于 export_for_platform 的平台预设及其规格(分辨率、宽高比、
    码率、最大帧率)。

    Output: dict {platform_name: {width, height, aspect, video_bitrate,
    audio_bitrate, fps_max, description}}
    Usage: list_platform_presets()
    """
    return exporter.list_platform_presets()


@mcp.tool()
def export_for_platform(video_path, platform, output_path=None, fit_mode="crop"):
    """
    按指定社交平台的推荐分辨率/码率/帧率重新编码导出视频，自动处理宽高比
    转换(裁切或加黑边)。

    Input:
      video_path (str): 源视频文件路径。
      platform (str): 目标平台，见 list_platform_presets()，例如
        "youtube"(横屏1080p), "youtube_shorts"|"tiktok"|"instagram_reels"
        (竖屏9:16), "instagram_post"(正方形), "instagram_story"(竖屏),
        "twitter"|"facebook"(横屏720p)。

    Optional params:
      fit_mode (str): 宽高比不匹配时的处理方式。
        - "crop" (默认): 缩放至覆盖目标尺寸后居中裁切，画面填满，可能裁掉
          边缘内容。适合素材比例和目标比例接近时。
        - "pad": 缩放至完整显示后用黑边填充，保留完整画面但可能有黑边。
          适合需要保留全部画面内容(如包含重要字幕/构图)时。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_<platform>.<ext>

    Output: {output_path, platform, width, height, fit_mode}
    Usage:
      export_for_platform(video_path="D:\\...\\Output\\edit.mp4", platform="tiktok")
      export_for_platform(video_path="D:\\...\\Output\\edit.mp4", platform="youtube",
                           fit_mode="pad")
    """
    return exporter.export_for_platform(video_path, platform, output_path=output_path, fit_mode=fit_mode)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
