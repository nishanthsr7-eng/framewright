import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from effects_mcp import effects

mcp = FastMCP("effects-mcp")


@mcp.tool()
def list_effects():
    """
    列出 apply_effect 可用的特效名称及说明。

    Output: {特效名: 说明} 字典，包括:
      - "zoom_punch": 短促放大冲击
      - "shake": 快速抖动
      - "rgb_split": RGB 通道分离(色差)
      - "flash": 白色闪光
      - "vignette": 暗角
      - "glow": 柔光/光晕
      - "film_grain": 胶片噪点
      - "light_leak": 暖色调光漏
      - "speed_ramp": 整体变速
      - "grade_warm" / "grade_cool" / "grade_high_contrast" / "grade_faded" /
        "grade_punchy": 调色预设
    """
    return effects.list_effects()


@mcp.tool()
def apply_effect(video_path, effect, intensity=1.0, start_time=0.0, duration=None, output_path=None):
    """
    为视频片段应用一个"剪辑风格"特效(基于 ffmpeg 滤镜)，输出处理后的新视频文件。

    Input:
      video_path (str): 源视频文件路径。
      effect (str): 特效名称，见 list_effects()。

    Optional params:
      intensity (float): 特效强度，约 0.5(轻微)~2.0(强烈)，默认 1.0。
      start_time (float): 特效生效起始时间(秒)，默认 0。
      duration (float): 特效生效持续时间(秒)。不传则到视频结尾。
        注意: "speed_ramp" 和 "grade_*" 调色特效作用于整段视频，忽略此时间区间。
        其余特效仅在 [start_time, start_time+duration] 区间内生效，区间外画面不变。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_<effect>.<ext>

    Output: {output_path, effect, intensity, start_time, end_time}

    Usage:
      apply_effect(video_path="D:\\...\\Sources\\clip.mp4", effect="zoom_punch",
                    intensity=1.2, start_time=2.0, duration=0.4)
      apply_effect(video_path="D:\\...\\Sources\\clip.mp4", effect="grade_punchy")
    """
    return effects.apply_effect(video_path, effect, intensity=intensity,
                                 start_time=start_time, duration=duration, output_path=output_path)


@mcp.tool()
def list_transitions():
    """
    列出 apply_transition 可用的转场名称(基于 ffmpeg xfade 滤镜的内置转场)。

    Output: 转场名称列表，例如 ["fade", "dissolve", "wipeleft", "wiperight",
    "slideup", "circleopen", "pixelize", "hblur", "zoomin", ...]
    """
    return effects.list_transitions()


@mcp.tool()
def apply_transition(video_a, video_b, transition="fade", duration=0.5, output_path=None):
    """
    在两个视频片段之间应用转场效果(基于 ffmpeg xfade)，输出 A 片段 -> 转场 -> B 片段
    拼接后的视频。

    Input:
      video_a (str): 第一个视频文件路径。
      video_b (str): 第二个视频文件路径(将被缩放到与 A 相同的分辨率/帧率)。

    Optional params:
      transition (str): 转场名称，见 list_transitions()，默认 "fade"。
      duration (float): 转场持续时间(秒)，默认 0.5。
      output_path (str): 输出文件路径。不传则默认为
        D:\\...\\Output\\<A视频名>\\<A视频名>_<transition>_transition.mp4

    Output: {output_path, transition, duration}

    Usage:
      apply_transition(video_a="D:\\...\\clip1.mp4", video_b="D:\\...\\clip2.mp4",
                        transition="dissolve", duration=0.5)
    """
    return effects.apply_transition(video_a, video_b, transition=transition,
                                     duration=duration, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
