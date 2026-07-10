import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from timeline_project_mcp import project as proj

mcp = FastMCP("timeline-project-mcp")


@mcp.tool()
def create_project(project_path, width=1920, height=1080, fps=30):
    """
    创建一个新的剪辑项目文件(JSON 格式)，初始为空的主时间轴和空的叠加层列表。
    后续调用 add_clip / add_overlay 向该文件追加内容，最后调用 render_project
    一次性渲染为最终视频。

    Input: project_path (str) - 项目 JSON 文件的保存路径，例如
      "D:\\...\\Output\\my_project.json"。

    Optional params:
      width/height (int, 默认 1920x1080): 最终输出视频的画布尺寸。
      fps (number, 默认 30): 最终输出视频的帧率。

    Output: 新创建的项目内容 {width, height, fps, clips: [], overlays: []}
    Usage:
      create_project(project_path="D:\\...\\Output\\my_project.json", width=1080, height=1920)
    """
    return proj.create_project(project_path, width=width, height=height, fps=fps)


@mcp.tool()
def add_clip(project_path, file, start=0.0, end=None, transition_in=None, transition_in_duration=0.5):
    """
    向项目主时间轴末尾追加一个片段(视频或图片)，按添加顺序依次播放。

    Input:
      project_path (str) - 项目 JSON 文件路径(须已用 create_project 创建)。
      file (str) - 片段的视频或图片文件路径。

    Optional params:
      start (number, 默认 0.0): 从源文件的第几秒开始截取。
      end (number, 默认 None): 截取到源文件的第几秒结束。不传则视频默认使用
        整个文件时长，图片默认使用 5 秒。
      transition_in (str, 默认 None): 与上一个片段之间使用的转场效果名称
        (例如 "fade"、"dissolve"、"wipeleft"、"slideup" 等，参考 effects-mcp
        的 list_transitions())。对项目中的第一个片段无效。
      transition_in_duration (number, 默认 0.5): 转场持续时间(秒)。

    Output: {index, clip, clip_count}
    Usage:
      add_clip(project_path="D:\\...\\my_project.json", file="D:\\...\\clip1.mp4")
      add_clip(project_path="D:\\...\\my_project.json", file="D:\\...\\clip2.mp4",
               transition_in="fade", transition_in_duration=1.0)
    """
    return proj.add_clip(project_path, file, start=start, end=end,
                          transition_in=transition_in, transition_in_duration=transition_in_duration)


@mcp.tool()
def remove_clip(project_path, index):
    """
    从项目主时间轴中删除第 index 个片段(从 0 开始计数)。

    Input: project_path (str), index (int)
    Output: {removed, clip_count}
    Usage: remove_clip(project_path="D:\\...\\my_project.json", index=2)
    """
    return proj.remove_clip(project_path, index)


@mcp.tool()
def add_overlay(project_path, file, x=0, y=0, width=None, height=None, opacity=1.0,
                start_time=0.0, end_time=None, audio=False):
    """
    向项目添加一个叠加层(图片、贴纸、文字图层、透明背景视频等)，叠加在最终
    合成画面之上。时间区间 start_time/end_time 相对于渲染出的整段视频时间轴
    (而不是主时间轴上某个片段内部)。

    Input:
      project_path (str) - 项目 JSON 文件路径。
      file (str) - 叠加层文件路径(图片，或带透明通道的视频如 webm/mov)。

    Optional params:
      x/y (int, 默认 0): 叠加层左上角在画布上的像素坐标。
      width/height (int, 默认 None): 缩放叠加层到指定像素尺寸。传 -1 表示
        按比例自动计算另一边。不传则使用原始尺寸。
      opacity (number, 默认 1.0): 不透明度(0.0-1.0)。
      start_time/end_time (number, 默认 0.0 / None): 叠加层在最终视频中出现的
        起止时间(秒)。end_time 不传则持续到视频结尾。
      audio (bool, 默认 False): 是否混入该叠加层文件自身的音轨(仅对视频
        文件有效，图片忽略)。

    Output: {index, overlay, overlay_count}
    Usage:
      add_overlay(project_path="D:\\...\\my_project.json", file="D:\\...\\logo.png",
                   x=20, y=20, width=200, start_time=0, end_time=5)
    """
    return proj.add_overlay(project_path, file, x=x, y=y, width=width, height=height,
                             opacity=opacity, start_time=start_time, end_time=end_time, audio=audio)


@mcp.tool()
def remove_overlay(project_path, index):
    """
    从项目中删除第 index 个叠加层(从 0 开始计数)。

    Input: project_path (str), index (int)
    Output: {removed, overlay_count}
    Usage: remove_overlay(project_path="D:\\...\\my_project.json", index=0)
    """
    return proj.remove_overlay(project_path, index)


@mcp.tool()
def get_project(project_path):
    """
    读取并返回项目的完整内容(画布尺寸/帧率、所有片段、所有叠加层)，并附带
    根据片段时长和转场估算的总时长(estimated_duration)，渲染前用于检查项目结构。

    Input: project_path (str)
    Output: {width, height, fps, clips, overlays, estimated_duration}
    Usage: get_project(project_path="D:\\...\\my_project.json")
    """
    return proj.get_project(project_path)


@mcp.tool()
def render_project(project_path, output_path=None):
    """
    渲染整个项目为最终视频文件: 依次将每个片段裁剪并缩放/填充到统一的画布
    尺寸和帧率，应用片段之间设置的转场效果(xfade/acrossfade)，再叠加所有
    叠加层(图片/贴纸/透明视频，支持时间区间、位置、缩放、透明度)，输出为
    一个 mp4 文件。

    Input: project_path (str) - 已通过 add_clip/add_overlay 配置好的项目文件。

    Optional params:
      output_path (str, 默认 None): 输出文件路径。不传则默认为
        D:\\...\\Output\\<项目名>\\<项目名>_render.mp4

    Output: {output_path, duration, clip_count, overlay_count}
    Usage: render_project(project_path="D:\\...\\my_project.json")
    """
    return proj.render_project(project_path, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
