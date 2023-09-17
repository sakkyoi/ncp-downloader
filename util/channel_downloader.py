from api.api import NicoChannelPlus, ChannelID
from util.m3u8_downloader import M3U8Downloader
from util.manager import ChannelManager


class ChannelDownloader:
    def __init__(self, channel_id: ChannelID, video_list: list, output: str = 'output',
                 target_resolution: tuple = None, wait: float = 1,
                 _continue: bool = None, transcode: bool = None, ffmpeg: str = 'ffmpeg',
                 acodec: str = 'copy', vcodec: str = 'copy', ffmpeg_options: list = None) -> None:
        self.nico = NicoChannelPlus()
        self.channel_id = channel_id
        self.video_list = video_list
        self.output = output
        self.target_resolution = target_resolution
        self.wait = wait
        self._continue = _continue
        self.transcode = transcode
        self.ffmpeg = ffmpeg
        self.acodec = acodec
        self.vcodec = vcodec
        self.ffmpeg_options = ffmpeg_options

        self.ChannelManager = ChannelManager(self.output, wait=self.wait, _continue=self._continue)

        self.tip = None

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
            output_name, _ = self.nico.get_video_name(video, self.ChannelManager.get_title(str(video)))
            m3u8_downloader = M3U8Downloader(session_id, f'{self.output}/{output_name}', self.target_resolution,
                                             _continue=self.ChannelManager.continue_exists_video,
                                             transcode=self.transcode, ffmpeg=self.ffmpeg,
                                             acodec=self.acodec, vcodec=self.vcodec, ffmpeg_options=self.ffmpeg_options,
                                             tip=f'({self.done+1}/{self.total})')
            if m3u8_downloader.done:
                self.ChannelManager.set_status(str(video), True)
                self.done += 1


if __name__ == '__main__':
    pass
