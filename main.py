import argparse

from api.api import NicoChannelPlus, ContentCode
from click import confirm
from urllib.parse import urlparse
from util.m3u8_downloader import M3U8Downloader
from util.channel_downloader import ChannelDownloader
from util.ffmpeg import FFMPEG
from sys import exit


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='')
    parser.add_argument('-o', '--output', help='output directory', default='output')
    parser.add_argument('-r', '--resolution', help='target resolution', default='1920x1080')
    parser.add_argument('-c', '--continue_all', help='continue download', action='store_true')
    parser.add_argument('-p', '--private', help='download private videos (channel only)', action='store_true')
    parser.add_argument('-y', '--yes', help='skip all confirmation', action='store_true')
    parser.add_argument('-t', '--transcode', help='transcode to mp4', action='store_true')
    parser.add_argument('-vcodec', help='video codec', default='copy')
    parser.add_argument('-acodec', help='audio codec', default='copy')
    parser.add_argument('-ffmpeg', help='ffmpeg path', default='ffmpeg')
    parser.add_argument('--ffmpeg-options', help='ffmpeg options', default='')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0.0')
    args = parser.parse_args()

    query = args.input
    output_dir = args.output
    continue_all = args.continue_all
    private = args.private
    yes = args.yes
    transcode = args.transcode
    vcodec = args.vcodec
    acodec = args.acodec
    ffmpeg = args.ffmpeg
    ffmpeg_options = args.ffmpeg_options
    if ffmpeg_options != '':
        ffmpeg_options = ffmpeg_options.split(' ')
    else:
        ffmpeg_options = []

    try:
        target_resolution = tuple(map(int, args.resolution.split('x')))
        if len(target_resolution) != 2:
            raise ValueError
    except ValueError:
        print('Invalid resolution, get highest resolution')
        target_resolution = None

    if transcode:
        if not FFMPEG(ffmpeg).check():
            raise FileNotFoundError('ffmpeg not found')

    try:
        nico = NicoChannelPlus()
        if nico.get_channel_id(query) is None:
            query = urlparse(query).path.strip('/').split('/')[-1]
            session_id = nico.get_session_id(ContentCode(query))

            if session_id is None:
                raise ValueError('Video not found')

            output_name, _ = nico.get_video_name(ContentCode(query))

            M3U8Downloader(session_id,
                           f'{output_dir}/{output_name}',
                           (1920, 1080),
                           _continue=True if continue_all or yes else None, transcode=transcode,
                           ffmpeg=ffmpeg, acodec=acodec, vcodec=vcodec, ffmpeg_options=ffmpeg_options)
        else:
            if not private and yes:
                private = yes

            check_download = yes
            if not yes:
                check_download = confirm('Download whole channel?', default=True)
                if not check_download:
                    exit(0)

            if not private:
                private = confirm('Do you want to download private videos?', default=False)

            if check_download:
                channel_id = nico.get_channel_id(query)
                channel_info = nico.get_channel_info(channel_id)
                if private:
                    video_list = nico.list_videos_x(channel_id)
                else:
                    video_list = nico.list_videos(channel_id)
                    video_list = [ContentCode(video['content_code']) for video in video_list]
                ChannelDownloader(channel_id, video_list, output=f'{output_dir}/{channel_info["fanclub_site_name"]}',
                                  target_resolution=target_resolution, _continue=continue_all or yes or None,
                                  transcode=transcode, ffmpeg=ffmpeg, acodec=acodec, vcodec=vcodec,
                                  ffmpeg_options=ffmpeg_options)
    except KeyboardInterrupt:
        exit(0)
    except Exception as e:
        print(e)
        exit(1)
