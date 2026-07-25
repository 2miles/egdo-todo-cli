"""Build Rich renderables for task lists and interactive style pickers."""

from __future__ import annotations

import textwrap

from egdo.dates import format_display_date, ordinal_suffix
from rich.console import Console, Group
from rich.text import Text

from egdo.markdown_store import split_task_prefix

HEADER_DATE_STYLE = "bold cyan"
SEPARATOR_STYLE = "dim"
PRIORITY_MARKERS = {1: "!!!", 2: ".!!", 3: "..!", 4: "..."}
DEFAULT_PRIORITY_STYLES = {
    "p1": "bold white on red",
    "p2": "bold orange1",
    "p3": "yellow",
    "p4": "grey50",
}

## Available colors: https://rich.readthedocs.io/en/stable/appendix/colors.html
TAG_STYLES = (
    "medium_orchid3",
    "medium_orchid",
    "dark_goldenrod",
    "rosy_brown",
    "grey63",
    "medium_purple2",
    "medium_purple1",
    "dark_khaki",
    "navajo_white3",
    "grey69",
    "light_steel_blue3",
    "light_steel_blue",
    "dark_olive_green3",
    "dark_sea_green3",
    "light_cyan3",
    "light_sky_blue1",
    "green_yellow",
    "dark_olive_green2",
    "pale_green1",
    "dark_sea_green2",
    "pale_turquoise1",
    "misty_rose3",
    "plum2",
    "light_pink1",
    "hot_pink2",
    "navajo_white1",
    "light_goldenrod3",
    "yellow3",
)


def render_list_header(target_date) -> Text:
    header = Text()
    header.append(format_display_date(target_date), style=HEADER_DATE_STYLE)
    return header


def render_separator(width: int) -> Text:
    return Text("─" * max(1, width), style=SEPARATOR_STYLE)


def render_task_line(
    index: int,
    task_text: str,
    created,
    tag_styles: dict[str, str],
    wrap_width: int = 88,
    priority_styles: dict[str, str] | None = None,
) -> Group:
    """Wrap one task while reserving fixed columns for index, priority, and date."""
    priority, tags, body = split_task_prefix(task_text)
    display_priority = priority if priority is not None else 4
    prefix_parts = [f"{{{tag.upper()}}}" for tag in tags]
    label = " ".join(prefix_parts + ([body] if body else []))
    date_text = f" ({_format_task_date(created)})"
    total_width = max(20, wrap_width)
    marker = PRIORITY_MARKERS[display_priority]
    initial_indent = f"{index:>2}. {marker:<3} "
    subsequent_indent = " " * len(initial_indent)
    first_line_width = max(8, total_width - len(initial_indent) - len(date_text) - 2)
    subsequent_width = max(8, total_width - len(subsequent_indent))
    wrapped_content = _wrap_task_content(label, first_line_width, subsequent_width)
    first_content = wrapped_content[0] if wrapped_content else ""
    padding = max(2, total_width - len(initial_indent) - len(first_content) - len(date_text))
    wrapped_lines = [f"{initial_indent}{first_content}{' ' * padding}{date_text}"]
    wrapped_lines.extend(f"{subsequent_indent}{line}" for line in wrapped_content[1:])
    return Group(
        *[
            style_wrapped_task_line(
                line,
                initial_indent,
                date_text,
                tag_styles,
                priority=display_priority,
                priority_styles=priority_styles,
            )
            for line in wrapped_lines
        ]
    )


def _format_task_date(value) -> str:
    return f"{value.strftime('%a, %b')} {value.day:>2}{ordinal_suffix(value.day)}"


def style_wrapped_task_line(
    line: str,
    initial_indent: str,
    date_text: str,
    tag_styles: dict[str, str],
    priority: int | None = None,
    priority_styles: dict[str, str] | None = None,
) -> Text:
    """Apply styles after wrapping so prefixes and right-aligned dates stay intact."""
    if line.startswith(initial_indent):
        prefix = initial_indent
    else:
        prefix = " " * len(initial_indent)

    content = line[len(prefix) :]
    date_suffix = ""
    if content.endswith(date_text):
        date_suffix = date_text
        content = content[: -len(date_suffix)]
    else:
        stripped_date = date_text.strip()
        if content == stripped_date:
            date_suffix = stripped_date
            content = ""

    _, tags, body = split_task_prefix(content)
    styled = Text()
    if priority is not None and line.startswith(initial_indent):
        marker = PRIORITY_MARKERS[priority]
        resolved_priority_styles = {**DEFAULT_PRIORITY_STYLES, **(priority_styles or {})}
        index_prefix = prefix[:-4].rstrip()
        styled.append(f"{index_prefix} ", style="white")
        for character in marker:
            style = resolved_priority_styles["p4" if character == "." else f"p{priority}"]
            styled.append(character, style=style)
        styled.append(" ")
    else:
        styled.append(prefix, style="white" if line.startswith(initial_indent) else None)
    for index, tag in enumerate(tags):
        if index > 0:
            styled.append(" ")
        styled.append(f"{{{tag.upper()}}}", style=tag_styles.get(tag.lower(), TAG_STYLES[0]))
    if tags and body:
        styled.append(" ")
    styled.append(body, style="default")
    if date_suffix:
        styled.append(date_suffix, style="dim")
    return styled


def task_wrap_width(current_console: Console) -> int:
    """Clamp output width to remain readable on narrow and very wide terminals."""
    return max(40, min(current_console.size.width, 96))


def render_tag_style_picker(tag: str, selected_index: int, current_style: str | None = None) -> Group:
    """Build the full-screen tag palette with selection and current markers."""
    title = Text("Choose a color for ")
    title.append(f"{{{tag.upper()}}}", style=TAG_STYLES[selected_index])
    instructions = Text("Use up/down or j/k, Enter to save, q or Esc to cancel.", style="dim")
    rows: list[Text] = [title, instructions, Text("")]
    for index, style_name in enumerate(TAG_STYLES):
        row = Text()
        marker = ">" if index == selected_index else " "
        row.append(f"{marker} ", style="bold" if index == selected_index else "dim")
        row.append(f"{{{tag.upper()}}} ", style=style_name)
        row.append(style_name, style="bold" if index == selected_index else "default")
        if style_name == current_style:
            row.append(" current", style="dim")
        rows.append(row)
    return Group(*rows)


def render_priority_style_picker(
    priority_key: str, selected_index: int, current_style: str | None = None
) -> Group:
    """Build the priority palette using the marker users will actually see."""
    priority = int(priority_key.removeprefix("p"))
    marker = PRIORITY_MARKERS[priority]
    title = Text(f"Choose a style for {priority_key.upper()}: ")
    title.append(marker, style=TAG_STYLES[selected_index])
    instructions = Text("Use up/down or j/k, Enter to save, q or Esc to cancel.", style="dim")
    rows: list[Text] = [title, instructions, Text("")]
    for index, style_name in enumerate(TAG_STYLES):
        row = Text()
        selection = ">" if index == selected_index else " "
        row.append(f"{selection} ", style="bold" if index == selected_index else "dim")
        row.append(f"{marker} ", style=style_name)
        row.append(style_name, style="bold" if index == selected_index else "default")
        if style_name == current_style:
            row.append(" current", style="dim")
        rows.append(row)
    return Group(*rows)


def _wrap_task_content(text: str, first_width: int, subsequent_width: int) -> list[str]:
    """Wrap the first line more narrowly to leave room for its date suffix."""
    if not text:
        return [""]

    wrapped: list[str] = []
    remaining = text
    current_width = first_width
    while remaining:
        lines = textwrap.wrap(
            remaining,
            width=current_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not lines:
            wrapped.append(remaining)
            break
        line = lines[0]
        wrapped.append(line)
        remaining = remaining[len(line) :].lstrip()
        current_width = subsequent_width
    return wrapped
