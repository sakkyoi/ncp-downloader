from pathlib import Path
from warnings import warn

from api.api import NCP, ChannelID
from util.m3u8_downloader import M3U8Downloader
from util.manager import ChannelManager


class ChannelDownloader(object):
    """
    Download videos from channel

    Args:
        nico (NCP): NCP object
        channel_id (ChannelID): channel id
        video_list (list): list of video id
        output (str): output directory
        target_resolution (tuple, optional): target resolution of video. Defaults to None.
        resume (bool, optional): resume download. Defaults to None.
        transcode (bool, optional): transcode video. Defaults to None.
        ffmpeg (str, optional): ffmpeg path. Defaults to 'ffmpeg'.
        vcodec (str, optional): video codec. Defaults to 'copy'.
        acodec (str, optional): audio codec. Defaults to 'copy'.
        ffmpeg_options (list, optional): ffmpeg options. Defaults to None.
        wait (float, optional): wait time between each request(exclude download). Defaults to 1.
    """
    def __init__(self, nico: NCP, channel_id: ChannelID, video_list: list, output: str,
                 target_resolution: tuple = None, resume: bool = None, transcode: bool = None, ffmpeg: str = 'ffmpeg',
                 vcodec: str = 'copy', acodec: str = 'copy', ffmpeg_options: list = None,
                 thread: int = 1, wait: float = 1) -> None:
        self.nico = nico

        self.channel_id = channel_id
        self.video_list = video_list
        self.output = output
        self.target_resolution = target_resolution
        self.resume = resume
        self.transcode = transcode
        self.ffmpeg = ffmpeg
        self.vcodec = vcodec
        self.acodec = acodec
        self.ffmpeg_options = ffmpeg_options
        self.thread = thread
        self.wait = wait

        self.ChannelManager = ChannelManager(self.nico, self.output, wait=self.wait, resume=self.resume)

        # workflow
        self.__init_manager()
        self.__download()

    def __init_manager(self) -> None:
        """Init m3u8 manager"""
        done, total = self.ChannelManager.init_manager(self.video_list)
        self.done = done
        self.total = total

    def __download(self) -> None:
        """Download videos"""
        for video in self.video_list:
            if self.ChannelManager.get_status(str(video)):
                continue

            session_id = self.nico.get_session_id(video)

            if session_id is None:
                warn(f'Video {video} not found or permission denied. Skip.', stacklevel=2)
                continue

            output_name, _ = self.nico.get_video_name(video, self.ChannelManager.get_title(str(video)))
            output = str(Path(self.output).joinpath(f'{output_name}'))

            tip = f'({self.done+1}/{self.total})'

            m3u8_downloader = M3U8Downloader(self.nico, session_id, output, self.target_resolution,
                                             self.ChannelManager.continue_exists_video, self.transcode,
                                             self.ffmpeg, self.vcodec, self.acodec, self.ffmpeg_options,
                                             self.thread, tip)
            if m3u8_downloader.done:
                self.ChannelManager.set_status(str(video), True)
                self.done += 1


if __name__ == '__main__':
    pass
