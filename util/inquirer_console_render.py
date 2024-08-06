from inquirer.render.console import ConsoleRender
from inquirer.themes import term
import unicodedata


def _print_options(self, render):
    for message, symbol, color in render.get_options():
        if hasattr(message, "decode"):  # python 2
            message = message.decode("utf-8")

        hint = ""
        if render.question.hints is not None:
            hint = render.question.hints.get(message, "")

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

            if total_width > self.terminal.width:
                # calculate how many characters to truncate
                to_truncate = total_width - self.terminal.width + ellipsis_width

                # truncate the hint
                while to_truncate > 0:
                    to_truncate -= count_string_width(hint[-1])
                    hint = hint[:-1]

                hint += "..."

            if message in render.locked:
                hint += f"{term.bold_red} (Done)"

        if hint:
            f = " {color}{s} {m} {h}{t.normal}" if render.question.choices[render.current] == message \
                else " {color}{s} {t.white}{m}{color} {h}{t.normal}"
            self.print_line(f, m=message, color=color, s=symbol, h=hint)
        else:
            self.print_line(" {color}{s} {m}{t.normal}", m=message, color=color, s=symbol)


def count_string_width(string):
    """
    Count the width of a string. East Asian characters are counted as 2.
    """
    # W: Wide, F: Full-width, A: Ambiguous(may be wide or narrow, depending on the context. consider as wide here)
    return sum(1 + (unicodedata.east_asian_width(c) in 'WFA') for c in string)


ConsoleRender._print_options = _print_options  # override the method to print hints with options
ConsoleRender._print_hint = lambda self, render: None  # do not print the hint line
