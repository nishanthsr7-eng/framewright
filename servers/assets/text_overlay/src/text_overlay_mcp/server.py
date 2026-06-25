import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from text_overlay_mcp import overlay, renderer

mcp = FastMCP("text-overlay-mcp")


@mcp.tool()
def list_fonts():
    """
    列出可用于 add_text_overlay 的内置字体名称（均为粗体无衬线，适合做"剧透/反转"文字特效）。

    Output: 字体名称列表，例如 ["anton", "bebas-neue", "montserrat-extrabold",
    "oswald-bold", "poppins-extrabold"]
    """
    return renderer.list_fonts()


@mcp.tool()
def add_text_overlay(
    video_path,
    text,
    output_folder=None,
    font="anton",
    font_size=None,
    color="#FFFFFF",
    outline_color="#000000",
    outline_width=0,
    shadow=False,
    position="center",
    start_time=0.0,
    duration=None,
    animation="word_by_word",
    fps=None,
):
    """
    为视频添加"剪辑风格"的文字特效（如 "IT WAS YOU" 这类粗体大字标题），
    同时输出一个透明的文字叠加层视频和一个已将文字烧录进画面的完整视频。

    Input:
      video_path (str): 源视频文件路径。
      text (str): 要显示的文字，使用 "\\n" 可分多行。

    Optional params:
      output_folder (str): 输出目录。不传则默认为
        D:\\...\\Output\\<视频名>_text_overlay\\
      font (str): 字体名称，可选: "anton" (默认，超粗体大写，最常见的剧情反转/
        "IT WAS YOU" 风格), "bebas-neue" (瘦高型粗体), "montserrat-extrabold",
        "poppins-extrabold" (圆润现代粗体), "oswald-bold"。
        使用 list_fonts() 查看完整列表。
      font_size (int): 字号(像素)。不传则按视频高度自动计算 (约为高度的9%)。
      color (str | [str, str]): 文字颜色，hex 格式 "#RRGGBB"。
        传一个颜色为纯色填充；传两个颜色 ["#FFFFFF", "#FFD700"] 为从上到下的渐变
        (例如白到金色，常见的高光效果)。
      outline_color (str): 描边颜色 hex，默认黑色 "#000000"。
      outline_width (int): 描边宽度(像素)，0 = 无描边 (默认)。常见效果可设为 4~10。
      shadow (bool): 是否添加投影，默认 False。
      position (str): 文字位置 "top" | "center" (默认) | "bottom"。
      start_time (float): 文字开始出现的时间点(秒)，默认 0。
      duration (float): 文字显示的持续时间(秒)。不传则默认为从 start_time 到
        视频结尾。
      animation (str): 动画效果:
        - "none": 全程静态显示
        - "fade": 整体淡入 (默认动画时间内的前15%)
        - "word_by_word" (默认): 逐词淡入出现，模拟 "反转剧情" 文字逐字弹出的效果
        - "typewriter": 逐词快速依次出现 (打字机效果)
      fps (float): 叠加层帧率。不传则使用源视频帧率(最高30)。

    Output:
      output_folder/overlay.webm  - 透明背景的文字动画视频 (VP9 + alpha通道，
        可在其他编辑软件中作为叠加层使用)
      output_folder/output_burned.<ext> - 文字已烧录进画面的完整视频 (与源视频
        分辨率/音频一致)

    Usage:
      add_text_overlay(video_path="D:\\...\\Sources\\clip.mp4", text="IT WAS YOU",
                        font="anton", color=["#FFFFFF", "#FFD700"],
                        outline_color="#000000", outline_width=6,
                        position="center", start_time=2.0, duration=2.5,
                        animation="word_by_word")
    """
    return overlay.create_text_overlay(
        video_path=video_path,
        text=text,
        output_folder=output_folder,
        font=font,
        font_size=font_size,
        color=color,
        outline_color=outline_color,
        outline_width=outline_width,
        shadow=shadow,
        position=position,
        start_time=start_time,
        duration=duration,
        animation=animation,
        fps=fps,
    )


@mcp.tool()
def add_karaoke_captions(
    video_path,
    segments,
    output_folder=None,
    font="anton",
    font_size=None,
    color="#FFFFFF",
    highlight_color="#FFD700",
    outline_color="#000000",
    outline_width=6,
    shadow=True,
    position="bottom",
    max_words_per_line=6,
    fps=None,
):
    """
    根据词级时间戳，为视频添加"卡拉OK"风格字幕（逐词高亮，跟随语音节奏点亮），
    同时输出一个透明的字幕叠加层视频和一个已烧录字幕的完整视频。

    Input:
      video_path (str): 源视频文件路径。
      segments (List[{start, end, text, words: [{word, start, end}, ...]}]): 词级
        时间戳数据，直接使用 audio-analyzer-mcp 的 transcribe_audio(word_timestamps=True)
        返回结果中的 "segments" 字段。

    Optional params:
      output_folder (str): 输出目录。不传则默认为
        D:\\...\\Output\\<视频名>_karaoke\\
      font (str): 字体名称，见 text-overlay-mcp 的 list_fonts()，默认 "anton"。
      font_size (int): 字号(像素)。不传则按视频高度自动计算 (约为高度的5.5%)。
      color (str): 未播放词的颜色，hex 格式，默认 "#FFFFFF"。
      highlight_color (str): 已播放/正在播放词的高亮颜色，默认 "#FFD700" (金色)。
      outline_color (str): 描边颜色，默认 "#000000"。
      outline_width (int): 描边宽度(像素)，默认 6。
      shadow (bool): 是否添加投影，默认 True。
      position (str): 字幕位置 "top" | "center" | "bottom" (默认)。
      max_words_per_line (int): 每行最多显示的词数，默认 6。每个 segment 按此数量
        切分为多行。
      fps (float): 叠加层帧率。不传则使用源视频帧率(最高30)。

    Output:
      output_folder/overlay.webm - 透明背景的字幕动画视频 (VP9 + alpha通道)
      output_folder/output_burned.<ext> - 字幕已烧录进画面的完整视频

    Usage:
      # 1. 先用 audio-analyzer-mcp 转录:
      #    result = transcribe_audio(audio_path="D:\\...\\clip.mp4")
      # 2. 再用 result["segments"] 生成卡拉OK字幕:
      add_karaoke_captions(video_path="D:\\...\\Sources\\clip.mp4",
                            segments=result["segments"],
                            font="anton", highlight_color="#FFD700",
                            position="bottom")
    """
    return overlay.create_karaoke_captions(
        video_path=video_path,
        segments=segments,
        output_folder=output_folder,
        font=font,
        font_size=font_size,
        color=color,
        highlight_color=highlight_color,
        outline_color=outline_color,
        outline_width=outline_width,
        shadow=shadow,
        position=position,
        max_words_per_line=max_words_per_line,
        fps=fps,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
