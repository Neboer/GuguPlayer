# from functools import wraps
from ffpyplayer.player import MediaPlayer
from ffpyplayer.tools import set_log_callback, loglevels, set_loglevel
import time
import asyncio
from asyncio import sleep, gather, Event


def player_control(func):
    def wrapper(self, *args, **kwargs):
        if self.player is None:
            print(f"[警告] 播放器尚未启动: {func.__name__}")
            return None
        if self._loading_finished.is_set():
            print(f"[警告] 播放器尚未准备好（初始化中）: {func.__name__}")
            return None
        return func(self, *args, **kwargs)

    return wrapper


def format_ffmpeg_headers(headers: dict) -> str:
    """
    将一个字典格式的 headers 转换为 ffmpeg/ffpyplayer 所需的 header 字符串。
    每个 header 用 \r\n 分隔，最后一行也以 \r\n 结尾。

    Args:
        headers (dict): 要发送的 HTTP headers，例如 {"X-API-KEY": "abc", "X-SECRET": "123"}

    Returns:
        str: 格式化的 header 字符串，用于传递给 ffmpeg 的 -headers 参数。
    """
    return "".join(f"{key}: {value}\r\n" for key, value in headers.items())


ffmpeg_log_file = open("ffpyplayer.log", "a", encoding="utf8")


def current_log_callback(level, message):
    ffmpeg_log_file.write(f"[{level}] {message}\n")
    ffmpeg_log_file.flush()


class FFPlayerBackend:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        http_headers: dict = {},
        log_callback=None,
    ):
        self.player: MediaPlayer = None
        self._loop = loop
        self._play_finished: asyncio.Future = loop.create_future()
        self._http_headers = http_headers
        # if log_callback:
        set_loglevel("warning")
        set_log_callback(current_log_callback)

        self._loading_time_s = 0.1  # 模拟加载时间
        self._loading_finished: Event = Event()  # 用于等待加载完成

        self._loading_finished.set()  # 初始时设置为已完成
        self._loading_manager_task: asyncio.Task | None = None

    # async def wait_until_ready(self):

    def _media_callback(self, selector, value):
        if selector == "eof":
            self._loop.call_soon_threadsafe(self._finish_playback)
        else:
            print(f"Media callback: {selector} - {value}")

    def _finish_playback(self):
        if not self._play_finished.done():
            self._play_finished.set_result(None)
        self._close_player()

    def _close_player(self):
        if self.player is not None:
            self.player.close_player()
            del self.player
            self.player = None

    async def _manage_loading_state(self):
        await sleep(self._loading_time_s)  # 模拟加载时间
        self._loading_finished.set()

    async def waiting_for_loading(self):
        return await self._loading_finished.wait()

    def start_play_audio(self, url: str):
        self._play_finished = self._loop.create_future()
        self._loading_finished.clear()  # 需要等待加载完成
        if self._loading_manager_task and not self._loading_manager_task.done():
            self._loading_manager_task.cancel()
        self._loading_manager_task = asyncio.create_task(self._manage_loading_state())

        ffmpeg_lib_opts: dict = {
            "reconnect": bytes(1),
            # "reconnect_at_eof": "1",
            # "reconnect_streamed": "1",
            # "reconnect_delay_max": "4000",
            # "reconnect_max_retries": "5",
            # "reconnect_delay_total_max": "30",
            # "respect_retry_after": "1"
        }

        ffmpeg_ff_opts = {
            "autoexit": True,
            "vn": True,
            "sn": True,
            "re": True,
        }

        if self._http_headers:
            ffmpeg_lib_opts.update(
                {
                    "headers": format_ffmpeg_headers(self._http_headers),
                }
            )

        self.player = MediaPlayer(
            url,
            callback=self._media_callback,
            lib_opts=ffmpeg_lib_opts,
            ff_opts=ffmpeg_ff_opts,
        )

    @property
    @player_control
    def elapsed_time(self):
        return self.player.get_pts()

    @player_control
    def pause(self):
        self.player.set_pause(True)

    @player_control
    def resume(self):
        self.player.set_pause(False)

    @player_control
    def stop(self):
        if not self._play_finished.done():
            self._play_finished.set_result(None)
        self._close_player()

    @player_control
    def get_metadata(self):
        return self.player.get_metadata()

    async def async_play_audio(self, url: str):
        self.start_play_audio(url)
        await self._play_finished


if __name__ == "__main__":

    async def main():
        url = "http://127.0.0.1:8000/Battle City.mp3"
        backend = FFPlayerBackend(asyncio.get_event_loop())

        async def stop_2s():
            await sleep(50)
            backend.pause()

        async def show_elapsed_time():
            while True:
                if backend.elapsed_time is None:
                    print("播放器未初始化或已关闭")
                    await sleep(0.2)
                    continue
                print(f"已播放时间: {backend.elapsed_time:.2f} 秒")
                await sleep(0.5)

        await gather(backend.async_play_audio(url), show_elapsed_time(), stop_2s())
        print("音频播放完毕")

    asyncio.run(main())
