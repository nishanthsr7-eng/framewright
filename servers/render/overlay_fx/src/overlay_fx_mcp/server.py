import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from overlay_fx_mcp import effects

mcp = FastMCP("overlay-fx-mcp")


@mcp.tool()
def add_film_grain(input_path, intensity=20, output_path=None):
    """
    为视频叠加胶片颗粒/噪点效果(film grain)，营造复古胶片质感。

    Input: input_path (str) - 源视频文件路径。
    Optional params:
      intensity (int, 0-100, 默认 20): 噪点强度。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_grain.<ext>
    Output: {output_path, intensity}
    Usage: add_film_grain(input_path="D:\\...\\Output\\clip.mp4", intensity=15)
    """
    return effects.add_film_grain(input_path, intensity=intensity, output_path=output_path)


@mcp.tool()
def add_vignette(input_path, intensity=0.5, output_path=None):
    """
    为视频添加暗角效果(vignette)，画面边缘逐渐变暗，引导视线聚焦中心。

    Input: input_path (str) - 源视频文件路径。
    Optional params:
      intensity (float, 0-1, 默认 0.5): 暗角强度，越大边缘越暗、范围越大。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_vignette.<ext>
    Output: {output_path, intensity}
    Usage: add_vignette(input_path="D:\\...\\Output\\clip.mp4", intensity=0.6)
    """
    return effects.add_vignette(input_path, intensity=intensity, output_path=output_path)


@mcp.tool()
def add_chromatic_aberration(input_path, shift=3, output_path=None):
    """
    为视频添加色差(chromatic aberration)效果: 红色和蓝色通道在水平方向上
    错位，营造故障感/赛博朋克/复古CRT质感。

    Input: input_path (str) - 源视频文件路径。
    Optional params:
      shift (int, 默认 3): 红/蓝通道的水平错位像素数(蓝色通道反向偏移)。
        数值越大效果越强烈。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_chroma_ab.<ext>
    Output: {output_path, shift}
    Usage: add_chromatic_aberration(input_path="D:\\...\\Output\\clip.mp4", shift=5)
    """
    return effects.add_chromatic_aberration(input_path, shift=shift, output_path=output_path)


@mcp.tool()
def add_light_leak(input_path, style="warm", intensity=0.5, pan="left_to_right", output_path=None):
    """
    为视频叠加光晕/漏光(light leak)效果，模拟胶片相机漏光或镜头光斑划过画面，
    常用于转场或氛围渲染。光斑会随时间在画面上平移。

    Input: input_path (str) - 源视频文件路径。
    Optional params:
      style (str, 默认 "warm"): 光晕颜色风格，可选 "warm"(暖橙色)、
        "golden"(金色)、"cool"(冷蓝色)、"white"(白色镜头光斑)。
      intensity (float, 0-1, 默认 0.5): 叠加强度(使用 screen 混合模式)。
      pan (str, 默认 "left_to_right"): 光斑移动方向，可选
        "left_to_right"、"right_to_left"、"static"(静止不动)。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_light_leak.<ext>
    Output: {output_path, style, intensity, pan}
    Usage: add_light_leak(input_path="D:\\...\\Output\\clip.mp4", style="golden", intensity=0.4)
    """
    return effects.add_light_leak(input_path, style=style, intensity=intensity,
                                   pan=pan, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
