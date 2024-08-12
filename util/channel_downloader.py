from pathlib import Path

from api.api import NCP, ChannelID
from util.m3u8_downloader import M3U8Downloader
from util.manager import ChannelManager
from util.progress import ProgressManager


class ChannelDownloader(object):
    """
    Download videos from channel

    Args:
        api_client (NCP): NCP object
        progress_manager (ProgressManager): progress manager
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
    def __init__(self, api_client: NCP, progress_manager: ProgressManager, channel_id: ChannelID, video_list: list,
                 output: str, target_resolution: tuple = None, resume: bool = None, transcode: bool = None,
                 ffmpeg: str = 'ffmpeg', vcodec: str = 'copy', acodec: str = 'copy', ffmpeg_options: list = None,
                 thread: int = 1, select_manually: bool = False, wait: float = 1) -> None:
        # args
        self.api_client = api_client
        self.progress_manager = progress_manager
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
        self.select_manually = select_manually
        self.wait = wait

        # init manager
        self.channel_manager = ChannelManager(self.api_client, self.output, self.select_manually, self.progress_manager,
                                              self.wait, self.resume)

        # init task progress
        self.task = self.progress_manager.add_overall_task('Starting', total=None)

    def start(self) -> None:
        self.__init_manager()
        self.__download()

    def __init_manager(self) -> None:
        """Init m3u8 manager"""
        # update progress bar
        self.progress_manager.overall_reset(self.task, description='Initializing')

        done, total = self.channel_manager.init_manager(self.video_list, self.task)

        self.progress_manager.overall_update(self.task, completed=done, total=total)

    def __download(self) -> None:
        """Download videos"""
        # update progress bar
        # we have set done and total in __init_manager, so we don't reset channel_progress here
        self.progress_manager.overall_update(self.task, description='Overall Progress')

        for video in self.video_list:
            # skip if video is already downloaded or status is None (not selected)
            if self.channel_manager.get_status(str(video)) or self.channel_manager.get_status(str(video)) is None:
                continue

            session_id = self.api_client.get_session_id(video)

            if session_id is None:
                self.progress_manager.live.console.print(
                    f'Video [bold white]{video}[/bold white] not found or permission denied. Skip.', style='yellow')
                continue

            output_name, _ = self.api_client.get_video_name(video, self.channel_manager.get_title(str(video)))
            output = str(Path(self.output).joinpath(f'{output_name}'))

            m3u8_downloader = M3U8Downloader(self.api_client, self.progress_manager, session_id, output,
                                             self.target_resolution, self.channel_manager.continue_exists_video,
                                             self.transcode, self.ffmpeg, self.vcodec, self.acodec, self.ffmpeg_options,
                                             self.thread)
            if m3u8_downloader.start() and m3u8_downloader.done:
                self.channel_manager.set_status(str(video), True)
            else:
                self.progress_manager.live.console.print(f'Failed to download video [bold white]{video}[/bold white].',
                                                         style='yellow')
                continue

            self.progress_manager.overall_update(self.task, advance=1)


if __name__ == '__main__':
    raise RuntimeError('This file is not intended to be run as a standalone script.')
