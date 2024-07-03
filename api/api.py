from typing import Optional, Tuple

import requests
import json
from urllib.parse import urlparse, urljoin
from datetime import datetime
from pathvalidate import sanitize_filename


class SessionID(object):
    """Session id of video"""
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    def __repr__(self) -> str:
        return str(self.session_id)


class ChannelID(object):
    """Channel id of channel"""
    def __init__(self, channel_id: str or int) -> None:
        self.channel_id = channel_id

    def __repr__(self) -> str:
        return str(self.channel_id)


class ContentCode(object):
    """Content code of video"""
    def __init__(self, content_code: str) -> None:
        self.content_code = content_code

    def __repr__(self) -> str:
        return str(self.content_code)


class NicoChannelPlus:
    """Nico Channel Plus API"""
    def __init__(self, headers=None) -> None:
        if headers is None:
            headers = {
                'Origin': 'https://nicochannel.jp',
                'Fc_use_device': 'null'
            }
        self.headers = headers

        self.api_base = 'https://api.nicochannel.jp/fc'
        self.api_channels = f'{self.api_base}/content_providers/channels'
        self.api_channel_info = f'{self.api_base}/fanclub_sites/%s/page_base_info'  # channel_id
        self.api_video_page = f'{self.api_base}/video_pages/%s'  # content_code
        self.api_public_status = f'{self.api_base}/video_pages/%s/public_status'  # content_code
        self.api_session_id = f'{self.api_base}/video_pages/%s/session_ids'  # content_code
        self.api_video_list = f'{self.api_base}/fanclub_sites/%s/video_pages?vod_type=%d&page=%d&per_page=%d&sort=%s'
        self.api_views_comments = f'{self.api_base}/fanclub_sites/%s/views_comments'  # channel_id

        self.api_video_index = 'https://hls-auth.cloud.stream.co.jp/auth/index.m3u8?session_id=%s'

    def get_channel_id(self, query: str) -> Optional[ChannelID]:
        """Get channel id from channel domain or name"""
        query = urlparse(query)

        if query.netloc == '':
            query = urlparse(urljoin('https://nicochannel.jp/', query.path.strip('/')))

        if query.netloc == 'nicochannel.jp':
            for channel in self.list_channels():
                if channel['domain'] == query.geturl().strip('/'):
                    return ChannelID(channel['id'])
        else:
            r = requests.get(urljoin(query.geturl(), './site/settings.json'))
            if r.status_code == 200 and r.headers['Content-Type'] == 'application/json':
                return ChannelID(r.json()['fanclub_site_id'])
            else:
                return None

    def get_channel_info(self, channel_id: ChannelID) -> dict:
        """Get channel info from channel id"""
        r = requests.get(self.api_channel_info % channel_id, headers=self.headers)
        return r.json()['data']['fanclub_site']

    def list_channels(self) -> list:
        """Get channel list"""
        r = requests.get(self.api_channels, headers=self.headers)
        print(r)
        return r.json()['data']['content_providers']

    def list_views_comments(self, channel_id: ChannelID) -> list:
        """Get count of views and comments of channel from channel id \n
        This api returns all the videos, *EVEN IF THE VIDEO IS PRIVATE* \n
        TODO: This api can set specific video, like ?content_codes[]=xxxxxx&content_codes[]=xxxxxx&..."""
        r = requests.get(self.api_views_comments % channel_id, headers=self.headers)
        return r.json()['data']['video_aggregate_infos']

    def list_videos(self,
                    channel_id: ChannelID,
                    vod_type: int = 0,
                    page: int = 1,
                    per_page: int = 12,
                    sort: str = '-display_date') -> list:
        """Get video list of channel from channel id"""
        r = requests.get(self.api_video_list % (channel_id, vod_type, page, per_page, sort), headers=self.headers)
        video_list = r.json()['data']['video_pages']['list']
        if len(r.json()['data']['video_pages']['list']) < r.json()['data']['video_pages']['total']:
            while len(video_list) < r.json()['data']['video_pages']['total']:
                page += 1
                r = requests.get(self.api_video_list % (channel_id, vod_type, page, per_page, sort),
                                 headers=self.headers)
                video_list += r.json()['data']['video_pages']['list']
        return video_list

    def list_videos_x(self, channel_id: ChannelID) -> list:
        """Get video list of channel from channel id by views and comments count list (should include private video)"""
        views_comments = self.list_views_comments(channel_id)
        return [ContentCode(video['content_code']) for video in views_comments]

    def list_lives(self, channel_id: str, live_type) -> list:
        """Get live list of channel from channel id"""
        # TODO: I'm lazy, and who cares about it?
        pass

    def get_session_id(self, content_code: ContentCode) -> Optional[SessionID]:
        """Get session id of video from content code"""
        r = requests.post(self.api_session_id % content_code,
                          headers=dict({'Content-Type': 'application/json'}, **self.headers),
                          data=json.dumps({}))
        if r.status_code == 200:
            return SessionID(r.json()['data']['session_id'])
        else:
            return None

    def get_public_status(self, content_code: ContentCode) -> dict:
        """Get public status of video from content code"""
        r = requests.get(self.api_public_status % content_code, headers=self.headers)
        return r.json()['data']['video_page']

    def get_video_page(self, content_code: ContentCode) -> Optional[dict]:
        """Get video page of video from content code"""
        r = requests.get(self.api_video_page % content_code, headers=self.headers)
        if r.status_code == 200:
            return r.json()['data']['video_page']
        else:
            return None  # if video is private, it will be error. (video still can be downloaded)

    def get_video_name(self, content_code: ContentCode, known_title: str = None,
                       _format: str = '%release_date% %title% [%content_code%]') -> Tuple[str, str]:
        """Get video name from content code"""
        video_page = self.get_video_page(content_code)
        title = video_page['title'] if video_page is not None \
            else 'private' if known_title is None else known_title
        title = sanitize_filename(title, '_')  # sanitize filename

        if video_page is not None:
            release_at = datetime.strptime(video_page['released_at'], '%Y-%m-%d %H:%M:%S')
            return _format.replace('%release_date%', release_at.strftime('%Y-%m-%d')) \
                .replace('%title%', title) \
                .replace('%content_code%', str(content_code)), video_page['title']
        else:
            public_status = self.get_public_status(content_code)
            release_at = datetime.strptime(public_status['released_at'], '%Y-%m-%d %H:%M:%S')
            return _format.replace('%release_date%', release_at.strftime('%Y-%m-%d')) \
                .replace('%title%', title) \
                .replace('%content_code%', str(content_code)), 'private'  # TODO: fix private video title


if __name__ == '__main__':
    raise Exception('This file is not meant to be executed')
