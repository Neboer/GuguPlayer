from typing import List, Union
from bilibili_api import video

def stream_sort_key(stream):
    # 音频优先（0 比 1 小）
    if hasattr(stream, "audio_quality"):
        priority = 0
        quality = stream.audio_quality
        quality_order = list(video.AudioQuality)
    elif hasattr(stream, "video_quality"):
        priority = 1
        quality = stream.video_quality
        quality_order = list(video.VideoQuality)
    else:
        # 未知类型，放最后
        return (2, 0)

    # 构造清晰度排序值：越靠后代表质量越好
    try:
        quality_index = quality_order.index(quality)
    except ValueError:
        quality_index = -1

    # 返回元组：第一优先音频/视频，第二优先清晰度高
    return (priority, -quality_index)


def sort_streams(streams):
    return sorted(streams, key=stream_sort_key)