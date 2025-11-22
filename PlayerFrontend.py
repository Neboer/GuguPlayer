from BilibiliAPI import BilibiliAPI, Track
from FFplayerBackend import FFPlayerBackend

from textual.app import App, ComposeResult
from textual.widgets import Static, ListView, ListItem, Label
from textual import events
from textual.reactive import reactive
from textual import log

from typing import TypedDict, List, Callable, Optional, Union

import json
import asyncio
from sys import argv
from bilibili_api import video


from typing import Optional, cast


class TrackListItem(ListItem):
    def __init__(self, track: Track):
        self.label = Label(track["title"])
        super().__init__(self.label)
        self.track = track

    def set_color(self, color: Optional[str] = None):
        if color:
            self.label.styles.color = color
        else:
            self.label.styles.color = None


def load_tracks_from_json() -> List[Track]:
    if len(argv) > 1:
        file_path = argv[1]
    else:
        file_path = "playlist.json"
    with open(file_path, "r", encoding="utf8") as f:
        tracks = json.load(f)
    return tracks


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
            asyncio.get_event_loop(),
            self.bilibili_api.http_headers,
            # log_callback=self._log_callback,
        )

        self.playing_task: Union[None, asyncio.Task] = None
        self.playing = False  # 播放状态
        self.playing_track_id: Union[int, None] = None  # 当前播放的 Track 索引

    # def _log_callback(self, level: str, message: str):
    #     log("ffpyplayer", message)
    #     if level == "error":
    #         log.error(message)
    #     elif level == "warning":
    #         log.warning(message)
    #     elif level == "info":
    #         log.info(message)
    #     elif level == "debug":
    #         log.debug(message)
    #     else:
    #         log(level, message)

    def compose(self) -> ComposeResult:
        self.list_view = ListView(*[TrackListItem(track) for track in self.track_list])
        yield self.list_view

    def on_mount(self) -> None:
        self.list_view.index = 0  # 默认选中第一项

    @property
    def current_selected_track(self) -> Optional[Track]:
        if self.list_view.index is not None:
            return self.track_list[self.list_view.index]
        return None

    @property
    def current_playing_listitem(self) -> Optional[TrackListItem]:
        if self.playing_track_id is not None:
            item = self.list_view.children[self.playing_track_id]
            if isinstance(item, TrackListItem):
                return item
        return None

    def _change_playing_track_color(self, color: Union[str,None]):
        self.current_playing_listitem.set_color(color) if self.current_playing_listitem else None

    def player_pause(self):
        if self.playing:
            log.info("Pausing player...")
            self.player.pause()
            self.playing = False
            # Set current track color to red
            self._change_playing_track_color("red")
        else:
            log.info("Player is already paused.")

    def player_resume(self):
        if not self.playing:
            log.info("Resuming player...")
            self.player.resume()
            self.playing = True
            # Set current track color to green
            self._change_playing_track_color("green")
        else:
            log.info("Player is already playing.")

    # 清理当前播放任务，停止播放器。
    async def player_stop(self):
        self._change_playing_track_color(None)
        if self.playing_task and not self.playing_task.done():
            log.info("Stopping player...")

            self.playing = False
            self.playing_track_id = None
            self.player.stop()
            self.playing_task.cancel()
            self.playing_task = None
        else:
            log.info("No player task to stop.")
        # Reset color to default

    async def track_playing_task(self, url):
        await self.player.async_play_audio(url)
        await self.player_stop()
        log.info(f"Track ${self.current_selected_track} finished playing.")

    async def player_start(self):
        track = self.current_selected_track
        track_index = self.list_view.index
        if track:
            log.info(f"Starting playback for track: {track['title']}")
            stream = await self.bilibili_api.get_best_audio_stream(track)
            if stream:
                # Try to get a quality attribute if available
                quality = (
                    getattr(stream, "audio_quality", None)
                    or getattr(stream, "video_quality", None)
                    or "unknown"
                )
                log.info(f"Playing stream with quality: {quality}")
                self.playing_task = asyncio.create_task(
                    self.track_playing_task(stream.url)
                )

                self.playing = True
                self.playing_track_id = track_index
                # Set current track color to green (playing)
                self._change_playing_track_color("green")
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
        if event.key == "space":
            await self.on_space_key_pressed()
        elif event.key == "q":
            await self.player_stop()
        elif event.key == "enter":
            await self.on_enter_key_pressed()
        elif event.key == "t":
            await self.player_stop()
            log.info("T key pressed, debugging mode enabled.")
            self.playing_task = asyncio.create_task(
                self.player.async_play_audio(
                    "http://127.0.0.1:8000/file_example_MP3_2MG.mp3"
                )
            )
            # debug mode,自动请求
        # ctrl+q 退出


async def main():
    app = TUIPlayer()
    await app.run_async()  # 启动应用


if __name__ == "__main__":
    asyncio.run(main())
