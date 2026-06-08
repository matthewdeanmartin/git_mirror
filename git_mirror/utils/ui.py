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


#: core classification tag ("ok"/"warn"/"error"/"dim") -> Rich colour/style.
#: The single mapping every Rich-based renderer shares, so the semantic
#: decision lives in core and only the colour lives here.
RICH_TAG_STYLE = {"ok": "green", "warn": "yellow", "error": "red", "dim": "dim"}


def rich_markup(tag: str, text: str) -> str:
    """Wrap text in the Rich colour for a core classification tag."""
    style = RICH_TAG_STYLE.get(tag)
    return f"[{style}]{text}[/{style}]" if style else text
