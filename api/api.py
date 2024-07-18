from typing import Optional, Tuple

import requests
import json
from urllib.parse import urlparse, urljoin
from datetime import datetime
from pathvalidate import sanitize_filename

from .auth import NCPAuth


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


class NCP(object):
    """
    The NCP API

    Args:
        site_base (str): site base
        username (str, optional): username. Defaults to None.
        password (str, optional): password. Defaults to None.
    """
    def __init__(self, site_base: str, username: Optional[str], password: Optional[str]) -> None:
        self.site_base = f'https://{site_base}'
        self.headers = {
            'Origin': self.site_base,
            'Fc_use_device': 'null'
        }

        # this api is used to get api_base_url, fanclub_site_id, platform_id
        self.api_settings = f'{self.site_base}/site/settings.json'
        self.api_base, self.fanclub_site_id, self.platform_id = self.__initial_api()

        # api_login: %s = fanclub_site_id
        # this api is used to get data.fanclub_site.auth0_web_client_id(client_id) &
        #                         data.fanclub_site.fanclub_group.auth0_domain(auth0_domain)
        self.api_login = f'{self.api_base}/fanclub_sites/%s/login'
        self.auth_base, self.auth_client_id = self.__initial_auth()

        # initial auth
        if username is not None and password is not None:
            self.auth = NCPAuth(username, password, site_base,
                                self.platform_id, self.auth_client_id, self.auth_base,
                                urlparse(self.api_base).netloc)
        else:
            self.auth = None

        # endpoints
        self.api_channels = f'{self.api_base}/content_providers/channels'
        self.api_channel_info = f'{self.api_base}/fanclub_sites/%s/page_base_info'  # channel_id
        self.api_video_page = f'{self.api_base}/video_pages/%s'  # content_code
        self.api_public_status = f'{self.api_base}/video_pages/%s/public_status'  # content_code
        self.api_session_id = f'{self.api_base}/video_pages/%s/session_ids'  # content_code
        self.api_video_list = f'{self.api_base}/fanclub_sites/%s/video_pages?vod_type=%d&page=%d&per_page=%d&sort=%s'
        self.api_views_comments = f'{self.api_base}/fanclub_sites/%s/views_comments'  # channel_id
        self.api_video_index = None  # this will be set when get_video_page is called

    def __initial_api(self) -> Tuple[str, str, str]:
        """Initial api base from settings"""
        req = requests.get(self.api_settings, headers=self.headers)
        resp = req.json()

        return resp['api_base_url'], resp['fanclub_site_id'], resp['platform_id']

    def __initial_auth(self) -> Tuple[str, str]:
        """Initial auth base from login api"""
        req = requests.get(self.api_login % self.fanclub_site_id, headers=self.headers)
        resp = req.json()

        return (resp['data']['fanclub_site']['fanclub_group']['auth0_domain'],
                resp['data']['fanclub_site']['auth0_web_client_id'])

    def get_channel_id(self, query: str) -> Optional[ChannelID]:
        """Get channel id from channel domain or name"""
        query = urlparse(query)

        if self.fanclub_site_id == '1':
            for channel in self.list_channels():
                if channel['domain'] == query.geturl().strip('/'):
                    return ChannelID(channel['id'])
        else:
            r = requests.get(urljoin(query.geturl(), './site/settings.json'))
            if r.status_code == 200 and r.headers['Content-Type'] == 'application/json':
                return ChannelID(r.json()['fanclub_site_id'])

        return None

    def get_channel_info(self, channel_id: ChannelID) -> dict:
        """Get channel info from channel id"""
        r = requests.get(self.api_channel_info % channel_id, headers=self.headers)
        return r.json()['data']['fanclub_site']

    def list_channels(self) -> list:
        """Get channel list"""
        r = requests.get(self.api_channels, headers=self.headers)
        return r.json()['data']['content_providers']

    def list_views_comments(self, channel_id: ChannelID) -> list:
        """Get count of views and comments of channel from channel id \n
        This api using different method to get video list \n
        This api can set specific video, like ?content_codes[]=xxxxxx&content_codes[]=xxxxxx&..., \
        but it's not implemented here"""
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
        """Get video list of channel from channel id by views and comments count list"""
        views_comments = self.list_views_comments(channel_id)
        return [ContentCode(video['content_code']) for video in views_comments]

    def list_lives(self, channel_id: str, live_type) -> list:
        """Get live list of channel from channel id"""
        # TODO: I'm lazy, and who cares about it?
        pass

    def get_session_id(self, content_code: ContentCode) -> Optional[SessionID]:
        """Get session id of video from content code"""
        r = requests.post(self.api_session_id % content_code,
                          headers=dict({'Content-Type': 'application/json'},
                                       **({'Authorization': f'Bearer {self.auth}'} if self.auth is not None else {}),
                                       **self.headers),
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
            return None  # if video is private, it will be error.

    def get_video_name(self, content_code: ContentCode, known_title: str = None,
                       _format: str = '%release_date% %title% [%content_code%]') -> Tuple[str, str]:
        """Get video name from content code"""
        video_page = self.get_video_page(content_code)
        self.api_video_index = video_page['video_stream']['authenticated_url'].replace('{session_id}', '%s')
        title = video_page['title'] if video_page is not None \
            else 'unknown' if known_title is None else known_title
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
                .replace('%content_code%', str(content_code)), 'unknown'


if __name__ == '__main__':
    raise Exception('This file is not meant to be executed')
