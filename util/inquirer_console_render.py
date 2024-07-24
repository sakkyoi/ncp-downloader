from inquirer.render.console import ConsoleRender


def _print_options(self, render):
    for message, symbol, color in render.get_options():
        if hasattr(message, "decode"):  # python 2
            message = message.decode("utf-8")

        hint = ""
        if render.question.hints is not None:
            hint = render.question.hints.get(message, "")

        if hint:
            f = " {color}{s} {m} {h}{t.normal}" if render.question.choices[render.current] == message \
                else " {color}{s} {t.white}{m}{color} {h}{t.normal}"
            self.print_line(f, m=message, color=color, s=symbol, h=hint)
        else:
            self.print_line(" {color}{s} {m}{t.normal}", m=message, color=color, s=symbol)


ConsoleRender._print_options = _print_options  # override the method to print hints with options
ConsoleRender._print_hint = lambda self, render: None  # do not print the hint line
