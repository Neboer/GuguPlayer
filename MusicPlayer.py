from typing import TypedDict
from bilibili_api import video
from FFplayerBackend import FFPlayerBackend
from asyncio import AbstractEventLoop
import asyncio
from BiliBiliTrack import sort_streams
from fake_useragent import UserAgent
import json


class Track(TypedDict):
    title: str
    bvid: str
    p: int  # 视频的分P编号
    cid: int  # 视频的CID编号


class MusicPlayer:
    def __init__(self, loop: AbstractEventLoop):
        self.playlist = []
        self.current_track_index = 0
        self.ua = UserAgent(os="Windows").chrome
        self.player = FFPlayerBackend(
            loop,
            http_headers={
                "referer": "https://www.bilibili.com/",
                "User-Agent": self.ua,
            },
        )

    def load_playlist(self, tracks):
        self.playlist = tracks
        self.current_track_index = 0

    async def _get_video_audio_url(self, track: Track) -> str:
        v = video.Video(track["bvid"])
        if "cid" not in track or "p" not in track:
            # 如果没有提供 cid 和 p，则默认获取第一个分P的视频流
            download_url_data = await v.get_download_url(0)
        else:
            download_url_data = await v.get_download_url(
                track.get("p", None), track.get("cid", None)
            )
        detecter = video.VideoDownloadURLDataDetecter(data=download_url_data)
        if detecter.check_video_and_audio_stream():
            streams = detecter.detect_all()
            best_stream: video.VideoStreamDownloadURL | video.AudioStreamDownloadURL = (
                sort_streams(streams)[0]
            )
            return best_stream.url
        else:
            raise ValueError("No valid audio stream found for the video.")

    async def start_play_track(self):
        if self.playlist:
            current_track = self.playlist[self.current_track_index]
            print(f"Playing: {self.playlist[self.current_track_index]}")
            url = await self._get_video_audio_url(current_track)
            await self.player.async_play_audio(url)
        else:
            print("No tracks in the playlist.")


if __name__ == "__main__":

    async def main():
        loop = asyncio.get_event_loop()
        player = MusicPlayer(loop)

        # 示例播放列表
        with open("playlist.json", "r", encoding="utf8") as f:
            tracks = json.load(f)

        player.load_playlist(tracks)
        player.current_track_index = 0  # 从第一首曲目开始播放
        await player.start_play_track()

    asyncio.run(main())  # Properly start the event loop
