from BilibiliAPI import BilibiliAPI, Track
from FFplayerBackend import FFPlayerBackend

from textual.app import App, ComposeResult
from textual.widgets import Static, ListView, ListItem, Label
from textual import events
from textual.reactive import reactive
from textual import log

from typing import TypedDict, List, Callable, Optional

import json
import asyncio
from sys import argv


class TrackListItem(ListItem):
    def __init__(self, track: Track):
        super().__init__(Label(track["title"]))
        self.track = track


def load_tracks_from_json() -> List[Track]:
    if len(argv) > 1:
        file_path = argv[1]
    else:
        file_path = "playlist.json"
    with open(file_path, "r", encoding="utf8") as f:
        tracks = json.load(f)
    return tracks
    # player.load_playlist(tracks)
    # player.current_track_index = 0  # 从第一首曲目开始播放
    # await player.start_play_track()

# class PlayStatusPanel(Static):
#     def __init__(self):
#         super().__init__()
#         self.playing = False

#     def render(self) -> str:
#         return "Playing" if self.playing else "Paused"

#     def update_status(self, playing: bool):
#         self.playing = playing
#         self.refresh()  # 刷新显示


class TUIPlayer(App):
    CSS = """
    ListView {
        height: 100%;
        border: round yellow;
    }
    """

    # 初始化时传入的 Track 列表
    def __init__(self):
        super().__init__()
        self.track_list = load_tracks_from_json()
        self.bilibili_api = BilibiliAPI()
        self.player = FFPlayerBackend(
            asyncio.get_event_loop(), self.bilibili_api.http_headers
        )

        self.playing_task: None | asyncio.Task = None
        self.playing = False  # 播放状态

    def compose(self) -> ComposeResult:
        self.list_view = ListView(*[TrackListItem(track) for track in self.track_list])
        yield self.list_view

    def on_mount(self) -> None:
        self.list_view.index = 0  # 默认选中第一项

    @property
    def current_track(self) -> Optional[Track]:
        if self.list_view.index is not None:
            return self.track_list[self.list_view.index]
        return None

    def player_pause(self):
        if self.playing:
            log.info("Pausing player...")
            self.player.pause()
            self.playing = False
        else:
            log.info("Player is already paused.")

    def player_resume(self):
        if not self.playing:
            log.info("Resuming player...")
            self.player.resume()
            self.playing = True
        else:
            log.info("Player is already playing.")

    # 清理当前播放任务，停止播放器。
    async def player_stop(self):
        if self.playing_task and not self.playing_task.done():
            log.info("Stopping player...")

            self.player_pause()
            self.player.stop()
            self.playing_task.cancel()
            self.playing_task = None
        else:
            log.info("No player task to stop.")

    async def track_playing_task(self, url):
        await self.player.async_play_audio(url)
        await self.player_stop()
        log.info(f"Track ${self.current_track} finished playing.")

    async def player_start(self):
        track = self.current_track
        if track:
            log.info(f"Starting playback for track: {track['title']}")
            stream = await self.bilibili_api.get_best_audio_stream(track)
            if stream:
                self.playing_task = asyncio.create_task(self.track_playing_task(stream.url))
                self.playing = True
            else:
                log.warning("No audio stream found for the selected track.")
        else:
            log.warning("No track selected to play.")


    async def on_space_key_pressed(self) -> None:
        # 如果正在播放，暂停；如果暂停，继续播放；如果没有播放，开始播放当前选中的曲目
        log.info("Space key pressed.")
        if self.playing:
            self.player_pause()
        else:
            if self.playing_task and not self.playing_task.done():
                self.player_resume()
            else:
                await self.player_start()
    
    async def on_enter_key_pressed(self) -> None:
        # 无论是否正在播放，立即暂停开始播放当前选中的曲目
        log.info("Enter key pressed.")
        await self.player_stop()
        await self.player_start()

    async def on_key(self, event: events.Key) -> None:
        # 支持手动上下键选择
        # if event.key == "up":
        #     self.list_view.action_cursor_up()
        # elif event.key == "down":
        #     self.list_view.action_cursor_down()
        if event.key == "space":
            await self.on_space_key_pressed()
        elif event.key == "q":
            await self.player_stop()
        elif event.key == "enter":
            await self.on_enter_key_pressed()
        # ctrl+q 退出


async def main():
    app = TUIPlayer()
    await app.run_async()  # 启动应用


if __name__ == "__main__":
    asyncio.run(main())
