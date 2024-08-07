import sys
import platform

import click
import inquirer
import typer
from typing_extensions import Annotated
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path
import pylibimport

from api.api import NCP, ContentCode
from util.ffmpeg import FFMPEG
from util.m3u8_downloader import M3U8Downloader
from util.channel_downloader import ChannelDownloader
from util.progress import ProgressManager

__import__('util.inquirer_console_render')  # hook for inquirer console render


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
                help='URL to be queried.',
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
                help='Number of threads. Be careful with this option.',
            ),
        ] = 1,
        select_manually: Annotated[
            bool,
            typer.Option(
                '--select-manually',
                show_default=False,
                help='Select which video to download manually. This option only works with channel.',
            ),
        ] = False,
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
    api_client = NCP(urlparse(query).netloc, username, password)
    progress_manager = ProgressManager()

    try:
        # Check ffmpeg if transcode is enabled
        if transcode and not FFMPEG(ffmpeg).check():
            raise FileNotFoundError('ffmpeg not found')

        # If yes is enabled, skip all confirmation
        if yes:
            resume = yes

        # tell user multithreading is dengerous
        # can not be skipped by --yes
        if thread > 1:
            with progress_manager.pause():
                if inquirer.prompt([inquirer.List('thread',
                                                  message='Multithreading is dangerous, are you sure to continue?',
                                                  choices=['Yes', 'No'], default='No')],
                                   raise_keyboard_interrupt=True)['thread'] == 'No':
                    raise RuntimeError('Aborted.')

        # Check if query is channel or video
        if api_client.get_channel_id(query) is None:
            query = urlparse(query).path.strip('/').split('/')[-1]
            session_id = api_client.get_session_id(ContentCode(query))

            # Check if video exists
            if session_id is None:
                raise ValueError('Video not found or permission denied.')

            output_name, _ = api_client.get_video_name(ContentCode(query))

            output = str(Path(output).joinpath(output_name))

            with progress_manager:
                m3u8_downloader = M3U8Downloader(api_client, progress_manager, session_id, output, resolution, resume,
                                                 transcode, ffmpeg, vcodec, acodec, ffmpeg_options, thread)
                if not m3u8_downloader.start():
                    raise RuntimeError('Failed to download video.')
        else:
            # warning for downloading whole channel if --yes is not set
            if not yes:
                with progress_manager.pause():
                    if inquirer.prompt([
                        inquirer.List('channel', message='Sure to download whole channel?',
                                      choices=['Sure', 'No'], default='No')
                    ], raise_keyboard_interrupt=True)['channel'] == 'No':
                        raise RuntimeError('Aborted.')

            # Get channel infomation
            channel_id = api_client.get_channel_id(query)
            channel_name = api_client.get_channel_info(channel_id)['fanclub_site_name']

            # Get video list
            video_list = api_client.list_videos(channel_id)
            video_list = [ContentCode(video['content_code']) for video in video_list]

            output = str(Path(output).joinpath(channel_name))

            with progress_manager:
                channel_downloader = ChannelDownloader(api_client, progress_manager, channel_id, video_list, output,
                                                       resolution, resume,
                                                       transcode, ffmpeg, vcodec, acodec, ffmpeg_options,
                                                       thread, select_manually)
                channel_downloader.start()
    except Exception as e:
        # Raise exception again if debug is enabled
        if debug:
            raise e
        # Print error message and exit if debug is disabled
        else:
            progress_manager.live.console.print(f'{e}', style='red')
            sys.exit(1)


if __name__ == "__main__":
    # find all the .pyd(win) or .so(linux and macos), files in the current directory
    if platform.system() == 'Windows':
        pyds = Path('.').glob('*.pyd')
    elif platform.system() == 'Linux' or platform.system() == 'Darwin':
        pyds = Path('.').glob('*.so')
    else:
        raise RuntimeError('Unsupported platform')

    # import all the .pyd or .so files
    for pyd in pyds:
        pylibimport.import_module(pyd.stem)

    typer.run(main)
