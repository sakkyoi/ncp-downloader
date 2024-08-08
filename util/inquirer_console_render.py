from inquirer.render.console import ConsoleRender
from inquirer.render.console._checkbox import Checkbox
from inquirer.themes import term
import unicodedata
from readchar import key

_old_process_input = Checkbox.process_input  # save the original method


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


def process_input_checkbox(self, pressed):
    _old_process_input(self, pressed)

    if pressed == key.CTRL_W:
        try:
            video_filter(self)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(e)


def video_filter(self):
    f = input("Filter: ")
    # Clear the print that inquirer made
    print(self.terminal.move_up + self.terminal.clear_eol, end="")

    # check if the filter is a command
    if not f.startswith("/"):
        return

    f = f.split(" ")

    # check if the filter is valid
    if len(f) < 2:
        return

    command = f[0][1:]
    f = " ".join(f[1:])

    if command == "lambda":
        selection = filter(lambda x: eval(f),
                           [DotDict({
                               "index": index,
                               "content_code": code,
                               "title": self.question.hints[code]
                           }) for index, code in enumerate(self.question.choices)])

        selection = [x.index for x in selection]
    else:
        selection = [i for i, c in enumerate(self.question.choices) if
                     self.question.hints[c].lower().find(f.lower()) != -1]

        if command == "add":
            selection = list(set(self.selection + selection))
        elif command == "remove":
            selection = [i for i in self.selection if i not in selection]
        elif command == "only":
            selection = selection
        else:
            return

        # add the locked options back if it is removed
        selection = list(set(selection) | set([i for i, c in enumerate(self.question.choices) if c in self.locked]))

    self.selection = selection


class DotDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


ConsoleRender._print_options = _print_options  # override the method to print hints with options
ConsoleRender._print_hint = lambda self, render: None  # do not print the hint line
Checkbox.process_input = process_input_checkbox  # override the method to handle the input
