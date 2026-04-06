from __future__ import annotations

import argparse
from datetime import date, timedelta
import os
from pathlib import Path
import sys
import termios
import textwrap
import tty

from egdo.config import CONFIG_PATH, load_config, save_config, write_config
from egdo.store import (
    add_note,
    add_task,
    complete_task,
    create_task,
    delete_task,
    edit_task,
    list_tasks,
    move_task,
    tag_task,
)
from rich.console import Console, Group
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text
from rich_argparse import RawDescriptionRichHelpFormatter

console = Console()
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="egdo",
        description="Manage a rolling markdown-backed todo list. Run without a command to show today's active tasks.",
        epilog=(
            "Examples:\n"
            "  egdo\n"
            '  egdo add "Do laundry"\n'
            '  egdo add --done "Call dad"\n'
            "  egdo list\n"
            "  egdo list --tag chores\n"
            "  egdo done 1\n"
            '  egdo edit 2 "Buy oat milk"\n'
            "  egdo move 2 tomorrow\n"
            "  egdo delete 2\n"
            "  egdo tag 3 chores home\n"
            '  egdo note "Need to test villager trading setup"\n\n'
            "Run `egdo COMMAND --help` for command-specific usage."
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        metavar="COMMAND",
        required=True,
        parser_class=argparse.ArgumentParser,
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Create egdo config",
        description="Create the egdo config file that points at your egdo storage directory.",
        epilog="Example:\n  egdo init --root /Users/miles/Notes/egdo",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    init_parser.add_argument("--root", required=True, help="Directory where egdo stores its yearly files")

    add_parser = subparsers.add_parser(
        "add",
        help="Add a task",
        description="Add a task to today's rolling list.",
        epilog='Examples:\n  egdo add "Buy milk"\n  egdo add "Do laundry"\n  egdo add --done "Call dad"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    add_parser.add_argument("text", help="Task text to add")
    add_parser.add_argument("--done", action="store_true", help="Create the task already completed")

    list_parser = subparsers.add_parser(
        "list",
        help="List active tasks",
        description="List today's active tasks. Use --tag to filter by leading bracket tags.",
        epilog="Examples:\n  egdo list\n  egdo list --tag chores",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    list_parser.add_argument("--tag", help="Show only tasks with this leading bracket tag")

    done_parser = subparsers.add_parser(
        "done",
        help="Complete a task",
        description="Mark a task complete using the index shown by `egdo list`.",
        epilog="Example:\n  egdo done 1",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    done_parser.add_argument("index", type=int, help="Task number from `egdo list`")

    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit a task",
        description="Edit a task using the index shown by `egdo list`.",
        epilog='Example:\n  egdo edit 2 "Buy oat milk"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    edit_parser.add_argument("index", type=int, help="Task number from `egdo list`")
    edit_parser.add_argument("text", help="Replacement task text")

    move_parser = subparsers.add_parser(
        "move",
        help="Move a task to a future date",
        description="Move a task to a future date using the index shown by `egdo list`.",
        epilog=(
            "Examples:\n"
            "  egdo move 2 tomorrow\n"
            "  egdo move 2 +3\n"
            "  egdo move 2 sunday\n"
            "  egdo move 2 2026-04-10"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    move_parser.add_argument("index", type=int, help="Task number from `egdo list`")
    move_parser.add_argument(
        "when",
        help="Future date: tomorrow, +N, weekday name, or YYYY-MM-DD",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description="Delete a task using the index shown by `egdo list`.",
        epilog="Example:\n  egdo delete 2",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    delete_parser.add_argument("index", type=int, help="Task number from `egdo list`")

    tag_parser = subparsers.add_parser(
        "tag",
        help="Add tag(s) to a task",
        description="Add one or more leading bracket tags to a task using the index shown by `egdo list`.",
        epilog="Example:\n  egdo tag 3 chores home",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    tag_parser.add_argument("index", type=int, help="Task number from `egdo list`")
    tag_parser.add_argument("tags", nargs="+", help="One or more tags to add")

    note_parser = subparsers.add_parser(
        "note",
        help="Add a note for today",
        description="Append a note to today's Notes section.",
        epilog='Example:\n  egdo note "Need to test villager trading setup"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    note_parser.add_argument("text", help="Note text to append")

    color_parser = subparsers.add_parser(
        "color",
        help="Set a tag color",
        description="Set the terminal style used for a tag. Defaults to an interactive picker.",
        epilog="Examples:\n  egdo color chores\n  egdo color chores --style green_yellow",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    color_parser.add_argument("tag", help="Tag name to style")
    color_parser.add_argument("--style", help="Rich style name to save without opening the picker")

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["list"]
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return _run_init(Path(args.root).expanduser())

        config = load_config()
        target_date = date.today()

        if args.command == "add":
            task = create_task(config.root, target_date, args.text, done=args.done)
            action = "Added" if not args.done else "Added done"
            console.print(f"{action} [{task.created.isoformat()}] {task.text}")
            return 0

        if args.command == "list":
            tasks = list_tasks(config.root, target_date, tag=args.tag)
            tag_styles, updated, warnings = _build_tag_styles(
                (task.text for task in tasks), config.tag_colors
            )
            if updated:
                config.tag_colors = tag_styles
                save_config(config)
            wrap_width = _task_wrap_width(console)
            console.print()
            console.print(_render_list_header(target_date))
            console.print(_render_separator(wrap_width))
            for warning in warnings:
                console.print(Text(warning, style="yellow"))
            if not tasks:
                console.print(Text("No active tasks.", style="dim"))
                return 0
            for idx, task in enumerate(tasks, start=1):
                console.print(
                    _render_task_line(
                        idx, task.text, task.created, tag_styles, wrap_width=wrap_width
                    )
                )
            return 0

        if args.command == "done":
            task = complete_task(config.root, target_date, args.index)
            console.print(f"Completed [{target_date.isoformat()}] {task.text}")
            return 0

        if args.command == "edit":
            task = edit_task(config.root, target_date, args.index, args.text)
            console.print(f"Edited [{task.created.isoformat()}] {task.text}")
            return 0

        if args.command == "move":
            destination_date = _parse_future_date(args.when, target_date)
            task = move_task(config.root, target_date, args.index, destination_date)
            console.print(
                f"Moved [{task.created.isoformat()}] {task.text} -> {destination_date.isoformat()}"
            )
            return 0

        if args.command == "delete":
            task = delete_task(config.root, target_date, args.index)
            console.print(f"Deleted [{target_date.isoformat()}] {task.text}")
            return 0

        if args.command == "tag":
            task = tag_task(config.root, target_date, args.index, args.tags)
            console.print(f"Tagged [{target_date.isoformat()}] {task.text}")
            return 0

        if args.command == "note":
            add_note(config.root, target_date, args.text)
            console.print(f"Noted [{target_date.isoformat()}] {args.text}")
            return 0

        if args.command == "color":
            tag = _normalize_tag_name(args.tag)
            if not tag:
                raise ValueError("Tag name cannot be empty")
            if args.style:
                selected_style = args.style.strip()
                if not _is_valid_style(selected_style):
                    raise ValueError(f"Invalid style: {selected_style}")
            else:
                selected_style = _choose_tag_style_interactive(tag, config.tag_colors.get(tag))
                if selected_style is None:
                    console.print("Canceled tag color update.")
                    return 0
            config.tag_colors[tag] = selected_style
            save_config(config)
            preview = Text()
            preview.append(f"[{tag}]", style=selected_style)
            preview.append(f" -> {selected_style}", style="dim")
            console.print(Text("Saved tag color: ") + preview)
            return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_init(root: Path) -> int:
    config_path = write_config(root=root, path=CONFIG_PATH)
    print(f"Wrote config to {config_path}")
    return 0


def _format_display_date(value: date) -> str:
    return f"{value.strftime('%a, %b')} {value.day}{_ordinal_suffix(value.day)}"


def _render_list_header(target_date: date) -> Text:
    header = Text()
    header.append(_format_display_date(target_date), style=HEADER_DATE_STYLE)
    return header


def _render_separator(width: int) -> Text:
    return Text("─" * max(1, width), style=SEPARATOR_STYLE)


def _render_task_line(
    index: int, task_text: str, created: date, tag_styles: dict[str, str], wrap_width: int = 88
) -> Group:
    tags, body = _split_leading_tags(task_text)
    label = "".join(f"[{tag}]" for tag in tags)
    if label and body:
        label = f"{label} {body}"
    elif body:
        label = body
    date_text = f" ({_format_display_date(created)})"
    initial_indent = f"{index}. "
    subsequent_indent = " " * len(initial_indent)
    wrapped_lines = textwrap.wrap(
        label,
        width=max(20, wrap_width),
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped_lines:
        wrapped_lines = [initial_indent.rstrip()]
    available = max(0, max(20, wrap_width) - len(wrapped_lines[-1]))
    if len(date_text) <= available:
        wrapped_lines[-1] = f"{wrapped_lines[-1]}{date_text}"
    else:
        wrapped_lines.append(f"{subsequent_indent}{date_text.strip()}")
    return Group(
        *[
            _style_wrapped_task_line(line, initial_indent, date_text, tag_styles)
            for line in wrapped_lines
        ]
    )


def _split_leading_tags(task_text: str) -> tuple[list[str], str]:
    tags: list[str] = []
    remaining = task_text.lstrip()
    while remaining.startswith("["):
        closing = remaining.find("]")
        if closing <= 1:
            break
        tag = remaining[1:closing].strip()
        if not tag:
            break
        tags.append(tag)
        remaining = remaining[closing + 1 :]
    return tags, remaining.lstrip()


def _style_wrapped_task_line(
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

    tags, body = _split_leading_tags(content)
    styled = Text()
    styled.append(prefix, style="dim")
    for tag in tags:
        styled.append(f"[{tag}]", style=tag_styles.get(tag.lower(), TAG_STYLES[0]))
    if tags and body:
        styled.append(" ")
    styled.append(body, style="default")
    if date_suffix:
        styled.append(date_suffix, style="dim")
    return styled


def _task_wrap_width(current_console: Console) -> int:
    return max(40, min(current_console.size.width, 96))


def _build_tag_styles(
    task_texts: list[str] | tuple[str, ...] | object, existing_styles: dict[str, str] | None = None
) -> tuple[dict[str, str], bool, list[str]]:
    styles = dict(existing_styles or {})
    updated = False
    warnings: list[str] = []
    valid_assigned = [style for style in styles.values() if _is_valid_style(style)]
    next_style = len(valid_assigned)
    for task_text in task_texts:
        tags, _ = _split_leading_tags(task_text)
        for tag in tags:
            normalized = tag.lower()
            if normalized in styles:
                if not _is_valid_style(styles[normalized]):
                    styles[normalized] = TAG_STYLES[next_style % len(TAG_STYLES)]
                    next_style += 1
                    updated = True
                    warnings.append(
                        f"Invalid style for tag `{normalized}` in config. Reassigned it to `{styles[normalized]}`."
                    )
                continue
            if normalized not in styles:
                styles[normalized] = TAG_STYLES[next_style % len(TAG_STYLES)]
                next_style += 1
                updated = True
    return styles, updated, warnings


def _normalize_tag_name(tag: str) -> str:
    return tag.strip().strip("[]").strip().lower()


def _choose_tag_style_interactive(tag: str, current_style: str | None = None) -> str | None:
    if not sys.stdin.isatty():
        raise ValueError(
            "Interactive color picker requires a TTY. Use `egdo color TAG --style STYLE`."
        )

    selected_index = TAG_STYLES.index(current_style) if current_style in TAG_STYLES else 0
    with console.screen(hide_cursor=True) as screen:
        screen.update(_render_tag_style_picker(tag, selected_index, current_style))
        while True:
            key = _read_picker_key()
            if key == "up":
                selected_index = (selected_index - 1) % len(TAG_STYLES)
            elif key == "down":
                selected_index = (selected_index + 1) % len(TAG_STYLES)
            elif key == "enter":
                return TAG_STYLES[selected_index]
            elif key in {"escape", "quit"}:
                return None
            else:
                continue
            screen.update(_render_tag_style_picker(tag, selected_index, current_style))


def _render_tag_style_picker(
    tag: str, selected_index: int, current_style: str | None = None
) -> Group:
    title = Text("Choose a color for ")
    title.append(f"[{tag}]", style=TAG_STYLES[selected_index])
    instructions = Text("Use up/down or j/k, Enter to save, q or Esc to cancel.", style="dim")
    rows: list[Text] = [title, instructions, Text("")]
    for index, style_name in enumerate(TAG_STYLES):
        row = Text()
        marker = ">" if index == selected_index else " "
        row.append(f"{marker} ", style="bold" if index == selected_index else "dim")
        row.append(f"[{tag}] ", style=style_name)
        row.append(style_name, style="bold" if index == selected_index else "default")
        if style_name == current_style:
            row.append(" current", style="dim")
        rows.append(row)
    return Group(*rows)


def _read_picker_key() -> str:
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        first = os.read(fd, 1)
        if first in {b"\r", b"\n"}:
            return "enter"
        if first in {b"k"}:
            return "up"
        if first in {b"j"}:
            return "down"
        if first in {b"q"}:
            return "quit"
        if first == b"\x1b":
            second = os.read(fd, 1)
            if second == b"[":
                third = os.read(fd, 1)
                if third == b"A":
                    return "up"
                if third == b"B":
                    return "down"
            return "escape"
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)


def _is_valid_style(style: str) -> bool:
    try:
        Style.parse(style)
    except StyleSyntaxError:
        return False
    return True


def _parse_future_date(value: str, today: date) -> date:
    token = value.strip()
    if not token:
        raise ValueError("Move date cannot be empty")

    lowered = token.lower()
    if lowered == "tomorrow":
        return today + timedelta(days=1)

    if lowered.startswith("+"):
        try:
            days = int(lowered[1:])
        except ValueError as exc:
            raise ValueError(f"Invalid relative date: {value}") from exc
        if days <= 0:
            raise ValueError("Relative move date must be at least +1")
        return today + timedelta(days=days)

    weekday = _parse_weekday_name(lowered)
    if weekday is not None:
        days_ahead = (weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    try:
        parsed = date.fromisoformat(token)
    except ValueError as exc:
        raise ValueError(
            "Invalid move date. Use tomorrow, +N, weekday name, or YYYY-MM-DD."
        ) from exc
    if parsed <= today:
        raise ValueError("Move destination must be a future date")
    return parsed


def _parse_weekday_name(value: str) -> int | None:
    weekday_names = {
        "monday": 0,
        "mon": 0,
        "tuesday": 1,
        "tue": 1,
        "tues": 1,
        "wednesday": 2,
        "wed": 2,
        "thursday": 3,
        "thu": 3,
        "thurs": 3,
        "friday": 4,
        "fri": 4,
        "saturday": 5,
        "sat": 5,
        "sunday": 6,
        "sun": 6,
    }
    return weekday_names.get(value)


def _ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


if __name__ == "__main__":
    raise SystemExit(main())
