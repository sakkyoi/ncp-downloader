import sys

import click
from click import confirm
import typer
from typing_extensions import Annotated
from typing import Optional
from rich.console import Console
from urllib.parse import urlparse
from pathlib import Path

from api.api import NCP, ContentCode
from util.ffmpeg import FFMPEG
from util.m3u8_downloader import M3U8Downloader
from util.channel_downloader import ChannelDownloader


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
                help='ID (Video), Name (Channel) or URL(Both) to be queried.',
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
            Optional[bool],
            typer.Option(
                '--resume/--new', '-R/-N',
                show_default=False,
                help='Resume download.',
            ),
        ] = None,
        experimental: Annotated[
            Optional[bool],
            typer.Option(
                '--experimental/--normal', '-e/-ne',
                show_default=False,
                help='Experimental download method',
            ),
        ] = None,
        yes: Annotated[
            Optional[bool],
            typer.Option(
                '--yes/--no', '-y/-n',
                show_default=False,
                help='Skip confirmation.',
            ),
        ] = None,
        transcode: Annotated[
            bool,
            typer.Option(
                '--transcode/--direct', '-t',
                show_default=True,
                help='Transcode video.',
            ),
        ] = False,
        ffmpeg: Annotated[
            str,
            typer.Option(
                '--ffmpeg',
                help='Path to ffmpeg.',
            ),
        ] = 'ffmpeg',
        vcodec: Annotated[
            str,
            typer.Option(
                '--vcodec',
                help='Video codec for ffmpeg.',
            ),
        ] = 'copy',
        acodec: Annotated[
            str,
            typer.Option(
                '--acodec',
                help='Audio codec for ffmpeg.',
            ),
        ] = 'copy',
        ffmpeg_options: Annotated[
            FFMPEGOptions,
            typer.Option(
                '--ffmpeg-options',
                show_default=False,
                help='Options for ffmpeg.',
                click_type=FFMPEGOptions(),
            ),
        ] = None,
        thread: Annotated[
            int,
            typer.Option(
                '--thread',
                show_default=True,
                help='Number of threads.',
            ),
        ] = 1,
        username: Annotated[
            str,
            typer.Option(
                '--username',
                help='Username for login.',
            ),
        ] = None,
        password: Annotated[
            str,
            typer.Option(
                '--password',
                help='Password for login.',
            ),
        ] = None,
        debug: Annotated[
            bool,
            typer.Option(
                '--debug',
                show_default=False,
                help='Enable debugging.',
            ),
        ] = False,
) -> None:
    """The NCP Downloader"""
    err_console = Console(stderr=True)

    # nico
    nico = NCP(urlparse(query).netloc, username, password)

    try:
        # Check ffmpeg if transcode is enabled
        if transcode:
            if not FFMPEG(ffmpeg).check():
                raise FileNotFoundError('ffmpeg not found')

        # If yes is enabled, skip all confirmation
        if yes:
            experimental = resume = yes

        # tell user multithreading is dengerous
        if (thread > 1 and
                not confirm('Download with multithreading may got you banned from Server. Continue?', default=False)):
            raise RuntimeError('Aborted.')

        # Check if query is channel or video
        if nico.get_channel_id(query) is None:
            query = urlparse(query).path.strip('/').split('/')[-1]
            session_id = nico.get_session_id(ContentCode(query))

            # Check if video exists
            if session_id is None:
                raise ValueError('Video not found or permission denied.')

            output_name, _ = nico.get_video_name(ContentCode(query))

            output = str(Path(output).joinpath(output_name))

            M3U8Downloader(nico, session_id, output, resolution, resume, transcode,
                           ffmpeg, vcodec, acodec, ffmpeg_options, thread)
        else:
            if not yes:
                if not confirm('Sure to download whole channel?', default=True):
                    raise RuntimeError('Aborted.')

            if experimental is None:
                experimental = confirm('Using experimental download method?', default=True)

            # Get channel infomation
            channel_id = nico.get_channel_id(query)
            channel_name = nico.get_channel_info(channel_id)['fanclub_site_name']

            # Get video list
            if experimental:
                video_list = nico.list_videos_x(channel_id)
            else:
                video_list = nico.list_videos(channel_id)
                video_list = [ContentCode(video['content_code']) for video in video_list]

            output = str(Path(output).joinpath(channel_name))

            ChannelDownloader(nico, channel_id, video_list, output, resolution, resume,
                              transcode, ffmpeg, vcodec, acodec, ffmpeg_options, thread)
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
