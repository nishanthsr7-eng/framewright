import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from speed_ramp_mcp import speed_ramp as sr

mcp = FastMCP("speed-ramp-mcp")


@mcp.tool()
def change_speed(input_path, speed=1.0, smooth=True, output_path=None):
    """
    改变整段视频的播放速度(慢动作/快放)，并相应调整音频音调保持的变速
    (atempo)。慢动作时可选用运动补偿插帧(minterpolate)让画面更顺滑，而不是
    简单的逐帧重复。

    Input: input_path (str) - 源视频文件路径。

    Optional params:
      speed (number, 默认 1.0): 速度倍数。0.5 = 半速慢动作，2.0 = 两倍速。
      smooth (bool, 默认 True): 当 speed < 1.0(慢动作)时，是否使用运动补偿
        插帧让慢动作更流畅(计算量较大)。对 speed >= 1.0 无效。
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_speed.<ext>

    Output: {output_path, speed, smooth, new_duration}
    Usage:
      change_speed(input_path="D:\\...\\Output\\clip.mp4", speed=0.25, smooth=True)
      change_speed(input_path="D:\\...\\Output\\clip.mp4", speed=2.0)
    """
    return sr.change_speed(input_path, speed=speed, smooth=smooth, output_path=output_path)


@mcp.tool()
def speed_ramp(input_path, segments, output_path=None):
    """
    对视频按多个时间区间分别应用不同的速度(速度坡度/speed ramp)，再拼接为
    一段视频。典型用法: 正常速度 -> 慢动作强调瞬间 -> 恢复正常/快速收尾。

    Input:
      input_path (str) - 源视频文件路径。
      segments (List[dict]) - 按时间顺序排列、互不重叠的片段列表，每个为:
        {"start": 数字, "end": 数字, "speed": 数字(默认1.0),
         "smooth": 布尔(默认True，仅在 speed<1 时影响是否插帧)}
        start/end 是相对源视频的秒数。segments 不需要覆盖整段视频——只截取
        并按速度处理你列出的区间，再依次拼接。

    Optional params:
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<视频名>\\<视频名>_ramp.<ext>

    Output: {output_path, segment_count, duration}
    Usage:
      speed_ramp(input_path="D:\\...\\Output\\clip.mp4", segments=[
        {"start": 0, "end": 2, "speed": 1.0},
        {"start": 2, "end": 3, "speed": 0.25},
        {"start": 3, "end": 6, "speed": 1.5}
      ])
    """
    return sr.speed_ramp(input_path, segments, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
