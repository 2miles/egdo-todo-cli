"""Command-line parser, dependency wiring, and process-level error handling."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import sys

from egdo.config import (
    CONFIG_PATH,
    LOCAL_CONFIG_NAME,
    initialize_local_marker,
    load_config,
    read_local_project,
    register_initialized_project,
    save_config,
    select_project_for_directory,
    use_project,
)
from egdo.dates import parse_future_date as _parse_future_date
from egdo.handlers import HandlerDeps
from egdo.handlers import dispatch_command
from egdo.interactive import (
    prompt_add_form,
    prompt_delete_form,
    prompt_done_form,
    prompt_edit_form,
    prompt_move_form,
    prompt_note_form,
    prompt_priority_form,
    prompt_project_form,
    prompt_tag_form,
)
from egdo.store import (
    add_note,
    complete_tasks,
    create_task,
    delete_tasks,
    edit_task,
    list_completed_tasks,
    list_task_refs,
    list_task_refs_readonly,
    move_tasks,
    prioritize_tasks,
    tag_tasks,
    untag_tasks,
)
from egdo.render import render_list_header as _render_list_header
from egdo.render import render_project_line as _render_project_line
from egdo.render import render_separator as _render_separator
from egdo.render import render_section_header as _render_section_header
from egdo.render import render_task_line as _render_task_line
from egdo.render import task_wrap_width as _task_wrap_width
from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

console = Console()


class EgdoArgumentParser(argparse.ArgumentParser):
    """Normalize command shapes that argparse cannot express unambiguously."""

    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if getattr(parsed, "command", None) == "move":
            values = parsed.move_values
            if len(values) == 1 and re.fullmatch(
                r"\d+[a-z]{0,2}", values[0], re.IGNORECASE
            ):
                parsed.indexes, parsed.when = values, None
            else:
                parsed.indexes = values[:-1] if values else []
                parsed.when = values[-1] if values else None
        if getattr(parsed, "command", None) == "priority":
            values = parsed.priority_values
            if values and values[-1].casefold() in {"important", "normal"}:
                parsed.indexes, parsed.level = values[:-1], values[-1]
            else:
                parsed.indexes, parsed.level = values, None
        return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the complete CLI grammar and its command-specific help text."""
    parser = EgdoArgumentParser(
        prog="egdo",
        description=(
            "A rolling Markdown work journal. Run without a command to show your tasks."
        ),
        epilog=(
            "Examples:\n"
            "  egdo init Main\n"
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

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize an egdo project here",
        description=(
            "Initialize a named egdo project in the current directory. "
            "Creates .egdo.toml and uses ./egdo for its Markdown archive."
        ),
        epilog="Example:\n  cd ~/Notes\n  egdo init Main",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    init_parser.add_argument("name", help="Project display name, such as Main or Minecraft")

    project_parser = subparsers.add_parser(
        "project",
        help="Manage named task roots",
        description=(
            "Choose the global fallback interactively, list named projects, or select "
            "one directly."
        ),
        epilog=(
            "Examples:\n  egdo project\n  egdo project list\n"
            "  egdo project use Minecraft"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    project_subparsers = project_parser.add_subparsers(
        dest="project_command",
        metavar="[ACTION]",
    )
    project_subparsers.add_parser("list", help="List configured projects")
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
    list_parser.add_argument(
        "--all-projects",
        action="store_true",
        help=(
            "Read tasks from every project; cannot be combined with other list filters"
        ),
    )
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
        description="Choose and edit a task, or supply its ID and replacement text.",
        epilog='Examples:\n  egdo edit\n  egdo edit 2\n  egdo edit 2 "Buy oat milk"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    edit_parser.add_argument("index", nargs="?", help="Task ID from `egdo list`")
    edit_parser.add_argument("text", nargs="?", help="Replacement task text")

    move_parser = subparsers.add_parser(
        "move",
        help="Move a task to another date",
        description=(
            "Choose tasks and a date interactively, or supply IDs followed by a date."
        ),
        epilog=(
            "Examples:\n"
            "  egdo move\n"
            "  egdo move tomorrow\n"
            "  egdo move 2 tomorrow\n"
            "  egdo move 7 today\n"
            "  egdo move 1 6 7 tomorrow\n"
            "  egdo move 2 +3\n"
            "  egdo move 2 sunday\n"
            "  egdo move 2 2026-04-10"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    move_parser.add_argument(
        "move_values",
        nargs="*",
        metavar="ID... WHEN",
        help="Task ID(s) followed by today or a future date",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description="Choose and confirm tasks interactively, or supply their IDs.",
        epilog="Examples:\n  egdo delete\n  egdo delete 2\n  egdo delete 1 6 7",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    delete_parser.add_argument("indexes", nargs="*", help="Task ID(s) from `egdo list`")

    tag_parser = subparsers.add_parser(
        "tag",
        help="Set or remove a task tag",
        description="Choose tasks and a tag interactively, or supply IDs and a tag.",
        epilog=(
            "Examples:\n"
            "  egdo tag\n"
            "  egdo tag 3\n"
            "  egdo tag 3 chores\n"
            "  egdo tag 1 6 7 work\n"
            "  egdo tag 3 6 7 --remove"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    tag_parser.add_argument(
        "values",
        nargs="*",
        help="Task numbers followed by one tag; with --remove, task numbers only",
    )
    tag_parser.add_argument("--remove", action="store_true", help="Remove the current tag")

    priority_parser = subparsers.add_parser(
        "priority",
        help="Set a task's priority",
        description="Choose tasks and priority interactively, or supply both directly.",
        epilog=(
            "Examples:\n  egdo priority\n  egdo priority 3\n"
            "  egdo priority 1 6 7 important\n  egdo priority 3 normal"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    priority_parser.add_argument(
        "priority_values",
        nargs="*",
        metavar="ID... LEVEL",
        help="Task ID(s) followed by important or normal",
    )

    note_parser = subparsers.add_parser(
        "note",
        help="Add a note for today",
        description="Prompt for or directly append a note to today's Notes section.",
        epilog=(
            'Examples:\n  egdo note\n'
            '  egdo note "Need to test villager trading setup"'
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    note_parser.add_argument(
        "text", nargs="?", help="Note text; omit to open your editor"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, load configuration, and dispatch one CLI invocation."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["list"]
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            try:
                config = load_config()
            except FileNotFoundError:
                config = None
            return _run_init(args.name, config, _current_directory())
        if args.command == "project":
            try:
                config = load_config()
            except FileNotFoundError:
                config = None
            return _run_project(args, config)
        config = load_config()
        if not (args.command == "list" and args.all_projects):
            config, registry_changed = select_project_for_directory(
                config, args.selected_project, _current_directory()
            )
            if registry_changed:
                save_config(config, CONFIG_PATH)
        target_date = date.today()
        deps = HandlerDeps(
            add_note=add_note,
            complete_tasks=complete_tasks,
            create_task=create_task,
            delete_tasks=delete_tasks,
            edit_task=edit_task,
            list_completed_tasks=list_completed_tasks,
            list_task_refs=list_task_refs,
            list_task_refs_readonly=list_task_refs_readonly,
            move_tasks=move_tasks,
            parse_future_date=_parse_future_date,
            prompt_add_form=prompt_add_form,
            prompt_delete_form=prompt_delete_form,
            prompt_done_form=prompt_done_form,
            prompt_edit_form=prompt_edit_form,
            prompt_move_form=prompt_move_form,
            prompt_note_form=prompt_note_form,
            prompt_priority_form=prompt_priority_form,
            prompt_tag_form=prompt_tag_form,
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
        raise FileNotFoundError(
            "No projects configured. Run `egdo init Main` in your notes directory."
        )
    if args.project_command == "list":
        console.print()
        for name, root in config.projects.items():
            console.print(
                _render_project_line(
                    name, str(root), is_default=name == config.default_project
                )
            )
        return 0
    if args.project_command is None:
        name = prompt_project_form(config, console)
        if name is None:
            console.print("Canceled project selection.")
            return 0
        updated = use_project(config, name)
        save_config(updated, CONFIG_PATH)
        console.print(f'Using project "{updated.project_name}"')
        return 0
    if args.project_command == "use":
        updated = use_project(config, args.name)
        save_config(updated, CONFIG_PATH)
        print(f'Using project "{updated.project_name}"')
        return 0
    raise ValueError(f"Unknown project action: {args.project_command}")


def _run_init(name: str, config: object | None, directory: Path) -> int:
    """Initialize or adopt a project in the current directory."""
    marker_path = directory.resolve() / LOCAL_CONFIG_NAME
    if marker_path.exists():
        existing = read_local_project(marker_path)
        if existing.name.casefold() != name.strip().casefold():
            raise ValueError(
                f'{marker_path} already identifies project "{existing.name}"'
            )
        name = existing.name

    root = directory.resolve() / "egdo"
    updated, config_changed = register_initialized_project(config, name, root)
    initialized_root, marker_created = initialize_local_marker(directory, name)
    if config_changed:
        save_config(updated, CONFIG_PATH)

    project_name = updated.select(name).project_name
    if not config_changed and not marker_created:
        print(f'Project "{project_name}" is already initialized at {initialized_root}')
    else:
        print(f'Initialized egdo project "{project_name}" in {initialized_root}')
    return 0


def _current_directory() -> Path:
    """Return the process working directory through an easy-to-test boundary."""
    return Path.cwd()


if __name__ == "__main__":
    raise SystemExit(main())
