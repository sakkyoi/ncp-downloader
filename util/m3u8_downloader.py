import requests
import m3u8
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC as RFC8216MediaSegmentEncryptMode
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.padding import PKCS7
import time
import inquirer
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.api import NCP, SessionID
from util.ffmpeg import FFMPEG
from util.manager import M3U8Manager
from util.progress import ProgressManager


class M3U8Downloader(object):
    """
    Download video from m3u8 url

    Args:
        api_client (NCP): NCP object
        progress_manager (ProgressManager): progress manager
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
        wait (float, optional): wait time between each request(exclude download). Defaults to 1.
    """
    def __init__(self, api_client: NCP, progress_manager: ProgressManager, session_id: SessionID, output: str,
                 targer_resolution: tuple = None, resume: bool = None, transcode: bool = None,
                 ffmpeg: str = 'ffmpeg', vcodec: str = 'copy', acodec: str = 'copy', ffmpeg_options: list = None,
                 thread: int = 1, wait: float = 1) -> None:
        # args
        self.api_client = api_client
        self.progress_manager = progress_manager
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
        self.wait = wait

        # init manager
        self.m3u8_manager = M3U8Manager(f'{self.output}.ts', resume=self.resume)

        # data load from session
        self.video_index = None
        self.target_video = None

        # decrypt settings
        self.algorithm = AES  # Decrypt algorithm
        self.mode = RFC8216MediaSegmentEncryptMode  # Decrypt mode
        self.unpadder = PKCS7(128)
        self.key = None  # Decrypt key

        # init task progress
        self.task = self.progress_manager.add_task('Start downloading', total=None)

        self.done = False

    def start(self) -> bool:
        """Start downloading video"""

        # loop until all segments are downloaded
        while True:
            # check if video is available and get video index
            if not self.__get_video_index():
                self.progress_manager.stop_task(self.task)
                return False

            # workflow
            self.__get_target_video()
            self.__get_key()
            self.__init_manager()
            # until all segments are downloaded, break
            if self.__download_threading():
                break

        self.__concat_temp()

        return True

    def __get_video_index(self) -> bool:
        """Get video index from session id"""
        # update progress bar
        self.progress_manager.reset(self.task, description='Getting video index')

        # get video index from session
        r = requests.get(self.api_client.api_video_index % self.session_id)
        if 'Error' in r.text:
            return False

        self.video_index = m3u8.loads(r.text)

        time.sleep(self.wait)  # don't spam the server

        return True  # this is for checking if the video is available now

    def __get_target_video(self) -> None:
        """Get target video from video index"""
        # update progress bar
        self.progress_manager.reset(self.task, description='Getting target resolution')

        target_video = self.video_index.playlists[0].uri  # default to the highest resolution
        if self.target_resolution is not None:
            for playlist in reversed([*self.video_index.playlists]):
                if playlist.stream_info.resolution >= self.target_resolution:
                    target_video = playlist.uri
                    break

        # get target video from video index
        r = requests.get(target_video)

        self.target_video = m3u8.loads(r.text)

        time.sleep(self.wait)  # don't spam the server

    def __get_key(self) -> None:
        """Get key from target video"""
        # update progress bar
        self.progress_manager.reset(self.task, description='Getting key')

        r = requests.get(self.target_video.keys[0].absolute_uri)
        self.key = r.content

        time.sleep(self.wait)  # don't spam the server

    def __decrypt(self, content: bytes, media_sequence):
        """
        Decrypt video segment

        Update on 2024/09/15, iv should be the media sequence number in big-endian binary
        representation into a 16-octet (128-bit) buffer and padding (on the left) with zeros.
        please refer to RFC 8216, Section 5.2:
        https://datatracker.ietf.org/doc/html/draft-pantos-hls-rfc8216bis#section-5.2
        """
        iv = media_sequence.to_bytes(16, 'big')
        cipher = Cipher(self.algorithm(self.key), self.mode(iv), backend=default_backend())

        decryptor = cipher.decryptor()
        decrypted = decryptor.update(content) + decryptor.finalize()

        unpadder = self.unpadder.unpadder()
        unpadded = unpadder.update(decrypted) + unpadder.finalize()

        return unpadded

    def __init_manager(self) -> None:
        """Initialize M3U8Manager"""
        # init manager
        # must stop live to prevent prompt not showing
        if self.resume is None:
            with self.progress_manager.pause():
                percentage = self.m3u8_manager.init_manager(self.target_video.segments)
        else:
            percentage = self.m3u8_manager.init_manager(self.target_video.segments)

        # update progress bar
        self.progress_manager.reset(self.task, total=1, completed=percentage)

    def __download_threading(self) -> bool:
        """Download video segments with threading"""
        # because we already reset the progress bar in __init_manager, we don't need to reset it again
        # just update the description
        self.progress_manager.update(self.task, description='Downloading video')

        # download video segments
        with ThreadPoolExecutor(max_workers=self.thread) as executor:
            futures = [executor.submit(self.__download_thread, segment) for segment in self.target_video.segments]

            try:
                for future in as_completed(futures):
                    future.result()
            except KeyboardInterrupt:
                self.progress_manager.live.console.print(
                    'got your interrupt request, hold on... do not press ctrl+c again', style='bold red on white')
                executor.shutdown(wait=False, cancel_futures=True)
                raise KeyboardInterrupt

        if not all(self.m3u8_manager.segment_db):
            return False

        return True

    def __download_thread(self, segment: m3u8.Segment) -> bool:
        """Download video segment"""
        # if the segment is already downloaded, skip
        if self.m3u8_manager.get_status(self.target_video.segments.index(segment)):
            # update progress bar
            self.progress_manager.update(self.task,
                                         completed=sum(self.m3u8_manager.segment_db) / len(self.target_video.segments))
            return True

        # or, download the segment
        r = requests.get(segment.absolute_uri, headers=self.api_client.headers)
        if r.status_code == 200:
            with open(f'{self.m3u8_manager.temp}/{self.target_video.segments.index(segment)}.ts', 'wb') as f:
                f.write(self.__decrypt(r.content, segment.media_sequence))

                # set the segment as downloaded
                self.m3u8_manager.set_status(self.target_video.segments.index(segment), True)

                # update progress bar
                self.progress_manager.update(self.task, completed=sum(self.m3u8_manager.segment_db) / len(
                    self.target_video.segments))
                return True

        # the segment failed to download(status code not 200)
        return False

    def __concat_temp(self) -> None:
        """Concatenate temp files"""
        # We don't want to reset the elapsed time, so we don't reset the progress bar
        self.progress_manager.update(self.task, description='Concatenating video', completed=0)

        with open(f'{self.output}.ts', 'wb') as f:
            for segment in self.target_video.segments:
                with open(f'{self.m3u8_manager.temp}/{self.target_video.segments.index(segment)}.ts', 'rb') as s:
                    f.write(s.read())

                percentage = (self.target_video.segments.index(segment) + 1) / len(self.target_video.segments)
                self.progress_manager.update(self.task, completed=percentage)

        # This question may not be asked by design
        if self.transcode is None:
            # must stop live to prevent prompt not showing
            with self.progress_manager.pause():
                self.transcode = True if inquirer.prompt([
                    inquirer.List('transcode', message='Do you want to transcode the video?',
                                  choices=['Yes', 'No'], default='Yes')
                ])['transcode'] == 'Yes' else False

        if self.transcode:
            # update progress bar
            self.progress_manager.update(self.task, description='Transcoding video', completed=0)

            _input = Path(f'{self.output}.ts')
            _output = f'{_input.parent.joinpath(_input.stem)}.mp4'

            ffmpeg = FFMPEG(self.ffmpeg).run(str(_input), _output, self.vcodec, self.acodec, self.ffmpeg_options)

            while True:
                n = next(ffmpeg)
                if n is not None:
                    self.progress_manager.update(self.task, completed=n)
                else:
                    _input.unlink()  # remove original file
                    self.progress_manager.update(self.task, completed=1)
                    break

        self.progress_manager.update(self.task, description='Removing temp files', completed=0, total=None)
        self.m3u8_manager.remove_temp()
        self.progress_manager.update(self.task, description='done!', completed=1)
        self.done = True


if __name__ == '__main__':
    raise RuntimeError('This file is not intended to be run as a standalone script.')
