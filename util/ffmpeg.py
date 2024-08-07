import subprocess
from typing import Iterator
import re
from typing import Optional


class FFMPEG(object):
    """
    FFMPEG wrapper

    Args:
        ffmpeg (str, optional): ffmpeg path. Defaults to 'ffmpeg'.
    """
    def __init__(self, ffmpeg: str = 'ffmpeg') -> None:
        self.ffmpeg_path = ffmpeg
        self.cmd = None
        self.process = None

        self.total_duration = None
        self.last_line = None

        self.DUR_REGEX = re.compile(
            r'Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})'
        )
        self.TIME_REGEX = re.compile(
            r'out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})'
        )

    def check(self) -> bool:
        """Check if ffmpeg is installed"""
        try:
            subprocess.run([self.ffmpeg_path, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

    def run(self, _input: str, _output: str, vcodec: str, acodec: str, options: list) -> Iterator[float]:
        """Run ffmpeg command and yield progress"""
        if options is None:
            options = []

        self.cmd = [self.ffmpeg_path,
                    '-progress', '-', '-nostats', '-y',
                    '-i', _input,
                    '-vcodec', vcodec,
                    '-acodec', acodec] + options + [_output]

        self.process = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        while self.process.poll() is None:
            if self.process.stdout is None:
                continue

            # read line from ffmpeg process
            line = self.__read_line()

            # trying to get total duration until it's found
            if self.total_duration is None:
                self.total_duration = self.__get_time(line, self.DUR_REGEX)
                continue

            progress_time = self.__get_time(line, self.TIME_REGEX)

            if progress_time:
                yield progress_time / self.total_duration  # return progress in percentage

        if self.process.poll() != 0:
            raise RuntimeError(f'Error while transcoding: {self.last_line}')
        else:
            yield None

    def __read_line(self) -> str:
        """Read line from ffmpeg process"""
        line = self.process.stdout.readline()
        line = line.decode('utf-8', errors='replace')
        line = line.strip()

        if line != '':
            self.last_line = line

        return line

    @staticmethod
    def __get_time(line: str, match: re.Pattern) -> Optional[int]:
        """Try to get current time from ffmpeg output"""
        time_match = match.search(line)

        if not time_match:
            return None

        hour = int(time_match.group('hour'))
        minute = int(time_match.group('min'))
        second = int(time_match.group('sec'))

        return hour * 3600 + minute * 60 + second


if __name__ == '__main__':
    raise RuntimeError('This file is not intended to be run as a standalone script.')
