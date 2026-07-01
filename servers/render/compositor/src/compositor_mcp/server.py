import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from compositor_mcp import compositor

mcp = FastMCP("compositor-mcp")


@mcp.tool()
def compose_layers(base_video, layers, output_path=None):
    """
    将多个图层(角色抠图/文字叠加层/画中画视频等，可含 alpha 透明通道)按位置、
    时间区间和层级顺序叠加合成到一个底层视频上，输出一个合成后的视频文件。

    常见用途:
      - 把 character-extractor-mcp 输出的角色抠图 PNG 序列(或转成的透明视频)
        放在新背景上的指定位置和时间段。
      - 把 text-overlay-mcp / add_karaoke_captions 输出的 overlay.webm
        (透明字幕/标题层) 叠加到剪辑好的视频上。
      - 实现画中画: 把另一个视频缩小后叠加到角落，并可选择混入它自己的音频。
      - 同时叠加多层(例如: 背景视频 + 角色抠图 + 标题文字 + 字幕)，层在
        layers 列表中的顺序即为从下到上的堆叠顺序(后面的层盖在前面的层之上)。

    Input:
      base_video (str): 底层(背景)视频文件路径，决定输出的分辨率、帧率、总时长。
      layers (List[dict]): 按从下到上顺序排列的图层列表，每个图层为:
        - file (str, 必填): 图层文件路径。
          * 图片(.png/.jpg/.webp 等): 会在其可见区间内静态显示(若有透明通道
            则透明部分不遮挡背景)，适合角色抠图、贴纸、Logo。
          * 视频/webm(含透明通道的 .webm 最适合文字/字幕叠加层): 会播放其
            内容(从该层自身的开头算起)，超出 base_video 总时长的部分会被截断。
        - x, y (str|int, 默认 0): 叠加位置，支持像素值或 ffmpeg overlay
          表达式，可用变量 W/H(底层宽高)和 w/h(本层宽高)，例如:
          "(W-w)/2" = 水平居中, "(H-h)/2" = 垂直居中, "W-w-20" = 右对齐
          (留20px边距), "20" = 距左边20px。
        - width, height (int, 可选): 将本层缩放到指定像素尺寸；只给一个时另一个
          传 -1 表示按原比例缩放(由调用方决定哪一个是 -1)。不传则保持原始尺寸。
        - opacity (float, 默认 1.0): 不透明度，0~1，例如 0.7 = 70% 不透明。
        - start_time, end_time (float, 可选): 本层在 base_video 时间轴上的
          可见区间(秒)。默认整段时间都可见。区间外该层完全不显示。
        - audio (bool, 默认 False): 仅对视频层有效。为 True 时会将该层自身的
          音轨(从 start_time 开始播放)与 base_video 的音轨混合到输出中。
      output_path (str, 可选): 输出文件路径。不传则默认为
        D:\\...\\Output\\<base_video 名>\\<base_video 名>_composite.<ext>

    Output: {output_path, layer_count, duration}

    Usage:
      # 背景视频 + 角色抠图(0-3秒出现在右下角) + 标题文字层(全程)
      compose_layers(
        base_video="D:\\...\\Output\\bg.mp4",
        layers=[
          {"file": "D:\\...\\Output\\char.png", "x": "W-w-40", "y": "H-h-40",
           "width": 400, "height": -1, "start_time": 0, "end_time": 3},
          {"file": "D:\\...\\Output\\clip_text_overlay\\overlay.webm",
           "x": "(W-w)/2", "y": "(H-h)/2"}
        ]
      )
    """
    return compositor.compose_layers(base_video=base_video, layers=layers, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
