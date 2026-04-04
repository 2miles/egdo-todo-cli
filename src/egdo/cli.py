from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from egdo.config import CONFIG_PATH, load_config, save_config, write_config
from egdo.store import add_task, complete_task, file_path, list_tasks
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text

console = Console()
HEADER_DATE_STYLE = "bold cyan"
TAG_STYLES = (
    "green",
    "blue",
    "magenta",
    "yellow",
    "red",
    "bright_black",
    "bright_blue",
    "bright_green",
    "bright_magenta",
    "bright_red",
    "bright_yellow",
    "bold green",
    "bold blue",
    "bold magenta",
    "bold yellow",
    "bold red",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="egdo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create egdo config")
    init_parser.add_argument("--notes-root", required=True)
    init_parser.add_argument("--todos-root", default="egdo")

    add_parser = subparsers.add_parser("add", help="Add a task")
    add_parser.add_argument("text")

    list_parser = subparsers.add_parser("list", help="List active tasks")
    list_parser.add_argument("--tag")

    done_parser = subparsers.add_parser("done", help="Complete a task")
    done_parser.add_argument("index", type=int)

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
            task = add_task(config.notes_dir, target_date, args.text)
            console.print(f"Added [{task.created.isoformat()}] {task.text}")
            return 0

        if args.command == "list":
            tasks = list_tasks(config.notes_dir, target_date, tag=args.tag)
            daily_path = file_path(config.notes_dir, target_date)
            tag_styles, updated, warnings = _build_tag_styles((task.text for task in tasks), config.tag_colors)
            if updated:
                config.tag_colors = tag_styles
                save_config(config)
            console.print(_render_list_header(target_date, daily_path))
            console.print(Text("---", style="dim"))
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


def _render_list_header(target_date: date, daily_path: Path) -> Text:
    header = Text()
    header.append(_format_display_date(target_date), style=HEADER_DATE_STYLE)
    header.append("  ")
    header.append(str(daily_path), style="dim")
    return header


def _render_task_line(index: int, task_text: str, created: date, tag_styles: dict[str, str]) -> Text:
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
