from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn, BarColumn, MofNCompleteColumn, TaskID
from rich.console import Group
from rich.live import Live
from contextlib import contextmanager


class ProgressManager:
    def __init__(self) -> None:
        # This is for the overall progress
        self.overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        )
        # This is for the individual progress
        self.progress = Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            "Elapsed:",
            TimeElapsedColumn(),
        )
        # The rendering group
        # The overall progress is in the last one because we want to make it always visible
        self.group = Group(
            self.progress,
            self.overall_progress
        )
        self.live = Live(self.group, refresh_per_second=10)

    def add_overall_task(self, description: str, total: float | None = 100.0) -> TaskID:
        return self.overall_progress.add_task(description, total=total)

    def overall_reset(self, task: TaskID, description: str | None = None,
                      total: float | None = None, completed: float | None = None) -> None:
        self.overall_progress.reset(task)  # <--- completed here doesn't accept float
        self.overall_update(task, description=description, total=total, completed=completed)

    def overall_update(self, task: TaskID, description: str | None = None, total: float | None = None,
                       completed: float | None = None, advance: float | None = None) -> None:
        self.overall_progress.update(task, description=description, total=total, completed=completed, advance=advance)

    def add_task(self, description: str, total: float | None = 100.0) -> TaskID:
        return self.progress.add_task(description, total=total)

    def reset(self, task: TaskID, description: str | None = None,
              total: float | None = None, completed: float | None = None) -> None:
        self.progress.reset(task)  # <--- completed here doesn't accept float
        self.update(task, description=description, total=total, completed=completed)

    def update(self, task: TaskID, description: str | None = None,
               total: float | None = None, completed: float | None = None, advance: float | None = None) -> None:
        self.progress.update(task, description=description, total=total, completed=completed, advance=advance)

    def stop_task(self, task: TaskID) -> None:
        self.progress.stop_task(task)
        self.progress.update(task, visible=False)

    @contextmanager
    def pause(self):
        self.live.stop()  # <--- this stop the live rendering

        yield  # <--- this is where the code inside the with block run

        self.live.start()  # <--- this start the live rendering
        self.live.console.clear()  # <--- this clear the console after the rendering

    def __enter__(self):
        self.live.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.live.__exit__(exc_type, exc_val, exc_tb)


if __name__ == '__main__':
    raise RuntimeError('This file is not intended to be run as a standalone script.')
