"""Build Rich renderables for task lists."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from egdo.markdown_store import split_task_prefix

HEADER_DATE_STYLE = "bold"
SEPARATOR_STYLE = "dim"
INDEX_COLUMN_WIDTH = 7
TAG_COLUMN_WIDTH = 12
TAG_STYLE = "dim cyan"


def render_list_header(target_date) -> Text:
    header = Text()
    header.append(target_date.strftime("%A, %B ") + str(target_date.day), style=HEADER_DATE_STYLE)
    return header


def render_separator(width: int) -> Text:
    return Text("─" * max(1, width), style=SEPARATOR_STYLE)


def render_section_header(label: str, width: int) -> Text:
    """Render a consistent labeled rule for a top-level task group."""
    padded_label = f" {label} "
    line_width = max(len(padded_label) + 2, width)
    left = 2
    right = line_width - left - len(padded_label)
    header = Text()
    header.append("─" * left, style=SEPARATOR_STYLE)
    header.append(padded_label)
    header.append("─" * right, style=SEPARATOR_STYLE)
    return header


def render_task_line(
    index: str | int,
    task_text: str,
    created,
    wrap_width: int = 88,
    depth: int = 0,
    show_created: bool = True,
) -> Table:
    """Render one task in fixed ID, priority, description, and date columns."""
    priority, tag, body = split_task_prefix(task_text)
    total_width = max(20, wrap_width)
    date_width = 8 if show_created else 0
    description_width = max(
        8, total_width - INDEX_COLUMN_WIDTH - 3 - TAG_COLUMN_WIDTH - date_width
    )

    table = Table.grid(padding=0)
    table.add_column(width=INDEX_COLUMN_WIDTH, no_wrap=True, style="white")
    table.add_column(width=3, no_wrap=True)
    table.add_column(width=TAG_COLUMN_WIDTH, no_wrap=True)
    table.add_column(width=description_width)
    if show_created:
        table.add_column(width=date_width, no_wrap=True, justify="right", style="dim")

    description = Text()
    if depth > 0:
        description.append("  " * (depth - 1))
        description.append("·", style="dim")
        description.append(" ")
    body = _capitalize_first_letter(body)
    description.append(body)

    marker = Text("●  " if priority else "   ")
    tag_text = Text(_truncate_tag(tag) if tag else "", style=TAG_STYLE)

    cells = [
        Text(_format_task_index(index), style="white"),
        marker,
        tag_text,
        description,
    ]
    if show_created:
        cells.append(Text(_format_task_date(created), style="dim"))
    table.add_row(*cells)
    return table


def _format_task_date(value) -> str:
    return f"{value.strftime('%b')} {value.day:>2}"


def _format_task_index(index: str | int) -> str:
    """Align the numeric parent portion while reserving room for nested suffixes."""
    token = str(index)
    digit_count = 0
    while digit_count < len(token) and token[digit_count].isdigit():
        digit_count += 1
    label = f"{token[:digit_count]:>2}{token[digit_count:]}."
    return f"{label:<{INDEX_COLUMN_WIDTH}}"


def _capitalize_first_letter(text: str) -> str:
    """Uppercase the first alphabetic character without changing the rest."""
    for index, character in enumerate(text):
        if character.isalpha():
            return f"{text[:index]}{character.upper()}{text[index + 1:]}"
    return text


def _truncate_tag(tag: str) -> str:
    """Fit a tag into its fixed display column without changing stored text."""
    label = tag.upper()
    visible_width = TAG_COLUMN_WIDTH - 2
    if len(label) <= visible_width:
        return label
    return f"{label[: visible_width - 1]}…"


def task_wrap_width(current_console: Console) -> int:
    """Clamp output width to remain readable on narrow and very wide terminals."""
    return max(40, min(current_console.size.width, 96))
