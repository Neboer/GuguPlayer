from typing import TypedDict
from bilibili_api import video
from fake_useragent import UserAgent

class Track(TypedDict):
    title: str
    bvid: str
    p: int  # 视频的分P编号
    cid: int  # 视频的CID编号

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


class BilibiliAPI:
    def __init__(self):
        self.ua = UserAgent(os="Windows").chrome
        self.http_headers = {
            "referer": "https://www.bilibili.com/",
            "User-Agent": self.ua,
        }

    async def get_best_audio_stream(
        self, track: Track
    ) -> video.VideoStreamDownloadURL | video.AudioStreamDownloadURL:
        """
        从一个 Track 对象中提取最优的音频流 URL。
        """
        v = video.Video(track["bvid"])
        if "cid" not in track or "p" not in track:
            download_url_data = await v.get_download_url(0)
        else:
            download_url_data = await v.get_download_url(
                track.get("p"), track.get("cid")
            )

        detector = video.VideoDownloadURLDataDetecter(data=download_url_data)
        if not detector.check_video_and_audio_stream():
            raise ValueError("No valid audio or video stream found.")

        streams = detector.detect_all()
        best_stream: video.VideoStreamDownloadURL | video.AudioStreamDownloadURL = (
            sort_streams(streams)[0]
        )
        return best_stream
