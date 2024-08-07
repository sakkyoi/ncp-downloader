from inquirer.render.console import ConsoleRender
from inquirer.themes import term
import unicodedata
from typing import Optional


def _print_options(self, render):
    for message, symbol, color in render.get_options():
        if hasattr(message, "decode"):  # python 2
            message = message.decode("utf-8")

        hint = make_hint(message, symbol, render, self.terminal.width)

        if not hint:
            f = " {color}{s} {m}{t.normal}"
        elif render.question.choices[render.current] == message:
            f = " {color}{s} {m} {h}{t.normal}"
        else:
            f = " {color}{s} {t.white}{m}{color} {h}{t.normal}"

        self.print_line(f, m=message, color=color, s=symbol, h=hint)


def count_string_width(string):
    """
    Count the width of a string. East Asian characters are counted as 2.
    """
    # W: Wide, F: Full-width, A: Ambiguous(maybe wide or narrow, depending on the context. consider as wide here)
    return sum(1 + (unicodedata.east_asian_width(c) in 'WFA') for c in string)


def make_hint(message, symbol, render, terminal_width):
    """
    Make a hint for the message.
    """
    # if there is no hint, return None
    if render.question.hints is None:
        return ""

    # get the hint for the message
    hint = render.question.hints.get(message, "")

    # calculate width
    symbol_width = count_string_width(symbol)
    message_width = count_string_width(message)
    hint_width = count_string_width(hint)
    space_width = 3  # space between symbol, message and hint
    # sometimes the last character will be truncated(just not shown),
    # so we need a buffer to ensure the hint is not truncated
    buffer_width = 1
    ellipsis_width = 3  # for the ellipsis("...")

    total_width = symbol_width + message_width + hint_width + space_width + buffer_width

    if message in render.locked:
        total_width += count_string_width(" (Done)")

    to_truncate = total_width - terminal_width + ellipsis_width

    # truncate the hint
    while to_truncate > 0:
        to_truncate -= count_string_width(hint[-1])
        hint = hint[:-1]

    # add the ellipsis if the hint is truncated
    if total_width > terminal_width:
        hint += "..."

    # add the "Done" hint if the message is locked(locked means the option is downloaded)
    if message in render.locked:
        hint += f"{term.bold_red} (Done)"

    return hint


ConsoleRender._print_options = _print_options  # override the method to print hints with options
ConsoleRender._print_hint = lambda self, render: None  # do not print the hint line
