import sys

import click
from click import confirm
import typer
from typing_extensions import Annotated
from rich.console import Console
from urllib.parse import urlparse
from pathlib import Path

from api.api import NicoChannelPlus, ContentCode
from util.ffmpeg import FFMPEG
from util.m3u8_downloader import M3U8Downloader
from util.channel_downloader import ChannelDownloader
from util.manager import ChannelManager


class Resolution(click.ParamType):
    name = 'Resolution'

    def convert(self, value, param, ctx):
        try:
            resolution = tuple(map(int, value.split('x')))
            if len(resolution) != 2:
                raise ValueError
            return resolution
        except ValueError:
            self.fail(f'Invalid resolution: {value}.', param, ctx)


class FFMPEGOptions(click.ParamType):
    name = 'FFMPEG Options'

    def __init__(self):
        self.options = []

    def __len__(self):
        return len(self.options)

    def convert(self, value, param, ctx):
        self.options = value.split(' ')
        return self.options


def main(
        query: Annotated[
            str,
            typer.Argument(
                help='URL or channel name to be queried.',
            )
        ],
        output: Annotated[
            str,
            typer.Argument(
                help='Output directory.',
            ),
        ] = 'output',
        resolution: Annotated[
            Resolution,
            typer.Option(
                '--resolution', '-r',
                help='Target resolution. Defaults to highest resolution.',
                click_type=Resolution(),
            ),
        ] = None,
        resume: Annotated[
            bool,
            typer.Option(
                '--resume', '-R',
                help='Resume download.',
            ),
        ] = None,
        private: Annotated[
            bool,
            typer.Option(
                '--private', '-p',
                help='Download private videos.',
            ),
        ] = None,
        yes: Annotated[
            bool,
            typer.Option(
                '--yes', '-y',
                help='Skip confirmation.',
            ),
        ] = None,
        transcode: Annotated[
            bool,
            typer.Option(
                '--transcode', '-t',
                help='Transcode video.',
            ),
        ] = False,
        ffmpeg: Annotated[
            str,
            typer.Option(
                '--ffmpeg', '-ffmpeg',
                help='Path to ffmpeg.',
            ),
        ] = 'ffmpeg',
        vcodec: Annotated[
            str,
            typer.Option(
                '--vcodec', '-vcodec',
                help='Video codec for ffmpeg.',
            ),
        ] = 'copy',
        acodec: Annotated[
            str,
            typer.Option(
                '--acodec', '-acodec',
                help='Audio codec for ffmpeg.',
            ),
        ] = 'copy',
        ffmpeg_options: Annotated[
            FFMPEGOptions,
            typer.Option(
                '--ffmpeg-options', '-ffmpeg-options',
                help='Options for ffmpeg.',
                click_type=FFMPEGOptions(),
            ),
        ] = None,
        debug: Annotated[
            bool,
            typer.Option(
                help='Enable debugging.',
            ),
        ] = False,
) -> None:
    """Nico Channel Plus Downloader"""
    err_console = Console(stderr=True)
    try:
        # Check ffmpeg if transcode is enabled
        if transcode:
            if not FFMPEG(ffmpeg).check():
                raise FileNotFoundError('ffmpeg not found')

        # If yes is enabled, skip all confirmation
        if yes:
            private = resume = yes

        nico = NicoChannelPlus()

        # Check if query is channel or video
        if nico.get_channel_id(query) is None:
            query = urlparse(query).path.strip('/').split('/')[-1]
            session_id = nico.get_session_id(ContentCode(query))

            # Check if video exists
            if session_id is None:
                raise ValueError('Video not found')

            output_name, _ = nico.get_video_name(ContentCode(query))

            output = str(Path(output).joinpath(output_name))

            M3U8Downloader(session_id, output, resolution, resume, transcode, ffmpeg, vcodec, acodec, ffmpeg_options)
        else:
            if not yes:
                if not confirm('Sure to download whole channel?', default=True):
                    raise RuntimeError('Aborted.')

            if private is None:
                private = confirm('Download private videos?', default=True)

            # Get channel infomation
            channel_id = nico.get_channel_id(query)
            channel_name = nico.get_channel_info(channel_id)["fanclub_site_name"]

            # Get video list
            if private:
                video_list = nico.list_videos_x(channel_id)
            else:
                video_list = nico.list_videos(channel_id)
                video_list = [ContentCode(video['content_code']) for video in video_list]

            output = str(Path(output).joinpath(channel_name))

            ChannelDownloader(channel_id, video_list, output, resolution, resume,
                              transcode, ffmpeg, vcodec, acodec, ffmpeg_options)
    except Exception as e:
        # Raise exception again if debug is enabled
        if debug:
            raise e
        # Print error message and exit if debug is disabled
        else:
            err_console.print(f'[red]{e}[/red]')
            sys.exit(1)


if __name__ == "__main__":
    typer.run(main)
