from ffpyplayer.player import MediaPlayer
import time
import asyncio
from asyncio import sleep, gather


def player_control(func):
    def wrapper(self, *args, **kwargs):
        if self.player is None:
            print(f"[警告] 播放器尚未启动: {func.__name__}")
            return None
        if (time.time() - self._init_ts) < self._init_wait:
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


class FFPlayerBackend:
    def __init__(self, loop: asyncio.AbstractEventLoop, http_headers: dict = {}):
        self.player: MediaPlayer = None
        self._loop = loop
        self._play_finished: asyncio.Future = loop.create_future()
        self._init_ts: float = 0.0
        self._init_wait: float = 0.1
        self._http_headers = http_headers

    def _media_callback(self, selector, value):
        if selector == "eof":
            self._loop.call_soon_threadsafe(self._finish_playback)

    def _finish_playback(self):
        if not self._play_finished.done():
            self._play_finished.set_result(None)
        self._close_player()

    def _close_player(self):
        if self.player is not None:
            self.player.close_player()
            del self.player
            self.player = None

    def start_play_audio(self, url: str):
        self._play_finished = self._loop.create_future()
        self._init_ts = time.time()

        if self._http_headers:
            self.player = MediaPlayer(
                url,
                callback=self._media_callback,
                lib_opts={"headers": format_ffmpeg_headers(self._http_headers)},
                ff_opts={"autoexit": True, "vn": True, "sn": True},
            )
        else:
            self.player = MediaPlayer(
                url,
                callback=self._media_callback,
                ff_opts={"autoexit": True, "vn": True, "sn": True},
            )

    @property
    @player_control
    def elapsed_time(self):
        return self.player.get_pts()

    @property
    @player_control
    def metadata(self):
        return self.player.get_metadata()

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

    async def async_play_audio(self, url: str):
        self.start_play_audio(url)
        await self._play_finished


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


if __name__ == "__main__":
    asyncio.run(main())
