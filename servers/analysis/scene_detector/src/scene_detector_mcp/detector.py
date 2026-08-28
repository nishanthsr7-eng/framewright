import os

from framewright_core import output_root as _get_output_root
from scenedetect import SceneManager, open_video, split_video_ffmpeg
from scenedetect.detectors import ContentDetector


def _find_scenes(video_path, threshold=27.0, min_scene_len=15):
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))
    scene_manager.detect_scenes(video=video, show_progress=False)
    return video, scene_manager.get_scene_list()


def detect_scenes(video_path: str, threshold: float = 27.0, min_scene_len: int = 15) -> dict:
    """
    检测视频中的镜头/场景切换点(基于画面内容变化)。

    threshold: 切换检测阈值，越小越敏感(检测到更多切换点)，默认 27.0。
    min_scene_len: 最短镜头长度(帧数)，默认 15。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")

    _, scene_list = _find_scenes(video_path, threshold=threshold, min_scene_len=min_scene_len)

    scenes = []
    for i, (start, end) in enumerate(scene_list):
        scenes.append(
            {
                "index": i + 1,
                "start": round(start.get_seconds(), 3),
                "end": round(end.get_seconds(), 3),
                "duration": round(end.get_seconds() - start.get_seconds(), 3),
            }
        )

    return {"scene_count": len(scenes), "scenes": scenes}


def split_scenes(
    video_path: str,
    output_folder: str | None = None,
    threshold: float = 27.0,
    min_scene_len: int = 15,
) -> dict:
    """
    检测视频镜头切换点，并将视频按镜头拆分为多个独立的视频文件(基于 ffmpeg)。
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")

    _, scene_list = _find_scenes(video_path, threshold=threshold, min_scene_len=min_scene_len)

    if output_folder is None:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_folder = os.path.join(_get_output_root(), f"{video_name}_scenes")
    os.makedirs(output_folder, exist_ok=True)

    if not scene_list:
        return {"scene_count": 0, "scenes": [], "output_folder": output_folder}

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    file_template = f"{video_name}-Scene-$SCENE_NUMBER.mp4"
    split_video_ffmpeg(
        video_path, scene_list, output_dir=output_folder, output_file_template=file_template, show_progress=False
    )

    scenes = []
    for i, (start, end) in enumerate(scene_list):
        scenes.append(
            {
                "index": i + 1,
                "start": round(start.get_seconds(), 3),
                "end": round(end.get_seconds(), 3),
                "duration": round(end.get_seconds() - start.get_seconds(), 3),
                "file": os.path.join(output_folder, file_template.replace("$SCENE_NUMBER", f"{i + 1:03d}")),
            }
        )

    return {"scene_count": len(scenes), "scenes": scenes, "output_folder": output_folder}
