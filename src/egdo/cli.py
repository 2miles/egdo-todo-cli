from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from egdo.config import CONFIG_PATH, load_config, save_config, write_config
from egdo.dates import format_display_date as _format_display_date
from egdo.dates import parse_future_date as _parse_future_date
from egdo.handlers import HandlerDeps
from egdo.handlers import build_tag_styles as _build_tag_styles
from egdo.handlers import choose_tag_style_interactive as _choose_tag_style_interactive
from egdo.handlers import dispatch_command
from egdo.handlers import is_valid_style as _is_valid_style
from egdo.handlers import normalize_tag_name as _normalize_tag_name
from egdo.store import (
    add_note,
    add_task,
    complete_task,
    create_task,
    delete_future_task,
    delete_task,
    edit_future_task,
    edit_task,
    complete_future_task,
    list_future_tasks,
    list_tasks,
    move_future_task,
    move_task,
    tag_future_task,
    tag_task,
    unmove_task,
)
from egdo.render import TAG_STYLES
from egdo.render import render_list_header as _render_list_header
from egdo.render import render_separator as _render_separator
from egdo.render import render_tag_style_picker as _render_tag_style_picker
from egdo.render import render_task_line as _render_task_line
from egdo.render import split_leading_tags as _split_leading_tags
from egdo.render import style_wrapped_task_line as _style_wrapped_task_line
from egdo.render import task_wrap_width as _task_wrap_width
from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

console = Console()


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
            "  egdo future\n"
            "  egdo list --tag chores\n"
            "  egdo done 1\n"
            '  egdo edit 2 "Buy oat milk"\n'
            "  egdo move 2 tomorrow\n"
            "  egdo future unmove 1\n"
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

    future_parser = subparsers.add_parser(
        "future",
        help="List or manage future tasks",
        description="List incomplete tasks scheduled after today, or operate on them by future index.",
        epilog=(
            "Examples:\n"
            "  egdo future\n"
            "  egdo future --tag chores\n"
            "  egdo future done 1\n"
            '  egdo future edit 1 "Buy oat milk"\n'
            "  egdo future move 2 sunday\n"
            "  egdo future unmove 1"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_subparsers = future_parser.add_subparsers(dest="future_command", metavar="FUTURE_COMMAND")
    future_parser.add_argument("--tag", help="Show only future tasks with this leading bracket tag")

    future_done_parser = future_subparsers.add_parser(
        "done",
        help="Complete a future task",
        description="Mark a task complete using the index shown by `egdo future`.",
        epilog="Example:\n  egdo future done 1",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_done_parser.add_argument("index", type=int, help="Task number from `egdo future`")

    future_delete_parser = future_subparsers.add_parser(
        "delete",
        help="Delete a future task",
        description="Delete a task using the index shown by `egdo future`.",
        epilog="Example:\n  egdo future delete 2",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_delete_parser.add_argument("index", type=int, help="Task number from `egdo future`")

    future_edit_parser = future_subparsers.add_parser(
        "edit",
        help="Edit a future task",
        description="Edit a task using the index shown by `egdo future`.",
        epilog='Example:\n  egdo future edit 1 "Buy oat milk"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_edit_parser.add_argument("index", type=int, help="Task number from `egdo future`")
    future_edit_parser.add_argument("text", help="Replacement task text")

    future_move_parser = future_subparsers.add_parser(
        "move",
        help="Move a future task to another future date",
        description="Move a task using the index shown by `egdo future`.",
        epilog=(
            "Examples:\n"
            "  egdo future move 2 tomorrow\n"
            "  egdo future move 2 +3\n"
            "  egdo future move 2 sunday\n"
            "  egdo future move 2 2026-04-12"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_move_parser.add_argument("index", type=int, help="Task number from `egdo future`")
    future_move_parser.add_argument(
        "when",
        help="Future date: tomorrow, +N, weekday name, or YYYY-MM-DD",
    )

    future_tag_parser = future_subparsers.add_parser(
        "tag",
        help="Add tag(s) to a future task",
        description="Add one or more leading bracket tags to a task using the index shown by `egdo future`.",
        epilog="Example:\n  egdo future tag 1 chores home",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_tag_parser.add_argument("index", type=int, help="Task number from `egdo future`")
    future_tag_parser.add_argument("tags", nargs="+", help="One or more tags to add")

    future_unmove_parser = future_subparsers.add_parser(
        "unmove",
        help="Bring a future task back to today",
        description="Move a task from `egdo future` back to today's active list.",
        epilog="Example:\n  egdo future unmove 1",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_unmove_parser.add_argument("index", type=int, help="Task number from `egdo future`")

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
        deps = HandlerDeps(
            add_note=add_note,
            complete_future_task=complete_future_task,
            complete_task=complete_task,
            create_task=create_task,
            delete_future_task=delete_future_task,
            delete_task=delete_task,
            edit_future_task=edit_future_task,
            edit_task=edit_task,
            list_future_tasks=list_future_tasks,
            list_tasks=list_tasks,
            move_future_task=move_future_task,
            move_task=move_task,
            parse_future_date=_parse_future_date,
            render_list_header=_render_list_header,
            render_separator=_render_separator,
            render_tag_style_picker=_render_tag_style_picker,
            render_task_line=_render_task_line,
            save_config=save_config,
            tag_future_task=tag_future_task,
            tag_task=tag_task,
            task_wrap_width=_task_wrap_width,
            unmove_task=unmove_task,
        )
        return dispatch_command(args, config, target_date, console, deps)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_init(root: Path) -> int:
    config_path = write_config(root=root, path=CONFIG_PATH)
    print(f"Wrote config to {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
