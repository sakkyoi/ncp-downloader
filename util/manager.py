import pathlib
from typing import Tuple

from m3u8 import model
from tinydb import TinyDB, Query
from click import confirm
from api.api import NCP
import time
from alive_progress import alive_bar


class M3U8Manager(object):
    def __init__(self, output: str, resume: bool = None):
        self.output = pathlib.Path(output)
        self.resume = resume
        self.temp = self.output.parent.joinpath(f'temp_{self.output.stem}')
        self.segment_db_path = self.output.parent.joinpath(f'temp_{self.output.stem}/{self.output.stem}.json')

        self.segment_db = None

        if not self.output.parent.exists():
            self.output.parent.mkdir(parents=True)
        if not self.temp.exists():
            self.temp.mkdir()

    def init_manager(self, segment_list: model.SegmentList) -> float:
        if self.resume is None and self.segment_db_path.exists():
            self.resume = confirm('Found existing task, do you want to continue?', default=True)
        if self.segment_db_path.exists() and self.resume:
            db = TinyDB(self.segment_db_path)
        else:
            if self.temp.exists():
                self.remove_temp(False)

            # tell user not to touch files in temp folder
            if not self.temp.joinpath('__DO NOT TOUCH FILES HERE__').exists():
                self.temp.joinpath('__DO NOT TOUCH FILES HERE__').mkdir()

            db = TinyDB(self.segment_db_path)
            for segment in segment_list:
                db.insert({
                    'id': segment_list.index(segment),
                    'done': False
                })

        self.segment_db = db

        return len(self.segment_db.search(Query().done == True)) / len(segment_list)

    def get_status(self, segment_id: int) -> bool:
        return self.segment_db.get(Query().id == segment_id)['done']

    def set_status(self, segment_id: int, status: bool) -> None:
        self.segment_db.update({'done': status}, Query().id == segment_id)

    def remove_temp(self, remove_self: bool = True) -> None:
        self.segment_db.close() if remove_self else None  # close db before removing temp folder
        for sub in self.temp.iterdir():
            if sub.is_dir():
                for file in sub.iterdir():
                    file.unlink()
                sub.rmdir()
            else:
                sub.unlink()
        self.temp.rmdir() if remove_self else None


class ChannelManager(object):
    def __init__(self, nico: NCP, output: str, wait: float = 1, resume: bool = None):
        self.nico = nico
        self.output = pathlib.Path(output)
        self.wait = wait
        self.resume = resume
        self.temp = self.output.parent.joinpath('temp')
        self.channel_db_path = self.temp.joinpath(f'{self.output.stem}.json')

        self.channel_db = None

        self.continue_exists_video = None

        if not self.output.parent.exists():
            self.output.parent.mkdir(parents=True)
        if not self.temp.exists():
            self.temp.mkdir()

    def init_manager(self, video_list: list) -> Tuple[int, int]:
        if self.resume is None and self.channel_db_path.exists():
            self.resume = confirm('Found existing task, do you want to continue?', default=True)
            self.continue_exists_video = confirm('Continue existing videos task?', default=True)
        else:
            self.continue_exists_video = True if self.resume else False

        if self.channel_db_path.exists() and self.resume:
            db = TinyDB(self.channel_db_path)
            count_new = 0
            with alive_bar(len(video_list), force_tty=True) as bar:
                bar.title('Initializing')
                for video in video_list:
                    if not db.contains(Query().id == str(video)):
                        _, title = self.nico.get_video_name(video)
                        db.insert({
                            'id': str(video),
                            'title': title,
                            'done': False
                        })
                        count_new += 1
                        time.sleep(self.wait)  # don't spam the server
                    bar()
                bar.title('done!')

            print(f'Found {len(video_list)} videos, {count_new} new videos added')
        else:
            if self.channel_db_path.exists():
                self.remove_temp(False)

            db = TinyDB(self.channel_db_path)
            with alive_bar(len(video_list), force_tty=True) as bar:
                bar.title('Initializing')
                for video in video_list:
                    _, title = self.nico.get_video_name(video)
                    db.insert({
                        'id': str(video),
                        'title': title,
                        'done': False
                    })
                    time.sleep(self.wait)  # don't spam the server
                    bar()
                bar.title('done!')

            print(f'Found {len(video_list)} videos, {len(video_list)} new videos added')

        self.channel_db = db

        return len(self.channel_db.search(Query().done == True)), len(video_list)

    def get_title(self, content_code: str) -> str:
        return self.channel_db.get(Query().id == content_code)['title']

    def get_status(self, content_code: str) -> bool:
        return self.channel_db.get(Query().id == content_code)['done']

    def set_status(self, content_code: str, status: bool) -> None:
        self.channel_db.update({'done': status}, Query().id == content_code)

    def remove_temp(self, remove_self: bool = True) -> None:
        self.channel_db.close() if remove_self else None  # close db before removing temp folder
        self.channel_db_path.unlink()


if __name__ == '__main__':
    pass
