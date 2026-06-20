import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from scene_detector_mcp import detector

mcp = FastMCP("scene-detector-mcp")


@mcp.tool()
def detect_scenes(video_path, threshold=27.0, min_scene_len=15):
    """
    检测视频中的镜头/场景切换点(基于画面内容变化，PySceneDetect ContentDetector)。
    适合在剪辑前先了解一个素材有哪些镜头、每个镜头的时间范围。

    Input:
      video_path (str): 源视频文件路径。

    Optional params:
      threshold (float): 切换检测阈值，默认 27.0。值越小越敏感(检测到更多切换点)，
        值越大越不敏感。
      min_scene_len (int): 最短镜头长度(帧数)，默认 15，避免检测到过短的误判镜头。

    Output:
      scene_count (int)
      scenes (List[{index, start, end, duration}])

    Usage: detect_scenes(video_path="D:\\...\\Sources\\clip.mp4")
    """
    return detector.detect_scenes(video_path, threshold=threshold, min_scene_len=min_scene_len)


@mcp.tool()
def split_scenes(video_path, output_folder=None, threshold=27.0, min_scene_len=15):
    """
    检测视频镜头切换点，并将视频按镜头拆分为多个独立的视频文件(ffmpeg)。
    适合在 extract_frames_from_video/extract_character 等逐帧处理前，先按镜头拆分，
    只处理需要的镜头。

    Input:
      video_path (str): 源视频文件路径。

    Optional params:
      output_folder (str): 输出目录。不传则默认为
        D:\\...\\Output\\<视频名>_scenes\\
      threshold (float): 切换检测阈值，默认 27.0。
      min_scene_len (int): 最短镜头长度(帧数)，默认 15。

    Output:
      scene_count (int)
      scenes (List[{index, start, end, duration, file}])
      output_folder (str)

    Usage: split_scenes(video_path="D:\\...\\Sources\\clip.mp4")
    """
    return detector.split_scenes(video_path, output_folder=output_folder, threshold=threshold, min_scene_len=min_scene_len)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
