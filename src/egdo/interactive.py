"""Interactive terminal forms for commands that can collect missing arguments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import sys
from typing import Any, Callable

from egdo.markdown_store import normalize_priority
from egdo.terminal_keys import read_picker_key
from rich.console import Console, Group
from rich.text import Text


@dataclass(frozen=True, slots=True)
class AddFormResult:
    """Values collected by the interactive add form."""

    text: str
    tag: str | None
    priority: str | None
    scheduled: date


def prompt_done_form(refs: list[Any], today: date, console: Console) -> list[str]:
    """Select globally indexed tasks with a keyboard-driven multi-select picker."""
    if not sys.stdin.isatty():
        raise ValueError("Interactive done requires a TTY. Use `egdo done ID...`.")
    if not refs:
        raise ValueError("No active tasks to complete.")

    selected: set[str] = set()
    cursor = 0
    warning = False
    with console.screen(hide_cursor=True) as screen:
        while True:
            rows = [
                Text("Complete tasks", style="bold"),
                Text("Up/down or j/k, Space to toggle, Enter to complete, q to cancel.", style="dim"),
                Text(""),
            ]
            for index, ref in enumerate(refs):
                identifier = ref.identifier.lower()
                inherited = _selected_ancestor(identifier, selected)
                checked = identifier in selected or inherited is not None
                row = Text("> " if index == cursor else "  ", style="bold" if index == cursor else "dim")
                row.append("[x] " if checked else "[ ] ", style="green" if checked else "dim")
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

    console.print(Text("\nAdd a task", style="bold"))
    console.print(Text("─" * 32, style="dim"))
    text = _prompt_required(console, "Task")
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


def _prompt_required(console: Console, label: str) -> str:
    while True:
        value = console.input(f"[bold]{label}[/]: ").strip()
        if value:
            return value
        console.print("A task description is required.", style="yellow")


_CANCELED = object()


def _choose_tag(
    console: Console, known_tags: list[str], initial: str | None
) -> str | None | object:
    tags = sorted({tag.lower() for tag in known_tags} | ({initial.lower()} if initial else set()))
    selected = initial.lower() if initial else None
    cursor = 0
    while True:
        result = _run_tag_picker(console, tags, selected, cursor)
        if result[0] == "cancel":
            return _CANCELED
        if result[0] == "done":
            return selected
        if result[0] == "new":
            new_tag = console.input("New tag: ").strip().strip("{}").strip().lower()
            if new_tag:
                if new_tag not in tags:
                    tags.append(new_tag)
                    tags.sort()
                selected = new_tag
                cursor = tags.index(new_tag) + 1
            continue
        _, cursor = result


def _run_tag_picker(
    console: Console,
    tags: list[str],
    selected: str | None,
    cursor: int,
) -> tuple[str, int]:
    item_count = len(tags) + 2
    with console.screen(hide_cursor=True) as screen:
        while True:
            rows = [
                Text("Choose a tag", style="bold"),
                Text("Up/down or j/k, Space to select, n for new, Enter to continue.", style="dim"),
                Text(""),
            ]
            labels = ["No tag", *tags, "Create a new tag…"]
            for index, label in enumerate(labels):
                row = Text("> " if index == cursor else "  ", style="bold" if index == cursor else "dim")
                if index == 0:
                    checked = selected is None
                elif index == len(labels) - 1:
                    row.append("[+] ", style="cyan")
                    row.append(label)
                    rows.append(row)
                    continue
                else:
                    checked = label == selected
                row.append("[x] " if checked else "[ ] ", style="green" if checked else "dim")
                row.append(label.upper() if index else label, style="dim cyan" if index else None)
                rows.append(row)
            screen.update(Group(*rows))
            key = read_picker_key()
            if key == "up":
                cursor = (cursor - 1) % item_count
            elif key == "down":
                cursor = (cursor + 1) % item_count
            elif key in {"new"} or (key in {"enter", "toggle"} and cursor == item_count - 1):
                return (("new", cursor))
            elif key == "toggle":
                if cursor == 0:
                    selected = None
                else:
                    selected = tags[cursor - 1]
            elif key == "enter":
                return (("done", cursor))
            elif key in {"escape", "quit"}:
                return (("cancel", cursor))


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
        value = console.input("Schedule (tomorrow, +N, weekday, or YYYY-MM-DD): ").strip()
        try:
            return parse_future_date(value, today)
        except ValueError as exc:
            console.print(str(exc), style="yellow")


def _run_single_picker(
    console: Console, title: str, labels: list[str], selected: int
) -> int | None:
    with console.screen(hide_cursor=True) as screen:
        while True:
            rows = [
                Text(title, style="bold"),
                Text("Up/down or j/k, Enter to choose, q or Esc to cancel.", style="dim"),
                Text(""),
            ]
            for index, label in enumerate(labels):
                row = Text("> " if index == selected else "  ", style="bold" if index == selected else "dim")
                row.append("(x) " if index == selected else "( ) ", style="green" if index == selected else "dim")
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
