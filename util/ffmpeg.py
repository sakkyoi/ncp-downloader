import subprocess
from typing import Iterator
import re


class FFMPEG:
    def __init__(self, _input: str, _output: str,
                 ffmpeg: str, vcodec: str, acodec: str) -> None:
        self.cmd = [ffmpeg,
                    '-progress', '-', '-nostats', '-y',
                    '-i', _input,
                    '-vcodec', vcodec,
                    '-acodec', acodec,
                    _output]
        self.process = None

        self.total_duration = None
        self.last_line = None

        self.DUR_REGEX = re.compile(
            r'Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})'
        )
        self.TIME_REGEX = re.compile(
            r'out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})'
        )

    def run(self) -> Iterator[float]:
        """Run ffmpeg command and yield progress"""
        self.process = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=False
        )

        while True:
            if self.process.stdout is None:
                continue

            if self.process.poll() is not None:
                if self.process.poll() != 0:
                    raise RuntimeError(f'Error while transcoding: {self.last_line}')
                else:
                    yield 999

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


if __name__ == '__main__':
    pass
