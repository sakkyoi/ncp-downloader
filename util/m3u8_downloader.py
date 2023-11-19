import requests
import m3u8
from Crypto.Cipher import AES
from alive_progress import alive_bar
import time
from click import confirm
from pathlib import Path
import threading

from api.api import NicoChannelPlus, SessionID
from util.ffmpeg import FFMPEG
from util.manager import M3U8Manager


class M3U8Downloader:
    def __init__(self, session_id: SessionID, output: str, targer_resolution: tuple = None,
                 resume: bool = None, transcode: bool = None,
                 ffmpeg: str = 'ffmpeg', vcodec: str = 'copy', acodec: str = 'copy', ffmpeg_options: list = None,
                 thread: int = 1, tip: str = None, wait: float = 1) -> None:
        """
        Download video from m3u8 url

        Args:
            session_id (SessionID): session id of video
            output (str): output file name without extension
            targer_resolution (tuple, optional): target resolution of video. Defaults to None.
            resume (bool, optional): resume download. Defaults to None.
            transcode (bool, optional): transcode video. Defaults to None.
            ffmpeg (str, optional): ffmpeg path. Defaults to 'ffmpeg'.
            vcodec (str, optional): video codec. Defaults to 'copy'.
            acodec (str, optional): audio codec. Defaults to 'copy'.
            ffmpeg_options (list, optional): ffmpeg options. Defaults to None.
            thread (int, optional): number of threads. Defaults to 1.
            tip (str, optional): tip for alive_bar. Defaults to None.
            wait (float, optional): wait time between each request(exclude download). Defaults to 1.
        """
        self.nico = NicoChannelPlus()

        self.session_id = session_id
        self.output = output
        self.target_resolution = targer_resolution
        self.resume = resume
        self.transcode = transcode
        self.ffmpeg = ffmpeg
        self.vcodec = vcodec
        self.acodec = acodec
        self.ffmpeg_options = ffmpeg_options
        self.thread = thread
        self.tip = tip
        self.wait = wait

        self.M3U8Manager = M3U8Manager(f'{self.output}.ts', resume=self.resume)

        self.video_index = None
        self.target_video = None
        self.key = None

        # Create alive_bar
        self.alive_bar = alive_bar(force_tty=True, manual=True)
        self.bar = self.alive_bar.__enter__()
        self.bar.title(f'Start downloading {self.tip if self.tip is not None else ""}')

        self.done = False

        # workflow
        self.__get_video_index()
        self.__get_target_video()
        self.__get_key()
        self.__init_manager()
        self.__download_threading()
        self.__concat_temp()

    def __get_video_index(self) -> None:
        """Get video index from session id"""
        self.bar.title(f'Getting video index {self.tip if self.tip is not None else ""}')
        r = requests.get(self.nico.api_video_index % self.session_id)
        self.video_index = m3u8.loads(r.text)
        time.sleep(self.wait)  # don't spam the server

    def __get_target_video(self) -> None:
        """Get target video from video index"""
        self.bar.title(f'Getting target resolution {self.tip if self.tip is not None else ""}')
        target_video = self.video_index.playlists[0].uri  # default to the highest resolution
        if self.target_resolution is not None:
            for playlist in reversed([*self.video_index.playlists]):
                if playlist.stream_info.resolution >= self.target_resolution:
                    target_video = playlist.uri
                    break

        r = requests.get(target_video)
        self.target_video = m3u8.loads(r.text)
        time.sleep(self.wait)  # don't spam the server

    def __get_key(self) -> None:
        """Get key from target video"""
        self.bar.title(f'Getting key {self.tip if self.tip is not None else ""}')
        r = requests.get(self.target_video.keys[0].absolute_uri)
        self.key = AES.new(r.content, AES.MODE_CBC)
        time.sleep(self.wait)  # don't spam the server

    def __init_manager(self) -> None:
        """Initialize M3U8Manager"""
        if self.resume is None:
            with self.bar.pause():
                percentage = self.M3U8Manager.init_manager(self.target_video.segments)
        else:
            percentage = self.M3U8Manager.init_manager(self.target_video.segments)
        self.bar(percentage)

    def __download_threading(self) -> None:
        """Download video segments with threading"""
        self.bar.title(f'Downloading video {self.tip if self.tip is not None else ""}')
        threads = []
        self.thread_results = [False] * self.thread
        for segment in self.target_video.segments:
            if self.M3U8Manager.get_status(self.target_video.segments.index(segment)):
                continue
            threads.append(threading.Thread(target=self.__download_thread, args=(segment,), daemon=True,
                                            name=f'{self.target_video.segments.index(segment)}'))
            threads[-1].start()
            if len(threads) >= self.thread:
                for thread in threads:
                    thread.join()

                if not all(self.thread_results):
                    raise ConnectionRefusedError('Connection refused by server')
                for thread in threads:
                    self.M3U8Manager.set_status(int(thread.name), True)

                self.bar((int(threads[-1].name) + 1) / len(self.target_video.segments))
                threads = []

    def __download_thread(self, segment: m3u8.Segment) -> None:
        """Download video segment"""
        r = requests.get(segment.absolute_uri, headers=self.nico.headers)
        if r.status_code == 200:
            with open(f'{self.M3U8Manager.temp}/{self.target_video.segments.index(segment)}.ts', 'ab') as f:
                f.write(self.key.decrypt(r.content))
                self.thread_results[self.target_video.segments.index(segment) % self.thread] = True

    def __download(self) -> None:
        """Download video"""
        self.bar.title(f'Downloading video {self.tip if self.tip is not None else ""}')
        for segment in self.target_video.segments:
            if self.M3U8Manager.get_status(self.target_video.segments.index(segment)):
                continue
            r = requests.get(segment.absolute_uri)
            if r.status_code == 200:
                with open(f'{self.M3U8Manager.temp}/{self.target_video.segments.index(segment)}.ts', 'ab') as f:
                    f.write(self.key.decrypt(r.content))
                    self.M3U8Manager.set_status(self.target_video.segments.index(segment), True)
                    self.bar((self.target_video.segments.index(segment) + 1) / len(self.target_video.segments))

    def __concat_temp(self) -> None:
        """Concatenate temp files"""
        self.bar.title(f'Concatenating video {self.tip if self.tip is not None else ""}')
        with open(f'{self.output}.ts', 'wb') as f:
            for segment in self.target_video.segments:
                with open(f'{self.M3U8Manager.temp}/{self.target_video.segments.index(segment)}.ts', 'rb') as s:
                    f.write(s.read())
                self.bar((self.target_video.segments.index(segment) + 1) / len(self.target_video.segments))

        # This question may not be asked by design
        if self.transcode is None:
            with self.bar.pause():
                self.transcode = confirm('Do you want to transcode the video?', default=True)

        if self.transcode:
            self.bar.title(f'Transcoding video {self.tip if self.tip is not None else ""}')
            _input = Path(f'{self.output}.ts')
            _output = f'{_input.parent.joinpath(_input.stem)}.mp4'

            ffmpeg = FFMPEG(self.ffmpeg).run(str(_input), _output, self.vcodec, self.acodec, self.ffmpeg_options)

            while n := next(ffmpeg):
                if n is not None:
                    self.bar(n)
                else:
                    _input.unlink()  # remove original file
                    self.bar(1)

        self.bar.title(f'Removing temp files {self.tip if self.tip is not None else ""}')
        self.M3U8Manager.remove_temp()
        self.bar.title(f'done! {self.tip if self.tip is not None else ""}')
        self.done = True
        self.alive_bar.__exit__(None, None, None)


if __name__ == '__main__':
    raise Exception('This file is not meant to be executed')
