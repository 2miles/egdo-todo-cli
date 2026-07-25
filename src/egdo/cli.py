from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from egdo.config import CONFIG_PATH, load_config, save_config, write_config
from egdo.dates import parse_future_date as _parse_future_date
from egdo.handlers import HandlerDeps
from egdo.handlers import dispatch_command
from egdo.store import (
    add_note,
    complete_tasks,
    create_task,
    delete_tasks,
    edit_task,
    list_finished_tasks,
    list_task_refs,
    move_tasks,
    prioritize_tasks,
    tag_tasks,
    untag_tasks,
    unmove_tasks,
)
from egdo.render import render_list_header as _render_list_header
from egdo.render import render_priority_style_picker as _render_priority_style_picker
from egdo.render import render_separator as _render_separator
from egdo.render import render_tag_style_picker as _render_tag_style_picker
from egdo.render import render_task_line as _render_task_line
from egdo.render import task_wrap_width as _task_wrap_width
from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="egdo",
        description="A rolling, Markdown-backed todo list. Run without a command to show your tasks.",
        epilog=(
            "Examples:\n"
            "  egdo\n"
            '  egdo add -p high -t work "Submit application"\n'
            "  egdo done 1 3\n"
            "  egdo move 2 5 tomorrow\n"
            "  egdo priority 4 high\n"
            "  egdo color --tag work\n\n"
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
        epilog=(
            'Examples:\n  egdo add "Buy milk"\n'
            '  egdo add -t chores -t home "Do laundry"\n'
            '  egdo add -p high -t work "Submit application"\n'
            '  egdo add "{CHORES} Do laundry"\n'
            '  egdo add --done -t car -t errands "Call the DMV"\n'
            '  egdo add --done "Call dad"'
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    add_parser.add_argument("text", help="Task text to add")
    add_parser.add_argument(
        "-t",
        "--tag",
        action="append",
        default=[],
        help="Add a leading tag. Repeat for multiple tags.",
    )
    add_parser.add_argument(
        "-p",
        "--priority",
        help="Set priority: 1/critical, 2/high, 3/normal, or 4/low",
    )
    add_parser.add_argument("--done", action="store_true", help="Create the task already completed")

    list_parser = subparsers.add_parser(
        "list",
        help="List active and future tasks",
        description="List today's active tasks. Use -t or --tag to filter by leading tags.",
        epilog="Examples:\n  egdo list\n  egdo list -t chores",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    list_parser.add_argument("-t", "--tag", help="Show only tasks with this leading tag")

    finished_parser = subparsers.add_parser(
        "finished",
        help="List finished tasks",
        description="List today's completed tasks. Use -t or --tag to filter by leading tags.",
        epilog="Examples:\n  egdo finished\n  egdo finished -t chores",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    finished_parser.add_argument("-t", "--tag", help="Show only finished tasks with this leading tag")

    future_parser = subparsers.add_parser(
        "future",
        help="Show the future-task view",
        description="Show incomplete tasks scheduled after today using their global task indexes.",
        epilog=(
            "Examples:\n"
            "  egdo future\n"
            "  egdo future -t chores\n"
            "  egdo future done 1\n"
            '  egdo future edit 1 "Buy oat milk"\n'
            "  egdo future move 2 sunday\n"
            "  egdo future unmove 1"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_subparsers = future_parser.add_subparsers(dest="future_command", metavar="FUTURE_COMMAND")
    future_parser.add_argument("-t", "--tag", help="Show only future tasks with this leading tag")

    future_done_parser = future_subparsers.add_parser(
        "done",
        help="Complete a future task",
        description="Mark a task complete using the index shown by `egdo future`.",
        epilog="Examples:\n  egdo future done 1\n  egdo future done 1 3 7",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_done_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo future`")

    future_delete_parser = future_subparsers.add_parser(
        "delete",
        help="Delete a future task",
        description="Delete a task using the index shown by `egdo future`.",
        epilog="Examples:\n  egdo future delete 2\n  egdo future delete 2 5 8",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_delete_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo future`")

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
            "  egdo future move 2 5 8 tomorrow\n"
            "  egdo future move 2 +3\n"
            "  egdo future move 2 sunday\n"
            "  egdo future move 2 2026-04-12"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_move_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo future`")
    future_move_parser.add_argument(
        "when",
        help="Future date: tomorrow, +N, weekday name, or YYYY-MM-DD",
    )

    future_tag_parser = future_subparsers.add_parser(
        "tag",
        help="Add or remove future-task tags",
        description="Add or remove tags from one or more future tasks.",
        epilog="Examples:\n  egdo future tag 1 chores home\n  egdo future tag 1 3 7 chores home",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_tag_parser.add_argument("values", nargs="+", help="Task number(s), followed by tags")
    future_tag_parser.add_argument("--remove", nargs="+", metavar="TAG", help="Remove tag(s)")

    future_priority_parser = future_subparsers.add_parser(
        "priority",
        help="Set or clear a future task's priority",
        description="Set priority using the index shown by `egdo future`.",
        epilog="Examples:\n  egdo future priority 1 3 7 high\n  egdo future priority 1 none",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_priority_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo future`")
    future_priority_parser.add_argument(
        "level", help="1/critical, 2/high, 3/normal, 4/low, or none"
    )

    future_unmove_parser = future_subparsers.add_parser(
        "unmove",
        help="Bring a future task back to today",
        description="Move a task from `egdo future` back to today's active list.",
        epilog="Examples:\n  egdo future unmove 1\n  egdo future unmove 1 3 7",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    future_unmove_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo future`")

    done_parser = subparsers.add_parser(
        "done",
        help="Complete a task",
        description="Mark a task complete using the index shown by `egdo list`.",
        epilog="Examples:\n  egdo done 1\n  egdo done 1 3 12",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    done_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo list`")

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
            "  egdo move 1 6 7 tomorrow\n"
            "  egdo move 2 +3\n"
            "  egdo move 2 sunday\n"
            "  egdo move 2 2026-04-10"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    move_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo list`")
    move_parser.add_argument(
        "when",
        help="Future date: tomorrow, +N, weekday name, or YYYY-MM-DD",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description="Delete a task using the index shown by `egdo list`.",
        epilog="Examples:\n  egdo delete 2\n  egdo delete 1 6 7",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    delete_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo list`")

    tag_parser = subparsers.add_parser(
        "tag",
        help="Add or remove task tags",
        description="Add or remove tags from one or more tasks using their global indexes.",
        epilog=(
            "Examples:\n"
            "  egdo tag 3 chores home\n"
            "  egdo tag 1 6 7 chores home\n"
            "  egdo tag 3 6 7 --remove work"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    tag_parser.add_argument(
        "values",
        nargs="+",
        help="Task numbers followed by tags to add; with --remove, task numbers only",
    )
    tag_parser.add_argument("--remove", nargs="+", metavar="TAG", help="Remove tag(s)")

    priority_parser = subparsers.add_parser(
        "priority",
        help="Set or clear a task's priority",
        description="Set priority using the index shown by `egdo list`.",
        epilog="Examples:\n  egdo priority 1 6 7 high\n  egdo priority 3 none",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    priority_parser.add_argument("indexes", nargs="+", type=int, help="Task number(s) from `egdo list`")
    priority_parser.add_argument("level", help="1/critical, 2/high, 3/normal, 4/low, or none")

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
        help="Set a tag or priority color",
        description="Set the terminal style used for a tag or priority. Defaults to an interactive picker.",
        epilog=(
            "Examples:\n"
            "  egdo color --tag chores\n"
            "  egdo color --tag chores --style green_yellow\n"
            "  egdo color --tag chores home --style green_yellow\n"
            '  egdo color --priority high --style "bold orange1"\n\n'
            "Rich color reference:\n"
            "  https://rich.readthedocs.io/en/stable/appendix/colors.html"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    color_target = color_parser.add_mutually_exclusive_group(required=True)
    color_target.add_argument("--tag", nargs="+", help="Tag name(s) to style")
    color_target.add_argument(
        "--priority", nargs="+", help="Priorities to style: 1/critical, 2/high, 3/normal, or 4/low"
    )
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
            complete_tasks=complete_tasks,
            create_task=create_task,
            delete_tasks=delete_tasks,
            edit_task=edit_task,
            list_finished_tasks=list_finished_tasks,
            list_task_refs=list_task_refs,
            move_tasks=move_tasks,
            parse_future_date=_parse_future_date,
            prioritize_tasks=prioritize_tasks,
            render_list_header=_render_list_header,
            render_priority_style_picker=_render_priority_style_picker,
            render_separator=_render_separator,
            render_tag_style_picker=_render_tag_style_picker,
            render_task_line=_render_task_line,
            save_config=save_config,
            tag_tasks=tag_tasks,
            task_wrap_width=_task_wrap_width,
            untag_tasks=untag_tasks,
            unmove_tasks=unmove_tasks,
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
