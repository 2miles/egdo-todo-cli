"""Command-line parser, dependency wiring, and process-level error handling."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from egdo.config import (
    CONFIG_PATH,
    add_project,
    create_config,
    load_config,
    save_config,
    set_project_root,
    use_project,
)
from egdo.dates import parse_future_date as _parse_future_date
from egdo.handlers import HandlerDeps
from egdo.handlers import dispatch_command
from egdo.interactive import prompt_add_form, prompt_done_form
from egdo.store import (
    add_note,
    complete_tasks,
    create_task,
    delete_tasks,
    edit_task,
    list_completed_tasks,
    list_task_refs,
    move_tasks,
    prioritize_tasks,
    tag_tasks,
    untag_tasks,
)
from egdo.render import render_list_header as _render_list_header
from egdo.render import render_separator as _render_separator
from egdo.render import render_section_header as _render_section_header
from egdo.render import render_task_line as _render_task_line
from egdo.render import task_wrap_width as _task_wrap_width
from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

console = Console()


def build_parser() -> argparse.ArgumentParser:
    """Build the complete CLI grammar and its command-specific help text."""
    parser = argparse.ArgumentParser(
        prog="egdo",
        description="A rolling, Markdown-backed todo list. Run without a command to show your tasks.",
        epilog=(
            "Examples:\n"
            "  egdo\n"
            '  egdo add -p important -t work "Submit application"\n'
            '  egdo add --parent 6 "Add tests"\n'
            "  egdo done 1 3\n"
            "  egdo move 2 5 tomorrow\n"
            "  egdo priority 4 important\n\n"
            "Run `egdo COMMAND --help` for command-specific usage."
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    parser.add_argument(
        "-P",
        "--project",
        dest="selected_project",
        help="Use a named project for this command without changing the default",
    )
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        metavar="COMMAND",
        required=True,
        parser_class=argparse.ArgumentParser,
    )

    project_parser = subparsers.add_parser(
        "project",
        help="Manage named task roots",
        description="Add, list, relocate, or select independent egdo project roots.",
    )
    project_subparsers = project_parser.add_subparsers(
        dest="project_command",
        metavar="ACTION",
        required=True,
    )
    project_add_parser = project_subparsers.add_parser(
        "add", help="Add a named project root"
    )
    project_add_parser.add_argument("name", help="Display name, such as Minecraft")
    project_add_parser.add_argument("root", help="Directory containing the project's files")
    project_subparsers.add_parser("list", help="List configured projects")
    project_set_parser = project_subparsers.add_parser(
        "set", help="Change a project's root"
    )
    project_set_parser.add_argument("name", help="Configured project name")
    project_set_parser.add_argument("root", help="New directory for the project")
    project_use_parser = project_subparsers.add_parser(
        "use", help="Make a project the default"
    )
    project_use_parser.add_argument("name", help="Configured project name")

    add_parser = subparsers.add_parser(
        "add",
        help="Add a task",
        description="Add a task, or omit the text to open an interactive form.",
        epilog=(
            "Examples:\n  egdo add\n"
            '  egdo add "Buy milk"\n'
            '  egdo add -t chores "Do laundry"\n'
            '  egdo add -p important -t work "Submit application"\n'
            '  egdo add --parent 6 "Add tests"\n'
            '  egdo add "{CHORES} Do laundry"\n'
            '  egdo add --done -t errands "Call the DMV"\n'
            '  egdo add --done "Call dad"'
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    add_parser.add_argument("text", nargs="?", help="Task text; omit to open the add form")
    add_parser.add_argument(
        "-t",
        "--tag",
        help="Set the task's tag",
    )
    add_parser.add_argument(
        "-p",
        "--priority",
        help="Set priority: important or normal",
    )
    add_parser.add_argument("--done", action="store_true", help="Create the task already completed")
    add_parser.add_argument("--parent", help="Parent task ID, such as 6 or 6a")

    list_parser = subparsers.add_parser(
        "list",
        help="List tasks",
        description="List active, future, or completed tasks, optionally filtering by tag.",
        epilog=(
            "Examples:\n"
            "  egdo list\n"
            "  egdo list -t chores\n"
            "  egdo list --future\n"
            "  egdo list --future -t chores\n"
            "  egdo list --completed\n"
            "  egdo list --completed -t chores"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    list_parser.add_argument("-t", "--tag", help="Show only tasks with this leading tag")
    list_view = list_parser.add_mutually_exclusive_group()
    list_view.add_argument("--future", action="store_true", help="Show only future tasks")
    list_view.add_argument(
        "--completed", action="store_true", help="Show today's completed tasks"
    )

    done_parser = subparsers.add_parser(
        "done",
        help="Complete a task",
        description="Complete task IDs, or omit them to open an interactive form.",
        epilog="Examples:\n  egdo done\n  egdo done 1\n  egdo done 1 3 12",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    done_parser.add_argument(
        "indexes", nargs="*", help="Task ID(s); omit to open the completion form"
    )

    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit a task",
        description="Edit a task using the index shown by `egdo list`.",
        epilog='Example:\n  egdo edit 2 "Buy oat milk"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    edit_parser.add_argument("index", help="Task ID from `egdo list`")
    edit_parser.add_argument("text", help="Replacement task text")

    move_parser = subparsers.add_parser(
        "move",
        help="Move a task to another date",
        description="Move tasks to today or a future date using IDs shown by `egdo list`.",
        epilog=(
            "Examples:\n"
            "  egdo move 2 tomorrow\n"
            "  egdo move 7 today\n"
            "  egdo move 1 6 7 tomorrow\n"
            "  egdo move 2 +3\n"
            "  egdo move 2 sunday\n"
            "  egdo move 2 2026-04-10"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    move_parser.add_argument("indexes", nargs="+", help="Task ID(s) from `egdo list`")
    move_parser.add_argument(
        "when",
        help="Date: today, tomorrow, +N, weekday name, or YYYY-MM-DD",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description="Delete a task using the index shown by `egdo list`.",
        epilog="Examples:\n  egdo delete 2\n  egdo delete 1 6 7",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    delete_parser.add_argument("indexes", nargs="+", help="Task ID(s) from `egdo list`")

    tag_parser = subparsers.add_parser(
        "tag",
        help="Set or remove a task tag",
        description="Set or remove the tag on one or more tasks using their global indexes.",
        epilog=(
            "Examples:\n"
            "  egdo tag 3 chores\n"
            "  egdo tag 1 6 7 work\n"
            "  egdo tag 3 6 7 --remove"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    tag_parser.add_argument(
        "values",
        nargs="+",
        help="Task numbers followed by one tag; with --remove, task numbers only",
    )
    tag_parser.add_argument("--remove", action="store_true", help="Remove the current tag")

    priority_parser = subparsers.add_parser(
        "priority",
        help="Set a task's priority",
        description="Set priority using the index shown by `egdo list`.",
        epilog="Examples:\n  egdo priority 1 6 7 important\n  egdo priority 3 normal",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    priority_parser.add_argument("indexes", nargs="+", help="Task ID(s) from `egdo list`")
    priority_parser.add_argument("level", help="important or normal")

    note_parser = subparsers.add_parser(
        "note",
        help="Add a note for today",
        description="Append a note to today's Notes section.",
        epilog='Example:\n  egdo note "Need to test villager trading setup"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    note_parser.add_argument("text", help="Note text to append")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, load configuration, and dispatch one CLI invocation."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["list"]
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "project":
            try:
                config = load_config()
            except FileNotFoundError:
                config = None
            return _run_project(args, config)
        config = load_config()
        if args.selected_project is not None:
            config = config.select(args.selected_project)
        target_date = date.today()
        deps = HandlerDeps(
            add_note=add_note,
            complete_tasks=complete_tasks,
            create_task=create_task,
            delete_tasks=delete_tasks,
            edit_task=edit_task,
            list_completed_tasks=list_completed_tasks,
            list_task_refs=list_task_refs,
            move_tasks=move_tasks,
            parse_future_date=_parse_future_date,
            prompt_add_form=prompt_add_form,
            prompt_done_form=prompt_done_form,
            prioritize_tasks=prioritize_tasks,
            render_list_header=_render_list_header,
            render_separator=_render_separator,
            render_section_header=_render_section_header,
            render_task_line=_render_task_line,
            tag_tasks=tag_tasks,
            task_wrap_width=_task_wrap_width,
            untag_tasks=untag_tasks,
        )
        return dispatch_command(args, config, target_date, console, deps)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_project(args: argparse.Namespace, config: object | None) -> int:
    """Execute project-management commands without touching task archives."""
    if config is None:
        if args.project_command != "add":
            raise FileNotFoundError(
                "No projects configured. Run `egdo project add Main ~/Notes/egdo`."
            )
        created = create_config(args.name, Path(args.root).expanduser())
        save_config(created, CONFIG_PATH)
        print(f'Added project "{created.project_name}" at {created.root}')
        return 0
    if args.project_command == "list":
        for name, root in config.projects.items():
            marker = "*" if name == config.default_project else " "
            print(f"{marker} {name}: {root}")
        return 0
    if args.project_command == "add":
        updated = add_project(config, args.name, Path(args.root).expanduser())
        save_config(updated, CONFIG_PATH)
        print(f'Added project "{args.name.strip()}" at {Path(args.root).expanduser()}')
        return 0
    if args.project_command == "set":
        updated = set_project_root(config, args.name, Path(args.root).expanduser())
        save_config(updated, CONFIG_PATH)
        project_name = updated.select(args.name).project_name
        print(f'Updated project "{project_name}" to {updated.projects[project_name]}')
        return 0
    if args.project_command == "use":
        updated = use_project(config, args.name)
        save_config(updated, CONFIG_PATH)
        print(f'Using project "{updated.project_name}"')
        return 0
    raise ValueError(f"Unknown project action: {args.project_command}")


if __name__ == "__main__":
    raise SystemExit(main())
