import subprocess
from typing import Iterator
import re


class FFMPEG(object):
    """
    FFMPEG wrapper

    Args:
        ffmpeg (str, optional): ffmpeg path. Defaults to 'ffmpeg'.
    """
    def __init__(self, ffmpeg: str = 'ffmpeg') -> None:
        self.ffmpeg = ffmpeg
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
            subprocess.run([self.ffmpeg, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

    def run(self, _input: str, _output: str, vcodec: str, acodec: str, options: list) -> Iterator[float]:
        """Run ffmpeg command and yield progress"""
        if options is None:
            options = []

        self.cmd = [self.ffmpeg,
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

            line = self.process.stdout.readline().decode('utf-8', errors='replace').strip()

            if line != '':
                self.last_line = line

            if self.total_duration is None:
                total_dur_match = self.DUR_REGEX.search(line)
                if total_dur_match:
                    self.total_duration = int(total_dur_match.group('hour')) * 3600 + int(
                        total_dur_match.group('min')) * 60 + int(total_dur_match.group('sec'))
                else:
                    continue
            else:
                progress_time = self.TIME_REGEX.search(line)
                if progress_time:
                    progress = int(progress_time.group('hour')) * 3600 + int(progress_time.group('min')) * 60 + int(
                        progress_time.group('sec'))
                    yield progress / self.total_duration  # yield progress

        if self.process.poll() != 0:
            raise RuntimeError(f'Error while transcoding: {self.last_line}')
        else:
            yield None


if __name__ == '__main__':
    pass
