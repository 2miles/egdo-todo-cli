from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from egdo.config import CONFIG_PATH, load_config, save_config, write_config
from egdo.store import add_note, add_task, complete_task, create_task, delete_task, list_tasks, tag_task
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text

console = Console()
HEADER_DATE_STYLE = "bold cyan"
SEPARATOR_STYLE = "dim"
SEPARATOR_TEXT = "────────────────────────────────────────"

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
)


class _EgdoArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        help_text = super().format_help()
        if self.prog == "egdo":
            help_text = help_text.replace(
                f"usage: {self.prog} [-h] {{init,add,list,done,delete,tag,note}} ...",
                f"usage: {self.prog} [-h] COMMAND ...",
                1,
            )
            help_text = help_text.replace("positional arguments:", "commands:")
            help_text = help_text.replace("  {init,add,list,done,delete,tag,note}", "  COMMAND", 1)
            if "options:" in help_text and "Run `egdo COMMAND --help`" not in help_text:
                help_text = help_text.replace(
                    "options:\n",
                    "Run `egdo COMMAND --help` for command-specific usage.\n\noptions:\n",
                    1,
                )
        return help_text


def build_parser() -> argparse.ArgumentParser:
    parser = _EgdoArgumentParser(
        prog="egdo",
        description=(
            "Manage a rolling markdown-backed todo list.\n\n"
            "Common commands:\n"
            "  egdo add \"[chores] Do laundry\"\n"
            "  egdo add --done \"Call dad\"\n"
            "  egdo list\n"
            "  egdo list --tag chores\n"
            "  egdo done 1\n"
            "  egdo delete 2\n"
            "  egdo tag 3 chores home\n"
            '  egdo note "Need to test villager trading setup"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Create egdo config",
        description="Create the egdo config file that points at your notes directory.",
        epilog='Example:\n  egdo init --notes-root /Users/miles/Notes --todos-root egdo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    init_parser.add_argument("--notes-root", required=True)
    init_parser.add_argument("--todos-root", default="egdo")

    add_parser = subparsers.add_parser(
        "add",
        help="Add a task",
        description="Add a task to today's rolling list.",
        epilog='Examples:\n  egdo add "Buy milk"\n  egdo add "[chores] Do laundry"\n  egdo add --done "Call dad"',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_parser.add_argument("text", help="Task text to add")
    add_parser.add_argument("--done", action="store_true", help="Create the task already completed")

    list_parser = subparsers.add_parser(
        "list",
        help="List active tasks",
        description="List today's active tasks. Use --tag to filter by leading bracket tags.",
        epilog='Examples:\n  egdo list\n  egdo list --tag chores',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_parser.add_argument("--tag", help="Show only tasks with this leading bracket tag")

    done_parser = subparsers.add_parser(
        "done",
        help="Complete a task",
        description="Mark a task complete using the index shown by `egdo list`.",
        epilog="Example:\n  egdo done 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    done_parser.add_argument("index", type=int, help="Task number from `egdo list`")

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description="Delete a task using the index shown by `egdo list`.",
        epilog="Example:\n  egdo delete 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    delete_parser.add_argument("index", type=int, help="Task number from `egdo list`")

    tag_parser = subparsers.add_parser(
        "tag",
        help="Add tag(s) to a task",
        description="Add one or more leading bracket tags to a task using the index shown by `egdo list`.",
        epilog="Example:\n  egdo tag 3 chores home",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    tag_parser.add_argument("index", type=int, help="Task number from `egdo list`")
    tag_parser.add_argument("tags", nargs="+", help="One or more tags to add")

    note_parser = subparsers.add_parser(
        "note",
        help="Add a note for today",
        description="Append a note to today's Notes section.",
        epilog='Example:\n  egdo note "Need to test villager trading setup"',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    note_parser.add_argument("text", help="Note text to append")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return _run_init(Path(args.notes_root).expanduser(), args.todos_root)

        config = load_config()
        target_date = date.today()

        if args.command == "add":
            task = create_task(config.notes_dir, target_date, args.text, done=args.done)
            action = "Added" if not args.done else "Added done"
            console.print(f"{action} [{task.created.isoformat()}] {task.text}")
            return 0

        if args.command == "list":
            tasks = list_tasks(config.notes_dir, target_date, tag=args.tag)
            tag_styles, updated, warnings = _build_tag_styles(
                (task.text for task in tasks), config.tag_colors
            )
            if updated:
                config.tag_colors = tag_styles
                save_config(config)
            console.print()
            console.print(_render_list_header(target_date))
            console.print(Text(SEPARATOR_TEXT, style=SEPARATOR_STYLE))
            for warning in warnings:
                console.print(Text(warning, style="yellow"))
            if not tasks:
                console.print(Text("No active tasks.", style="dim"))
                return 0
            for idx, task in enumerate(tasks, start=1):
                console.print(_render_task_line(idx, task.text, task.created, tag_styles))
            return 0

        if args.command == "done":
            task = complete_task(config.notes_dir, target_date, args.index)
            console.print(f"Completed [{target_date.isoformat()}] {task.text}")
            return 0

        if args.command == "delete":
            task = delete_task(config.notes_dir, target_date, args.index)
            console.print(f"Deleted [{target_date.isoformat()}] {task.text}")
            return 0

        if args.command == "tag":
            task = tag_task(config.notes_dir, target_date, args.index, args.tags)
            console.print(f"Tagged [{target_date.isoformat()}] {task.text}")
            return 0

        if args.command == "note":
            add_note(config.notes_dir, target_date, args.text)
            console.print(f"Noted [{target_date.isoformat()}] {args.text}")
            return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_init(notes_root: Path, todos_root: str) -> int:
    config_path = write_config(notes_root=notes_root, todos_root=todos_root, path=CONFIG_PATH)
    print(f"Wrote config to {config_path}")
    return 0


def _format_display_date(value: date) -> str:
    return f"{value.strftime('%a, %b')} {value.day}{_ordinal_suffix(value.day)}"


def _render_list_header(target_date: date) -> Text:
    header = Text()
    header.append(_format_display_date(target_date), style=HEADER_DATE_STYLE)
    return header


def _render_task_line(
    index: int, task_text: str, created: date, tag_styles: dict[str, str]
) -> Text:
    tags, body = _split_leading_tags(task_text)
    line = Text()
    line.append(f"{index}. ", style="dim")
    for tag in tags:
        line.append(f"[{tag}]", style=tag_styles.get(tag.lower(), TAG_STYLES[0]))
    if tags and body:
        line.append(" ")
    line.append(body, style="default")
    line.append(f" ({_format_display_date(created)})", style="dim")
    return line


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


def _is_valid_style(style: str) -> bool:
    try:
        Style.parse(style)
    except StyleSyntaxError:
        return False
    return True


def _ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


if __name__ == "__main__":
    raise SystemExit(main())
