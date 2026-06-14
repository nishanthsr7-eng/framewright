import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

cur_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, cur_path + "/..")

from mcp.server.fastmcp import FastMCP
from audio_analyzer_mcp import analyzer

mcp = FastMCP("audio-analyzer-mcp")


@mcp.tool()
def get_audio_info(audio_path):
    """
    返回音频/视频文件的音频基本信息：时长(秒)、采样率、整体响度(RMS均值/最大值)。

    Input:
      audio_path (str): 音频或视频文件路径（视频会自动提取音轨）。

    Usage: get_audio_info(audio_path="D:\\...\\Sources\\clip.mp4")
    """
    return analyzer.get_audio_info(audio_path)


@mcp.tool()
def detect_beats(audio_path, start_time=0.0, duration=None):
    """
    检测音频的节奏(BPM)和节拍时间点列表，可用于按节奏做卡点剪辑（每个节拍点切一刀、
    在节拍上触发文字/特效等）。

    Input:
      audio_path (str): 音频或视频文件路径。

    Optional params:
      start_time (float): 分析起始时间(秒)，默认 0。
      duration (float): 分析时长(秒)，默认到文件结尾。

    Output:
      tempo_bpm (float): 估计的速度(每分钟节拍数)。
      beat_times (List[float]): 每个节拍发生的时间点(秒)。
      beat_count (int): 节拍总数。

    Usage: detect_beats(audio_path="D:\\...\\Sources\\clip.mp4")
    """
    return analyzer.detect_beats(audio_path, start_time=start_time, duration=duration)


@mcp.tool()
def detect_downbeats(audio_path, start_time=0.0, duration=None, beats_per_bar=4):
    """
    在节拍基础上估计"重拍"(downbeat，每小节第一拍)时间点，比 detect_beats 的节拍点
    更稀疏、更适合作为大段落切换、最强特效或转场的卡点。

    Input:
      audio_path (str): 音频或视频文件路径。

    Optional params:
      start_time (float): 分析起始时间(秒)，默认 0。
      duration (float): 分析时长(秒)，默认到文件结尾。
      beats_per_bar (int): 每小节拍数，默认 4 (4/4 拍)。

    Output:
      tempo_bpm (float): 估计速度。
      beats_per_bar (int)
      downbeat_times (List[float]): 每个重拍的时间点(秒)。
      downbeat_count (int)

    Usage: detect_downbeats(audio_path="D:\\...\\Sources\\clip.mp4")
    """
    return analyzer.detect_downbeats(audio_path, start_time=start_time, duration=duration, beats_per_bar=beats_per_bar)


@mcp.tool()
def detect_sections(audio_path, start_time=0.0, duration=None, n_sections=None):
    """
    将音频分割为若干结构性段落（启发式标签：intro / build / drop / chorus / verse /
    outro），按相对能量定位"高潮/drop"位置，适合决定在哪里放置最强的特效/文字反转。

    Input:
      audio_path (str): 音频或视频文件路径。

    Optional params:
      start_time (float): 分析起始时间(秒)，默认 0。
      duration (float): 分析时长(秒)，默认到文件结尾。
      n_sections (int): 段落数量。不传则按时长自动估计 (约 时长/8秒，限制在 2~8)。

    Output:
      sections (List[{label, start, end, energy}]): energy 为相对最大段落能量
      归一化后的值 (0~1)。

    Usage: detect_sections(audio_path="D:\\...\\Sources\\song.mp3")
    """
    return analyzer.detect_sections(audio_path, start_time=start_time, duration=duration, n_sections=n_sections)


@mcp.tool()
def detect_impacts(audio_path, start_time=0.0, duration=None, sensitivity=1.0):
    """
    检测音频中的"冲击/瞬态"时刻（鼓点、打击声、突然的响度变化等），每个时刻附带相对强度
    (0~1)。适合用作转场、特效触发、文字弹出的时间点。

    Input:
      audio_path (str): 音频或视频文件路径。

    Optional params:
      start_time (float): 分析起始时间(秒)，默认 0。
      duration (float): 分析时长(秒)，默认到文件结尾。
      sensitivity (float): 灵敏度，默认 1.0。数值越大检测到的瞬态点越多。

    Output:
      impact_count (int): 检测到的瞬态点数量。
      impacts (List[{time, strength}]): 每个瞬态点的时间(秒)和相对强度(0~1)。

    Usage: detect_impacts(audio_path="D:\\...\\Sources\\clip.mp4", sensitivity=1.5)
    """
    return analyzer.detect_impacts(audio_path, start_time=start_time, duration=duration, sensitivity=sensitivity)


@mcp.tool()
def analyze_audio_features(audio_path, start_time=0.0, duration=None, window=1.0):
    """
    按时间窗口分析音频的能量(RMS)、频谱中心(spectral centroid)、过零率(zero crossing
    rate)等特征，并给出整段的统计汇总。可用于找出最响亮/最安静/最"明亮"的片段。

    Input:
      audio_path (str): 音频或视频文件路径。

    Optional params:
      start_time (float): 分析起始时间(秒)，默认 0。
      duration (float): 分析时长(秒)，默认到文件结尾。
      window (float): 每个分析窗口的长度(秒)，默认 1.0。

    Output:
      window_seconds (float): 窗口长度。
      windows (List[{time, rms, spectral_centroid, zero_crossing_rate}]): 每个窗口
        的特征值。
      summary ({rms_mean, rms_max, spectral_centroid_mean, zero_crossing_rate_mean}):
        整段的统计汇总。

    Usage: analyze_audio_features(audio_path="D:\\...\\Sources\\clip.mp4", window=0.5)
    """
    return analyzer.analyze_audio_features(audio_path, start_time=start_time, duration=duration, window=window)


@mcp.tool()
def transcribe_audio(audio_path, model_size="base", language=None, word_timestamps=True):
    """
    使用 faster-whisper 在本地将音频/视频中的语音转录为文字（"audio text"），支持词级
    时间戳，可用于自动生成字幕或对齐文字特效出现的时机。

    首次使用某个 model_size 时会从 huggingface 自动下载模型权重（需要联网），之后会缓存
    在本地，无需重复下载。

    Input:
      audio_path (str): 音频或视频文件路径。

    Optional params:
      model_size (str): Whisper 模型大小，"tiny" | "base" (默认) | "small" | "medium" |
        "large-v3"。越大越准确但越慢，"base" 对大多数场景足够。
      language (str): 语言代码(如 "en"、"zh")，不传则自动检测。
      word_timestamps (bool): 是否输出词级时间戳，默认 True。

    Output:
      language (str): 检测/指定的语言代码。
      language_probability (float): 语言检测置信度。
      text (str): 完整转录文本。
      segments (List[{start, end, text, words}]): 按句/段划分的转录结果，words 为
        每个词的 {word, start, end}。

    Usage: transcribe_audio(audio_path="D:\\...\\Sources\\clip.mp4", model_size="base")
    """
    return analyzer.transcribe_audio(audio_path, model_size=model_size, language=language, word_timestamps=word_timestamps)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
