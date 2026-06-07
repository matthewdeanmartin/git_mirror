from rich.console import Console
from rich.theme import Theme

console = None


def console_with_theme() -> Console:
    """Factory to allow for app theming."""
    global console
    if console is None:
        custom_theme = Theme({"info": "dim cyan", "warning": "magenta", "danger": "bold red"})
        console = Console(theme=custom_theme)
    return console
