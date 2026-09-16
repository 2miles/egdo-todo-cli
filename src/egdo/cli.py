"""Command-line parsing, process setup, and error handling."""

from __future__ import annotations

import argparse
import calendar
from datetime import date
import os
from pathlib import Path
import re
import sys

from egdo import __version__
from egdo.config import (
    CONFIG_PATH,
    LOCAL_CONFIG_NAME,
    initialize_local_marker,
    load_config,
    read_local_project,
    register_initialized_project,
    remove_project,
    save_config,
    use_project,
)
from egdo.handlers import dispatch_command
from egdo.interactive import (
    open_editor,
    prompt_project_form,
)
from egdo.markdown_store import file_path
from egdo.render import render_confirmation as _render_confirmation
from egdo.render import render_project_line as _render_project_line
from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

console = Console()


class EgdoArgumentParser(argparse.ArgumentParser):
    """Normalize command shapes that argparse cannot express unambiguously."""

    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if getattr(parsed, "command", None) == "move":
            values = parsed.move_values
            if len(values) == 1 and re.fullmatch(r"\d+[a-z]{0,2}", values[0], re.IGNORECASE):
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
        description=("A rolling Markdown work journal. Run without a command to show your tasks."),
        epilog=(
            "Examples:\n"
            "  egdo init Main\n"
            "  egdo\n"
            '  egdo add -p important -t work "Submit application"\n'
            '  egdo add --parent 6 "Add tests"\n'
            "  egdo done 1 3\n"
            "  egdo move 2 5 tomorrow\n"
            "  egdo priority 4 important\n"
            "  egdo -P Minecraft list\n\n"
            "Run `egdo COMMAND --help` for command-specific usage."
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    parser.add_argument(
        "-P",
        "--project",
        dest="selected_project",
        metavar="NAME",
        help="Use a named project for this command without changing the active project",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show a traceback when a command fails",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the installed version and exit",
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
    init_parser.add_argument("name", metavar="NAME", help="Display name, such as Main or Minecraft")

    project_parser = subparsers.add_parser(
        "project",
        help="Manage projects",
        description=(
            "Choose the active project interactively, or use an action to list, select, "
            "or unregister configured projects."
        ),
        epilog=(
            "Examples:\n  egdo project\n  egdo project list\n"
            "  egdo project use Minecraft\n"
            "  egdo project remove Demo"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    project_subparsers = project_parser.add_subparsers(
        dest="project_command",
        metavar="[ACTION]",
    )
    project_subparsers.add_parser(
        "list",
        help="List configured projects",
        description="List every configured project and mark the active one.",
        epilog="Example:\n  egdo project list",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    project_use_parser = project_subparsers.add_parser(
        "use",
        help="Make a project active",
        description="Make one configured project the default for future commands.",
        epilog="Example:\n  egdo project use Minecraft",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    project_use_parser.add_argument("name", metavar="NAME", help="Configured project name")
    project_remove_parser = project_subparsers.add_parser(
        "remove",
        help="Unregister a project without deleting its files",
        description=(
            "Unregister a configured project without deleting its Markdown archive. "
            "Confirmation is required unless --force is supplied."
        ),
        epilog=("Examples:\n" "  egdo project remove Demo\n" "  egdo project remove Demo --force"),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    project_remove_parser.add_argument("name", metavar="NAME", help="Configured project name")
    project_remove_parser.add_argument(
        "--force",
        action="store_true",
        help="Remove without an interactive confirmation",
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Add a task",
        description=(
            "Add a task directly, or omit TEXT to choose its text, tag, priority, and "
            "schedule interactively."
        ),
        epilog=(
            "Examples:\n  egdo add\n"
            '  egdo add "Buy milk"\n'
            '  egdo add -t chores "Do laundry"\n'
            '  egdo add -p important -t work "Submit application"\n'
            '  egdo add --parent 6 "Add tests"\n'
            '  egdo add --done "Call dad"'
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    add_parser.add_argument(
        "text", nargs="?", metavar="TEXT", help="Task text; omit to open the add form"
    )
    add_parser.add_argument(
        "-t",
        "--tag",
        metavar="TAG",
        help="Set one leading task tag",
    )
    add_parser.add_argument(
        "-p",
        "--priority",
        metavar="LEVEL",
        help="Set priority: important or normal",
    )
    add_parser.add_argument("--done", action="store_true", help="Create the task already completed")
    add_parser.add_argument(
        "--parent", metavar="ID", help="Create under a parent task, such as 6 or 6a"
    )

    list_parser = subparsers.add_parser(
        "list",
        help="List tasks",
        description=(
            "List today's active tasks by default, or show future, completed, or "
            "all-project views."
        ),
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
    list_parser.add_argument(
        "-t", "--tag", metavar="TAG", help="Show only tasks with this leading tag"
    )
    list_parser.add_argument(
        "--all-projects",
        action="store_true",
        help=("Read tasks from every project; cannot be combined with other list filters"),
    )
    list_view = list_parser.add_mutually_exclusive_group()
    list_view.add_argument("--future", action="store_true", help="Show only future tasks")
    list_view.add_argument("--completed", action="store_true", help="Show today's completed tasks")

    search_parser = subparsers.add_parser(
        "search",
        help="Search archived tasks",
        description=(
            "Search tasks and notes case-insensitively across the selected project's archive. "
            "Results are read-only and grouped by date."
        ),
        epilog=(
            "Examples:\n"
            "  egdo search dentist\n"
            "  egdo search --tag work\n"
            "  egdo search --completed application\n"
            "  egdo search dentist --notes\n"
            "  egdo search dentist --all-projects"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    search_parser.add_argument(
        "query", nargs="?", metavar="TEXT", help="Text to find in task descriptions"
    )
    search_parser.add_argument(
        "-t", "--tag", metavar="TAG", help="Show only tasks with this leading tag"
    )
    search_parser.add_argument(
        "--completed", action="store_true", help="Show only completed matches"
    )
    search_kind = search_parser.add_mutually_exclusive_group()
    search_kind.add_argument("--tasks", action="store_true", help="Search task text only")
    search_kind.add_argument("--notes", action="store_true", help="Search note paragraphs only")
    search_parser.add_argument(
        "--all-projects", action="store_true", help="Search every configured project"
    )

    done_parser = subparsers.add_parser(
        "done",
        help="Complete a task",
        description=(
            "Complete one or more IDs shown by egdo list, or omit IDs to choose tasks "
            "interactively."
        ),
        epilog="Examples:\n  egdo done\n  egdo done 1\n  egdo done 1 3 12",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    done_parser.add_argument(
        "indexes",
        nargs="*",
        metavar="ID",
        help="Task IDs; omit to open the completion form",
    )

    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit a task",
        description=(
            "Choose a task interactively, supply an ID and then enter text, or provide "
            "both values directly."
        ),
        epilog='Examples:\n  egdo edit\n  egdo edit 2\n  egdo edit 2 "Buy oat milk"',
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    edit_parser.add_argument("index", nargs="?", metavar="ID", help="Task ID shown by egdo list")
    edit_parser.add_argument("text", nargs="?", metavar="TEXT", help="Replacement task text")

    move_parser = subparsers.add_parser(
        "move",
        help="Move a task to another date",
        description=(
            "Move tasks to a future date, or move future tasks back to today. Supply IDs "
            "followed by WHEN, or omit either part to choose it interactively."
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
        metavar="ID_OR_WHEN",
        help="Task IDs, then today, tomorrow, +N, weekday, or YYYY-MM-DD",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description=(
            "Permanently remove tasks and their subtasks. Choose and confirm tasks "
            "interactively, or supply IDs directly."
        ),
        epilog="Examples:\n  egdo delete\n  egdo delete 2\n  egdo delete 1 6 7",
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    delete_parser.add_argument(
        "indexes", nargs="*", metavar="ID", help="Task IDs shown by egdo list"
    )

    tag_parser = subparsers.add_parser(
        "tag",
        help="Set or remove a task tag",
        description=(
            "Set one tag on selected tasks, replacing any current tag. Missing IDs or "
            "the tag are collected interactively."
        ),
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
        metavar="ID_OR_TAG",
        help="Task IDs, then one tag; with --remove, task IDs only",
    )
    tag_parser.add_argument("--remove", action="store_true", help="Remove the current tag")

    priority_parser = subparsers.add_parser(
        "priority",
        help="Set a task's priority",
        description=(
            "Mark selected tasks important or normal. Missing IDs or the level are "
            "collected interactively."
        ),
        epilog=(
            "Examples:\n  egdo priority\n  egdo priority 3\n"
            "  egdo priority 1 6 7 important\n  egdo priority 3 normal"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    priority_parser.add_argument(
        "priority_values",
        nargs="*",
        metavar="ID_OR_LEVEL",
        help="Task IDs followed by important or normal",
    )

    note_parser = subparsers.add_parser(
        "note",
        help="Add a note for today",
        description=(
            "Append text to today's Notes section, or omit TEXT to compose a multiline "
            "note in $VISUAL or $EDITOR."
        ),
        epilog=("Examples:\n  egdo note\n" '  egdo note "Need to test villager trading setup"'),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    note_parser.add_argument(
        "text", nargs="?", metavar="TEXT", help="Note text; omit to open your editor"
    )

    open_parser = subparsers.add_parser(
        "open",
        help="Open a monthly Markdown file",
        description=(
            "Open a project's monthly Markdown file in $VISUAL, $EDITOR, or vi. "
            "With no month, open the current month."
        ),
        epilog=(
            "Examples:\n"
            "  egdo open\n"
            "  egdo open 2026-01\n"
            "  egdo open jan\n"
            "  egdo open jan 2026\n"
            "  egdo open January 2026"
        ),
        formatter_class=RawDescriptionRichHelpFormatter,
    )
    open_parser.add_argument(
        "month_values",
        nargs="*",
        metavar="MONTH",
        help="YYYY-MM, a month name, or a month name followed by a year",
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
            _configure_console(config)
            return _run_init(args.name, config, _current_directory())
        if args.command == "project":
            try:
                config = load_config()
            except FileNotFoundError:
                config = None
            _configure_console(config)
            return _run_project(args, config)
        config = load_config()
        _configure_console(config)
        if not (args.command in {"list", "search"} and getattr(args, "all_projects", False)):
            if args.selected_project is not None:
                config = config.select(args.selected_project)
        target_date = date.today()
        if args.command == "open":
            return _run_open(args.month_values, config, target_date)
        return dispatch_command(args, config, target_date, console)
    except Exception as exc:  # noqa: BLE001
        if args.debug:
            raise
        print(f"egdo: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_open(month_values: list[str], config: object, today: date) -> int:
    """Open the selected project's requested monthly Markdown file."""
    selected_month = _parse_open_month(month_values, today)
    path = file_path(config.root, selected_month)
    path.parent.mkdir(parents=True, exist_ok=True)
    open_editor(path)
    return 0


def _parse_open_month(values: list[str], today: date) -> date:
    """Parse the friendly month forms accepted by ``egdo open``."""
    if not values:
        return today.replace(day=1)
    if len(values) == 1:
        iso_match = re.fullmatch(r"(\d{4})-(\d{2})", values[0])
        if iso_match:
            return _replace_month(today, int(iso_match[1]), int(iso_match[2]))
        month = _month_number(values[0])
        if month is not None:
            return today.replace(month=month, day=1)
    elif len(values) == 2:
        month = _month_number(values[0])
        if month is not None and re.fullmatch(r"\d{4}", values[1]):
            return _replace_month(today, int(values[1]), month)
    raise ValueError("Invalid month. Use YYYY-MM, MONTH, or MONTH YYYY, such as `jan 2026`.")


def _month_number(value: str) -> int | None:
    normalized = value.casefold()
    for month in range(1, 13):
        if normalized in {
            calendar.month_abbr[month].casefold(),
            calendar.month_name[month].casefold(),
        }:
            return month
    return None


def _replace_month(today: date, year: int, month: int) -> date:
    try:
        return today.replace(year=year, month=month, day=1)
    except ValueError as exc:
        raise ValueError(
            "Invalid month. Use YYYY-MM, MONTH, or MONTH YYYY, such as `jan 2026`."
        ) from exc


def _configure_console(config: object | None) -> None:
    """Apply persistent display preferences while honoring NO_COLOR."""
    color_enabled = True if config is None else getattr(config, "color", True)
    console.no_color = not color_enabled or os.environ.get("NO_COLOR", "") != ""


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
                _render_project_line(name, str(root), is_active=name == config.active_project)
            )
        return 0
    if args.project_command is None:
        name = prompt_project_form(config, console)
        if name is None:
            console.print("Canceled project selection.")
            return 0
        updated = use_project(config, name)
        save_config(updated, CONFIG_PATH)
        console.print(_render_confirmation("Selected project", updated.project_name))
        return 0
    if args.project_command == "use":
        updated = use_project(config, args.name)
        save_config(updated, CONFIG_PATH)
        console.print(_render_confirmation("Selected project", updated.project_name))
        return 0
    if args.project_command == "remove":
        project_name = config.select(args.name).project_name
        assert project_name is not None
        if not args.force and not _confirm_project_removal(project_name):
            console.print("Canceled project removal.")
            return 0
        updated = remove_project(config, project_name)
        save_config(updated, CONFIG_PATH)
        console.print(
            _render_confirmation("Unregistered project", project_name, detail="files kept")
        )
        return 0
    raise ValueError(f"Unknown project action: {args.project_command}")


def _run_init(name: str, config: object | None, directory: Path) -> int:
    """Initialize or adopt a project in the current directory."""
    marker_path = directory.resolve() / LOCAL_CONFIG_NAME
    if marker_path.exists():
        existing = read_local_project(marker_path)
        if existing.name.casefold() != name.strip().casefold():
            raise ValueError(f"{marker_path} already identifies project “{existing.name}”")
        name = existing.name

    root = directory.resolve() / "egdo"
    updated, config_changed = register_initialized_project(config, name, root)
    initialized_root, marker_created = initialize_local_marker(directory, name)
    if config_changed:
        save_config(updated, CONFIG_PATH)

    project_name = updated.select(name).project_name
    if not config_changed and not marker_created:
        console.print(f"Project “{project_name}” is already initialized at {initialized_root}.")
    else:
        console.print(
            _render_confirmation("Initialized project", project_name, detail=str(initialized_root))
        )
    return 0


def _current_directory() -> Path:
    """Return the process working directory through an easy-to-test boundary."""
    return Path.cwd()


def _confirm_project_removal(name: str) -> bool:
    """Confirm an unregister operation, requiring --force outside a terminal."""
    if not sys.stdin.isatty():
        raise ValueError(
            "Project removal requires confirmation in a terminal; use --force to continue"
        )
    answer = input(f"Unregister project “{name}”? Its files will not be deleted. [y/N] ")
    return answer.strip().casefold() in {"y", "yes"}


if __name__ == "__main__":
    raise SystemExit(main())
