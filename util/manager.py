import pathlib
from typing import Tuple

from m3u8 import model
from tinydb import TinyDB, Query
import pickle
import inquirer
from inquirer.themes import term
from rich.progress import TaskID
from rich.panel import Panel
from api.api import NCP
import time

from util.progress import ProgressManager


class M3U8Manager(object):
    def __init__(self, output: str, resume: bool = None):
        self.output = pathlib.Path(output)
        self.resume = resume
        self.temp = self.output.parent.joinpath(f'temp_{self.output.stem}')
        self.segment_db_path = self.output.parent.joinpath(f'temp_{self.output.stem}/{self.output.stem}.pickle')

        self.segment_db = None

        if not self.output.parent.exists():
            self.output.parent.mkdir(parents=True)
        if not self.temp.exists():
            self.temp.mkdir()

    def init_manager(self, segment_list: model.SegmentList) -> float:
        if self.resume is None and self.segment_db_path.exists():
            questions = [
                inquirer.List('resume', message='Found existing task, do you want to continue?',
                              choices=['Yes', 'No'], default='Yes')
            ]
            answer = inquirer.prompt(questions)['resume']
            self.resume = True if answer == 'Yes' else False

        # resume download
        if self.segment_db_path.exists() and self.resume:
            # load the list of segment status
            db = pickle.load(open(self.segment_db_path, 'rb'))
        # new download
        else:
            if self.temp.exists():
                self.remove_temp(False)

            # tell user not to touch files in temp folder
            if not self.temp.joinpath('__DO NOT TOUCH FILES HERE__').exists():
                self.temp.joinpath('__DO NOT TOUCH FILES HERE__').mkdir()

            # initial the list of segment status
            db = [False] * len(segment_list)
            # dump the list to pickle file
            pickle.dump(db, open(self.segment_db_path, 'wb'))

        # set the segment_db
        self.segment_db = db

        return sum(self.segment_db) / len(segment_list)

    def get_status(self, segment_id: int) -> bool:
        return self.segment_db[segment_id]

    def set_status(self, segment_id: int, status: bool) -> None:
        self.segment_db[segment_id] = status
        pickle.dump(self.segment_db, open(self.segment_db_path, 'wb'))

    def remove_temp(self, remove_self: bool = True) -> None:
        for sub in self.temp.iterdir():
            if sub.is_dir():
                for file in sub.iterdir():
                    file.unlink()
                sub.rmdir()
            else:
                sub.unlink()
        self.temp.rmdir() if remove_self else None


class ChannelManager(object):
    def __init__(self, api_client: NCP, output: str, select_manually: bool, wait, resume):
        self.api_client = api_client
        self.output = pathlib.Path(output)
        self.select_manually = select_manually
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

    def init_manager(self, video_list: list, progress_manager: ProgressManager, task: TaskID) -> Tuple[int, int]:
        if self.resume is None and self.channel_db_path.exists():
            with progress_manager.pause():
                answer = inquirer.prompt([
                    inquirer.List('resume', message='Found existing task, do you want to continue?',
                                  choices=['Yes', 'No'], default='Yes'),
                    inquirer.List('continue', message='Continue existing videos task?',
                                  choices=['Yes', 'No'], default='Yes')
                ], raise_keyboard_interrupt=True)
                self.resume = True if answer['resume'] == 'Yes' else False
                self.continue_exists_video = True if answer['continue'] == 'Yes' else False
        else:
            self.continue_exists_video = True if self.resume else False

        count_new = 0

        progress_manager.overall_update(task, total=len(video_list))
        if self.channel_db_path.exists() and self.resume:
            db = TinyDB(self.channel_db_path)

            for video in video_list:
                if not db.contains(Query().id == str(video)):
                    _, title = self.api_client.get_video_name(video)
                    db.insert({
                        'id': str(video),
                        'title': title,
                        'done': False
                    })
                    count_new += 1
                    time.sleep(self.wait)  # don't spam the server
                progress_manager.overall_update(task, advance=1)
        else:
            if self.channel_db_path.exists():
                self.remove_temp(False)

            db = TinyDB(self.channel_db_path)

            for video in video_list:
                _, title = self.api_client.get_video_name(video)
                db.insert({
                    'id': str(video),
                    'title': title,
                    'done': False
                })
                time.sleep(self.wait)  # don't spam the server
                progress_manager.overall_update(task, advance=1)

            count_new = len(video_list)
        progress_manager.overall_update(task, description='done!')

        if self.select_manually:
            # select videos to download
            with progress_manager.pause():
                locked = [video['id'] for video in db.search(Query().done == True)]
                hints = {
                    video['id']: f'{video['title']}'
                                 f'{term.bold_red}{" (Done)" if video['done'] else ""}'
                    for video in db.all()}
                choices = [f'{video['id']}' for video in db.all()]
                default = [video['id'] for video in db.search(Query().done != None)]

                selected = inquirer.prompt([
                    inquirer.Checkbox('videos', message='Select videos to download',
                                      locked=locked,
                                      hints=hints,
                                      choices=choices,
                                      default=default)
                ], raise_keyboard_interrupt=True)['videos']

            # set unselected videos to None(skip)
            for video in set(choices) - set(selected):
                db.update({'done': None}, Query().id == video)

            # set selected videos to False(not done)
            for video in set(selected) - set(default):
                db.update({'done': False}, Query().id == video)
        else:
            selected = [video['id'] for video in db.search(Query().done != None)]
            if len(selected) != len(video_list):
                progress_manager.live.console.print('Warning: not all videos are selected. '
                                                    '(use --select-manually to select manually)', style='yellow')

        progress_manager.live.console.print(
            Panel(f'Found {len(video_list)} videos, {count_new} new videos added, '
                  f'{sum(1 for _ in selected)} videos selected.',
                  title='Info'))

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
