"""Interactive terminal forms for commands that can collect missing arguments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any, Callable

from egdo.markdown_store import normalize_priority
from egdo.terminal_keys import read_picker_key
from rich.console import Console, Group
from rich.text import Text


FOCUS_MARKER = "› "
MULTI_SELECTED = "■ "
MULTI_UNSELECTED = "□ "
SINGLE_SELECTED = "● "
SINGLE_UNSELECTED = "○ "


def _picker_hint(*bindings: tuple[str, str]) -> Text:
    """Render reusable key/action help with visually distinct keys."""
    hint = Text()
    for position, (keys, action) in enumerate(bindings):
        if position:
            hint.append("  •  ", style="dim")
        hint.append(keys, style="bright_white")
        hint.append(f" {action}", style="dim")
    return hint


@dataclass(frozen=True, slots=True)
class AddFormResult:
    """Values collected by the interactive add form."""

    text: str
    tag: str | None
    priority: str | None
    scheduled: date


@dataclass(frozen=True, slots=True)
class EditFormResult:
    identifier: str
    text: str


@dataclass(frozen=True, slots=True)
class MoveFormResult:
    identifiers: list[str]
    scheduled: date


@dataclass(frozen=True, slots=True)
class TagFormResult:
    identifiers: list[str]
    tag: str | None


@dataclass(frozen=True, slots=True)
class PriorityFormResult:
    identifiers: list[str]
    priority: str


def prompt_done_form(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str = "Main",
) -> list[str]:
    """Select globally indexed tasks with a keyboard-driven multi-select picker."""
    return _prompt_task_multiselect(
        refs, today, console, project_name, "Complete tasks", "Complete"
    )


def _prompt_task_multiselect(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str,
    title: str,
    action: str,
) -> list[str]:
    """Select one or more project-local task identifiers."""
    if not sys.stdin.isatty():
        raise ValueError(
            f"Interactive {title.lower()} requires a TTY. Supply task IDs directly."
        )
    if not refs:
        raise ValueError("No active tasks available.")

    selected: set[str] = set()
    cursor = 0
    warning = False
    with console.screen(hide_cursor=True) as screen:
        while True:
            rows = [
                Text(f"Project: {project_name}", style="bold cyan"),
                Text(title, style="bold"),
                _picker_hint(
                    ("↑/↓ j/k", "Move"),
                    ("Space", "Toggle"),
                    ("Enter", action),
                    ("q/Esc", "Cancel"),
                ),
                Text(""),
            ]
            for index, ref in enumerate(refs):
                identifier = ref.identifier.lower()
                inherited = _selected_ancestor(identifier, selected)
                checked = identifier in selected or inherited is not None
                row = Text(
                    FOCUS_MARKER if index == cursor else "  ",
                    style="bold bright_white" if index == cursor else "dim",
                )
                row.append(
                    MULTI_SELECTED if checked else MULTI_UNSELECTED,
                    style="green" if checked else "dim",
                )
                row.append(f"{ref.identifier:>5}. ")
                row.append("  " * getattr(ref.task, "depth", 0))
                row.append(ref.task.text, style="dim" if inherited else None)
                schedule = "today" if ref.scheduled == today else ref.scheduled.isoformat()
                row.append(f" ({schedule})", style="dim")
                if inherited:
                    row.append(f" via {inherited}", style="dim")
                rows.append(row)
            if warning:
                rows.extend([Text(""), Text("Select at least one task before continuing.", style="yellow")])
            screen.update(Group(*rows))
            key = read_picker_key()
            if key == "up":
                cursor = (cursor - 1) % len(refs)
            elif key == "down":
                cursor = (cursor + 1) % len(refs)
            elif key == "toggle":
                identifier = refs[cursor].identifier.lower()
                if _selected_ancestor(identifier, selected) is not None:
                    continue
                if identifier in selected:
                    selected.remove(identifier)
                else:
                    selected = {
                        chosen for chosen in selected if not _is_descendant(chosen, identifier)
                    }
                    selected.add(identifier)
                warning = False
            elif key == "enter":
                if selected:
                    return [
                        ref.identifier
                        for ref in refs
                        if ref.identifier.lower() in selected
                    ]
                warning = True
            elif key in {"escape", "quit"}:
                return []


def _prompt_task_single(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str,
    title: str,
) -> str | None:
    """Choose exactly one task using the shared picker grammar."""
    if not sys.stdin.isatty():
        raise ValueError(f"Interactive {title.lower()} requires a TTY.")
    if not refs:
        raise ValueError("No active tasks available.")
    labels = []
    for ref in refs:
        schedule = "today" if ref.scheduled == today else ref.scheduled.isoformat()
        indent = "  " * getattr(ref.task, "depth", 0)
        labels.append(f"{ref.identifier:>5}. {indent}{ref.task.text} ({schedule})")
    choice = _run_single_picker(
        console, title, labels, 0, context=f"Project: {project_name}"
    )
    return None if choice is None else refs[choice].identifier


def prompt_project_form(config: Any, console: Console) -> str | None:
    """Choose the persistent default project."""
    if not sys.stdin.isatty():
        raise ValueError("Interactive project selection requires a TTY.")
    names = list(config.projects)
    selected = names.index(config.default_project)
    choice = _run_single_picker(console, "Choose default project", names, selected)
    return None if choice is None else names[choice]


NOTE_INSTRUCTIONS = "<!-- egdo:note-instructions -->"


def prompt_note_form(
    console: Console, project_name: str, today: date
) -> str | None:
    """Collect a multiline Markdown note using the user's terminal editor."""
    if not sys.stdin.isatty():
        raise ValueError('Interactive note requires a TTY. Use `egdo note "TEXT"`.')
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    command = shlex.split(editor)
    if not command:
        raise ValueError("VISUAL or EDITOR must name an editor command")
    template = (
        "\n"
        f"{NOTE_INSTRUCTIONS}\n"
        "Write the note above this line. Save and close to add it.\n"
        "Leave it empty to cancel. Markdown and line breaks are preserved.\n"
        f"Project: {project_name}\n"
        f"Date: {today.isoformat()}\n"
    )
    descriptor, raw_path = tempfile.mkstemp(prefix="egdo-note-", suffix=".md")
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(template)
        try:
            result = subprocess.run([*command, str(path)], check=False)
        except OSError as exc:
            raise RuntimeError(f"Could not open editor {command[0]!r}: {exc}") from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"Editor {command[0]!r} exited with status {result.returncode}"
            )
        content = path.read_text(encoding="utf-8")
        note = content.split(NOTE_INSTRUCTIONS, 1)[0].strip()
        return note or None
    finally:
        path.unlink(missing_ok=True)


def prompt_edit_form(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str,
    initial_identifier: str | None = None,
) -> EditFormResult | None:
    """Choose a task and collect its replacement text."""
    identifier = initial_identifier or _prompt_task_single(
        refs, today, console, project_name, "Edit task"
    )
    if identifier is None:
        return None
    text = _prompt_required(console, "New text")
    return None if text is None else EditFormResult(identifier, text)


def prompt_move_form(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str,
    parse_future_date: Callable[[str, date], date],
    initial_identifiers: list[str] | None = None,
    initial_scheduled: date | None = None,
) -> MoveFormResult | None:
    """Choose tasks and a destination date."""
    identifiers = initial_identifiers or _prompt_task_multiselect(
        refs, today, console, project_name, "Move tasks", "Continue"
    )
    if not identifiers:
        return None
    scheduled = initial_scheduled or _choose_schedule(
        console, today, parse_future_date
    )
    return None if scheduled is None else MoveFormResult(identifiers, scheduled)


def prompt_delete_form(
    refs: list[Any], today: date, console: Console, project_name: str
) -> list[str]:
    """Choose tasks and explicitly confirm their deletion."""
    identifiers = _prompt_task_multiselect(
        refs, today, console, project_name, "Delete tasks", "Continue"
    )
    if not identifiers:
        return []
    choice = _run_single_picker(
        console,
        "Confirm deletion",
        ["Keep tasks", f"Delete {len(identifiers)} selected task(s)"],
        0,
    )
    return identifiers if choice == 1 else []


def prompt_tag_form(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str,
    known_tags: list[str],
    remove_only: bool = False,
    initial_identifiers: list[str] | None = None,
) -> TagFormResult | None:
    """Choose tasks and then choose, create, or remove their tag."""
    identifiers = initial_identifiers or _prompt_task_multiselect(
        refs, today, console, project_name, "Tag tasks", "Continue"
    )
    if not identifiers:
        return None
    if remove_only:
        return TagFormResult(identifiers, None)
    tag = _choose_tag(console, known_tags, None)
    return None if tag is _CANCELED else TagFormResult(identifiers, tag)


def prompt_priority_form(
    refs: list[Any],
    today: date,
    console: Console,
    project_name: str,
    initial_identifiers: list[str] | None = None,
) -> PriorityFormResult | None:
    """Choose tasks and a priority level."""
    identifiers = initial_identifiers or _prompt_task_multiselect(
        refs, today, console, project_name, "Prioritize tasks", "Continue"
    )
    if not identifiers:
        return None
    priority = _choose_priority(console, None)
    return (
        None
        if priority is _CANCELED
        else PriorityFormResult(identifiers, str(priority))
    )


def _parent_identifier(identifier: str) -> str | None:
    if "." in identifier:
        return identifier.rsplit(".", 1)[0]
    original = identifier
    while identifier and identifier[-1].isalpha():
        identifier = identifier[:-1]
    return identifier if identifier != original else None


def _selected_ancestor(identifier: str, selected: set[str]) -> str | None:
    parent = _parent_identifier(identifier)
    while parent is not None:
        if parent in selected:
            return parent
        parent = _parent_identifier(parent)
    return None


def _is_descendant(identifier: str, possible_parent: str) -> bool:
    return _selected_ancestor(identifier, {possible_parent}) is not None


def prompt_add_form(
    config: Any,
    today: date,
    console: Console,
    parse_future_date: Callable[[str, date], date],
    initial_tag: str | None = None,
    initial_priority: str | None = None,
    known_tags: list[str] | None = None,
) -> AddFormResult | None:
    """Collect task text, tags, priority, and schedule from a terminal."""
    if not sys.stdin.isatty():
        raise ValueError('Interactive add requires a TTY. Use `egdo add "TASK"`.')

    project_name = getattr(config, "project_name", "Main")
    console.print(Text(f"\nProject: {project_name}", style="bold cyan"))
    console.print(Text("Add a task", style="bold"))
    console.print(Text("─" * 32, style="dim"))
    text = _prompt_required(console, "Task")
    if text is None:
        return None
    tag = _choose_tag(console, known_tags or [], initial_tag)
    if tag is _CANCELED:
        return None
    priority = _choose_priority(console, initial_priority)
    if priority is _CANCELED:
        return None
    scheduled = _choose_schedule(console, today, parse_future_date)
    if scheduled is None:
        return None
    return AddFormResult(text, tag, priority, scheduled)


def _prompt_required(console: Console, label: str) -> str | None:
    while True:
        value = console.input(
            f"[bold]{label}[/] [dim](/cancel to cancel)[/]: "
        ).strip()
        if value.casefold() == "/cancel":
            return None
        if value:
            return value
        console.print(f"{label} is required.", style="yellow")


_CANCELED = object()


def _choose_tag(
    console: Console, known_tags: list[str], initial: str | None
) -> str | None | object:
    tags = sorted({tag.lower() for tag in known_tags} | ({initial.lower()} if initial else set()))
    selected = initial.lower() if initial else None
    cursor = 0
    while True:
        action, cursor, selected = _run_tag_picker(
            console, tags, selected, cursor
        )
        if action == "cancel":
            return _CANCELED
        if action == "done":
            return selected
        if action == "new":
            new_tag = console.input(
                "New tag [dim](/cancel to cancel)[/]: "
            ).strip()
            if new_tag.casefold() == "/cancel":
                return _CANCELED
            new_tag = new_tag.strip("{}").strip().lower()
            if new_tag:
                if new_tag not in tags:
                    tags.append(new_tag)
                    tags.sort()
                selected = new_tag
                cursor = tags.index(new_tag) + 1
            continue


def _run_tag_picker(
    console: Console,
    tags: list[str],
    selected: str | None,
    cursor: int,
) -> tuple[str, int, str | None]:
    item_count = len(tags) + 2
    with console.screen(hide_cursor=True) as screen:
        while True:
            rows = [
                Text("Choose a tag", style="bold"),
                _picker_hint(
                    ("↑/↓ j/k", "Move"),
                    ("Space", "Select"),
                    ("Enter", "Continue"),
                    ("n", "New"),
                    ("q/Esc", "Cancel"),
                ),
                Text(""),
            ]
            labels = ["No tag", *tags, "Create a new tag…"]
            for index, label in enumerate(labels):
                focused = index == cursor
                row = Text(
                    FOCUS_MARKER if focused else "  ",
                    style="bold bright_white" if focused else "dim",
                )
                if index == 0:
                    checked = selected is None
                elif index == len(labels) - 1:
                    row.append("+ ", style="bright_cyan" if focused else "cyan")
                    row.append(label, style="bold bright_cyan" if focused else None)
                    rows.append(row)
                    continue
                else:
                    checked = label == selected
                row.append(
                    SINGLE_SELECTED if checked else SINGLE_UNSELECTED,
                    style="green" if checked else "dim",
                )
                label_style = None
                if index:
                    label_style = "bold bright_cyan" if focused else "dim cyan"
                elif focused:
                    label_style = "bold bright_white"
                row.append(label.upper() if index else label, style=label_style)
                rows.append(row)
            screen.update(Group(*rows))
            key = read_picker_key()
            if key == "up":
                cursor = (cursor - 1) % item_count
            elif key == "down":
                cursor = (cursor + 1) % item_count
            elif key in {"new"} or (key in {"enter", "toggle"} and cursor == item_count - 1):
                return ("new", cursor, selected)
            elif key == "toggle":
                if cursor == 0:
                    selected = None
                else:
                    selected = tags[cursor - 1]
            elif key == "enter":
                return ("done", cursor, selected)
            elif key in {"escape", "quit"}:
                return ("cancel", cursor, selected)


def _choose_priority(console: Console, initial: str | None) -> str | None | object:
    values = ["normal", "important"]
    labels = ["Normal", "Important"]
    selected = 0
    if initial is not None:
        priority = normalize_priority(initial)
        selected = 1 if priority else 0
    choice = _run_single_picker(console, "Choose priority", labels, selected)
    return _CANCELED if choice is None else values[choice]


def _choose_schedule(
    console: Console, today: date, parse_future_date: Callable[[str, date], date]
) -> date | None:
    dates = [today, today + timedelta(days=1)]
    labels = ["Today", "Tomorrow"]
    for offset in range(2, 9):
        candidate = today + timedelta(days=offset)
        labels.append(f"{candidate:%A (%b} {candidate.day})")
        dates.append(candidate)
    labels.append("Enter another date…")
    choice = _run_single_picker(console, "Schedule task", labels, 0)
    if choice is None:
        return None
    if choice < len(dates):
        return dates[choice]
    while True:
        value = console.input(
            "Schedule (tomorrow, +N, weekday, or YYYY-MM-DD; /cancel to cancel): "
        ).strip()
        if value.casefold() == "/cancel":
            return None
        try:
            return parse_future_date(value, today)
        except ValueError as exc:
            console.print(str(exc), style="yellow")


def _run_single_picker(
    console: Console,
    title: str,
    labels: list[str],
    selected: int,
    context: str | None = None,
) -> int | None:
    with console.screen(hide_cursor=True) as screen:
        while True:
            rows = [
                *([Text(context, style="bold cyan")] if context else []),
                Text(title, style="bold"),
                _picker_hint(
                    ("↑/↓ j/k", "Move"),
                    ("Enter", "Select"),
                    ("q/Esc", "Cancel"),
                ),
                Text(""),
            ]
            for index, label in enumerate(labels):
                focused = index == selected
                row = Text(
                    FOCUS_MARKER if focused else "  ",
                    style="bold bright_white" if focused else "dim",
                )
                row.append(
                    SINGLE_SELECTED if focused else SINGLE_UNSELECTED,
                    style="green" if focused else "dim",
                )
                row.append(label)
                rows.append(row)
            screen.update(Group(*rows))
            key = read_picker_key()
            if key == "up":
                selected = (selected - 1) % len(labels)
            elif key == "down":
                selected = (selected + 1) % len(labels)
            elif key == "enter":
                return selected
            elif key in {"escape", "quit"}:
                return None
