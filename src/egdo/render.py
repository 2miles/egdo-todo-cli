from __future__ import annotations

import textwrap

from egdo.dates import format_display_date
from rich.console import Console, Group
from rich.text import Text

HEADER_DATE_STYLE = "bold cyan"
SEPARATOR_STYLE = "dim"

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
    index: int, task_text: str, created, tag_styles: dict[str, str], wrap_width: int = 88
) -> Group:
    tags, body = split_leading_tags(task_text)
    label = " ".join(f"{{{tag.upper()}}}" for tag in tags)
    if label and body:
        label = f"{label} {body}"
    elif body:
        label = body
    date_text = f" ({format_display_date(created)})"
    total_width = max(20, wrap_width)
    initial_indent = f"{index}. "
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
            style_wrapped_task_line(line, initial_indent, date_text, tag_styles)
            for line in wrapped_lines
        ]
    )


def split_leading_tags(task_text: str) -> tuple[list[str], str]:
    tags: list[str] = []
    remaining = task_text.lstrip()
    while True:
        parsed = _parse_tag_token(remaining)
        if parsed is None:
            break
        tag, remaining = parsed
        tags.append(tag)
        remaining = remaining.lstrip()
    return tags, remaining.lstrip()


def style_wrapped_task_line(
    line: str, initial_indent: str, date_text: str, tag_styles: dict[str, str]
) -> Text:
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

    tags, body = split_leading_tags(content)
    styled = Text()
    styled.append(prefix, style="dim")
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
    return max(40, min(current_console.size.width, 96))


def render_tag_style_picker(tag: str, selected_index: int, current_style: str | None = None) -> Group:
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


def _parse_tag_token(text: str) -> tuple[str, str] | None:
    if text.startswith("{"):
        closing = text.find("}")
        if closing <= 1:
            return None
        tag = text[1:closing].strip()
        if not tag:
            return None
        return (tag, text[closing + 1 :])
    return None


def _wrap_task_content(text: str, first_width: int, subsequent_width: int) -> list[str]:
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
