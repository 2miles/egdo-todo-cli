"""Execute parsed commands and coordinate storage with Rich terminal output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
import re
import sys
import termios
import tty
from collections.abc import Iterable
from typing import Any

from egdo.dates import format_display_date
from egdo.markdown_store import (
    merge_priority_into_text,
    merge_tags_into_text,
    normalize_priority,
    split_task_prefix,
    task_identifiers,
)
from egdo.render import TAG_STYLES
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text


@dataclass(slots=True)
class HandlerDeps:
    """Inject command dependencies so dispatch behavior stays easy to test."""
    add_note: Any
    complete_tasks: Any
    create_task: Any
    delete_tasks: Any
    edit_task: Any
    list_finished_tasks: Any
    list_task_refs: Any
    move_tasks: Any
    parse_future_date: Any
    prioritize_tasks: Any
    render_list_header: Any
    render_priority_style_picker: Any
    render_separator: Any
    render_tag_style_picker: Any
    render_task_line: Any
    save_config: Any
    tag_tasks: Any
    task_wrap_width: Any
    untag_tasks: Any
    unmove_tasks: Any


def dispatch_command(args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps) -> int:
    """Route one parsed command while keeping process setup out of handlers."""
    if args.command == "add":
        task_text = merge_tags_into_text(args.text, args.tag or [])
        task_text = merge_priority_into_text(task_text, args.priority)
        create_kwargs = {"done": args.done}
        if args.parent is not None:
            create_kwargs["parent"] = args.parent
        task = deps.create_task(config.root, target_date, task_text, **create_kwargs)
        action = "Added" if not args.done else "Added done"
        _print_task_message(console, action, task.created.isoformat(), task.text)
        return 0

    if args.command == "list":
        return _handle_list(args, config, target_date, console, deps)

    if args.command == "finished":
        return _handle_finished(args, config, target_date, console, deps)

    if args.command == "unmove":
        tasks = deps.unmove_tasks(config.root, target_date, _normalize_task_ids(args.indexes))
        for task in tasks:
            _print_task_message(
                console,
                "Unmoved",
                task.created.isoformat(),
                task.text,
                suffix=f" -> {target_date.isoformat()}",
            )
        return 0

    if args.command == "done":
        tasks = deps.complete_tasks(config.root, target_date, _normalize_task_ids(args.indexes))
        for task in tasks:
            _print_task_message(console, "Completed", target_date.isoformat(), task.text)
        return 0

    if args.command == "edit":
        task = deps.edit_task(config.root, target_date, _parse_task_id(str(args.index)), args.text)
        _print_task_message(console, "Edited", task.created.isoformat(), task.text)
        return 0

    if args.command == "move":
        destination_date = deps.parse_future_date(args.when, target_date)
        tasks = deps.move_tasks(
            config.root, target_date, _normalize_task_ids(args.indexes), destination_date
        )
        for task in tasks:
            _print_task_message(
                console,
                "Moved",
                task.created.isoformat(),
                task.text,
                suffix=f" -> {destination_date.isoformat()}",
            )
        return 0

    if args.command == "delete":
        tasks = deps.delete_tasks(config.root, target_date, _normalize_task_ids(args.indexes))
        for task in tasks:
            _print_task_message(console, "Deleted", target_date.isoformat(), task.text)
        return 0

    if args.command == "tag":
        if args.remove:
            indexes = _parse_indexes(args.values, "tag removal")
            tasks = deps.untag_tasks(config.root, target_date, indexes, args.remove)
            action = "Untagged"
        else:
            indexes, tags = _split_indexed_values(args.values, "tag")
            tasks = deps.tag_tasks(config.root, target_date, indexes, tags)
            action = "Tagged"
        for task in tasks:
            _print_task_message(console, action, target_date.isoformat(), task.text)
        return 0

    if args.command == "priority":
        tasks = deps.prioritize_tasks(
            config.root, target_date, _normalize_task_ids(args.indexes), args.level
        )
        for task in tasks:
            _print_task_message(console, "Prioritized", target_date.isoformat(), task.text)
        return 0

    if args.command == "note":
        deps.add_note(config.root, target_date, args.text)
        _print_task_message(console, "Noted", target_date.isoformat(), args.text)
        return 0

    if args.command == "color":
        return handle_color(args, config, console, deps)

    raise ValueError(f"Unknown command: {args.command}")


def _handle_list(args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps) -> int:
    """Render filtered task refs without renumbering their global indexes."""
    indexed_refs = [
        (ref.identifier or str(position), ref)
        for position, ref in enumerate(deps.list_task_refs(config.root, target_date), start=1)
        if (not args.future or ref.scheduled > target_date)
        and (args.tag is None or args.tag.strip().lower() in ref.task.tags)
    ]
    tag_styles, updated, warnings = build_tag_styles(
        [ref.task.text for _, ref in indexed_refs],
        config.tag_colors,
    )
    if updated:
        config.tag_colors = tag_styles
        deps.save_config(config)
    wrap_width = deps.task_wrap_width(console)
    priority_styles = getattr(config, "priority_styles", {})
    console.print()
    console.print(deps.render_list_header(target_date))
    console.print(deps.render_separator(wrap_width))
    for warning in warnings:
        console.print(Text(warning, style="yellow"))
    if not indexed_refs:
        empty_message = "No future tasks." if args.future else "No active tasks."
        console.print(Text(empty_message, style="dim"))
        return 0

    todays_tasks = [
        (index, ref.task)
        for index, ref in indexed_refs
        if ref.scheduled == target_date and (ref.root_created or ref.task.created) == target_date
    ]
    old_tasks = [
        (index, ref.task)
        for index, ref in indexed_refs
        if ref.scheduled == target_date and (ref.root_created or ref.task.created) != target_date
    ]
    future_tasks = [
        (index, ref.scheduled, ref.task)
        for index, ref in indexed_refs
        if ref.scheduled > target_date
    ]
    rendered_active_sections = False
    if todays_tasks:
        console.print(Text("Today", style="bold"))
        _render_indexed_tasks(
            console, deps, todays_tasks, tag_styles, priority_styles, wrap_width
        )
        rendered_active_sections = True
    if old_tasks:
        if rendered_active_sections:
            console.print()
        console.print(Text("Old", style="bold"))
        _render_indexed_tasks(console, deps, old_tasks, tag_styles, priority_styles, wrap_width)
        rendered_active_sections = True
    if future_tasks:
        if rendered_active_sections:
            console.print()
        console.print(_render_future_divider(wrap_width))
        _render_future_groups(
            console,
            deps,
            target_date,
            future_tasks,
            tag_styles,
            priority_styles,
            wrap_width,
        )
    return 0


def _render_indexed_tasks(
    console: Console,
    deps: HandlerDeps,
    tasks: Iterable[tuple[int, Any]],
    tag_styles: dict[str, str],
    priority_styles: dict[str, str],
    wrap_width: int,
) -> None:
    """Render tasks whose indexes were assigned before grouping or filtering."""
    for index, task in tasks:
        console.print(
            deps.render_task_line(
                index,
                task.text,
                task.created,
                tag_styles,
                wrap_width=wrap_width,
                priority_styles=priority_styles,
                depth=getattr(task, "depth", 0),
            )
        )


def _handle_finished(
    args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps
) -> int:
    """Load completed tasks and render them through the shared collection path."""
    tasks = deps.list_finished_tasks(config.root, target_date, tag=args.tag)
    return _render_task_collection(
        console,
        deps,
        config,
        target_date,
        tasks,
        empty_message="No finished tasks.",
    )


def _render_task_collection(
    console: Console,
    deps: HandlerDeps,
    config: Any,
    target_date: date,
    tasks: list[Any],
    empty_message: str,
) -> int:
    """Render a simple dated task collection and persist new tag styles."""
    tag_styles, updated, warnings = build_tag_styles((task.text for task in tasks), config.tag_colors)
    if updated:
        config.tag_colors = tag_styles
        deps.save_config(config)
    wrap_width = deps.task_wrap_width(console)
    priority_styles = getattr(config, "priority_styles", {})
    console.print()
    console.print(deps.render_list_header(target_date))
    console.print(deps.render_separator(wrap_width))
    for warning in warnings:
        console.print(Text(warning, style="yellow"))
    if not tasks:
        console.print(Text(empty_message, style="dim"))
        return 0
    _render_indexed_tasks(
        console,
        deps,
        zip(task_identifiers(tasks), tasks),
        tag_styles,
        priority_styles,
        wrap_width,
    )
    return 0


def _render_future_groups(
    console: Console,
    deps: HandlerDeps,
    target_date: date,
    future_tasks: list[tuple[int, date, Any]],
    tag_styles: dict[str, str],
    priority_styles: dict[str, str],
    wrap_width: int,
) -> None:
    """Render future refs grouped by scheduled date, preserving global indexes."""
    current_day: date | None = None
    for idx, scheduled_date, task in future_tasks:
        if scheduled_date != current_day:
            if current_day is not None:
                console.print()
            console.print(Text(_future_group_label(target_date, scheduled_date), style="bold"))
            current_day = scheduled_date
        console.print(
            deps.render_task_line(
                idx,
                task.text,
                task.created,
                tag_styles,
                wrap_width=wrap_width,
                priority_styles=priority_styles,
            )
        )


def _render_future_divider(width: int) -> Text:
    """Build the labeled rule separating active work from future work."""
    label = " Future "
    line_width = max(len(label) + 2, width)
    left = 2
    right = line_width - left - len(label)
    divider = Text()
    divider.append("─" * left, style="dim")
    divider.append(label, style="bold")
    divider.append("─" * right, style="dim")
    return divider


def _future_group_label(target_date: date, scheduled_date: date) -> str:
    """Give tomorrow a friendly label and use a normal date otherwise."""
    if scheduled_date.toordinal() == target_date.toordinal() + 1:
        return f"Tomorrow ({format_display_date(scheduled_date)})"
    return format_display_date(scheduled_date)


def handle_color(args: Any, config: Any, console: Console, deps: HandlerDeps) -> int:
    """Resolve interactive or explicit styles and save all changes once."""
    explicit_style = _validated_style(args.style)

    if args.priority is not None:
        if args.copy_from is not None:
            raise ValueError("--copy-from can only be used with --tag")
        if not hasattr(config, "priority_styles"):
            config.priority_styles = {}
        changed = False
        for priority in args.priority:
            normalized = normalize_priority(priority)
            assert normalized is not None
            key = f"p{normalized}"
            selected_style = explicit_style or choose_tag_style_interactive(
                key,
                console,
                deps.render_priority_style_picker,
                config.priority_styles.get(key),
                command_hint=f"egdo color --priority {priority} --style STYLE",
            )
            if selected_style is None:
                console.print("Canceled priority style update.")
                continue
            config.priority_styles[key] = selected_style
            changed = True
            preview = Text(f"{key.upper()} -> ")
            preview.append(selected_style, style=selected_style)
            console.print(Text("Saved priority style: ") + preview)
        if changed:
            deps.save_config(config)
        return 0

    copied_style: str | None = None
    if args.copy_from is not None:
        source_tag = normalize_tag_name(args.copy_from)
        if not source_tag:
            raise ValueError("Source tag name cannot be empty")
        copied_style = config.tag_colors.get(source_tag)
        if copied_style is None:
            raise ValueError(f"Tag `{source_tag}` has no saved color to copy")

    changed = False
    for tag_value in args.tag:
        tag = normalize_tag_name(tag_value)
        if not tag:
            raise ValueError("Tag name cannot be empty")
        if copied_style is not None:
            selected_style = copied_style
        elif explicit_style is not None:
            selected_style = explicit_style
        else:
            selected_style = choose_tag_style_interactive(
                tag, console, deps.render_tag_style_picker, config.tag_colors.get(tag)
            )
            if selected_style is None:
                console.print("Canceled tag color update.")
                continue
        config.tag_colors[tag] = selected_style
        changed = True
        preview = Text()
        preview.append(f"{{{tag.upper()}}}", style=selected_style)
        preview.append(f" -> {selected_style}", style="dim")
        console.print(Text("Saved tag color: ") + preview)
    if changed:
        deps.save_config(config)
    return 0


def _validated_style(value: str | None) -> str | None:
    """Normalize an optional Rich style and reject invalid syntax."""
    if value is None:
        return None
    style = value.strip()
    if not is_valid_style(style):
        raise ValueError(f"Invalid style: {style}")
    return style


def _print_task_message(
    console: Console, action: str, date_label: str, text: str, suffix: str = ""
) -> None:
    """Print a consistently formatted confirmation for a task action."""
    message = Text(f"{action} [{date_label}] ")
    message.append(text)
    if suffix:
        message.append(suffix)
    console.print(message)


TASK_ID_RE = re.compile(r"^\d+(?:[a-z]|[a-z]\.[a-z])?$")


def _split_indexed_values(values: list[str], action: str) -> tuple[list[str | int], list[str]]:
    """Split ambiguous ``INDEX... VALUE...`` positionals at the first non-number."""
    indexes: list[str | int] = []
    position = 0
    while position < len(values):
        if not TASK_ID_RE.fullmatch(values[position].lower()):
            break
        indexes.append(_parse_task_id(values[position]))
        position += 1
    remaining = values[position:]
    if not indexes:
        raise ValueError(f"At least one task index is required for {action}")
    if not remaining:
        raise ValueError(f"At least one value is required for {action}")
    return indexes, remaining


def _parse_indexes(values: list[str], action: str) -> list[str | int]:
    """Validate positionals that must contain only task indexes."""
    if any(not TASK_ID_RE.fullmatch(value.lower()) for value in values):
        raise ValueError(f"Only task indexes may appear before --remove for {action}")
    indexes = [_parse_task_id(value) for value in values]
    if not indexes:
        raise ValueError(f"At least one task index is required for {action}")
    return indexes


def _parse_task_id(value: str) -> str | int:
    normalized = value.lower()
    return int(normalized) if normalized.isdigit() else normalized


def _normalize_task_ids(values: list[str | int]) -> list[str | int]:
    return [_parse_task_id(str(value)) for value in values]


def build_tag_styles(
    task_texts: Iterable[str], existing_styles: dict[str, str] | None = None
) -> tuple[dict[str, str], bool, list[str]]:
    """Assign stable palette entries to unseen tags and repair invalid styles."""
    styles = dict(existing_styles or {})
    updated = False
    warnings: list[str] = []
    valid_assigned = [style for style in styles.values() if is_valid_style(style)]
    next_style = len(valid_assigned)
    for task_text in task_texts:
        _, tags, _ = split_task_prefix(task_text)
        for tag in tags:
            normalized = tag.lower()
            if normalized in styles:
                if not is_valid_style(styles[normalized]):
                    styles[normalized] = TAG_STYLES[next_style % len(TAG_STYLES)]
                    next_style += 1
                    updated = True
                    warnings.append(
                        f"Invalid style for tag `{normalized}` in config. Reassigned it to `{styles[normalized]}`."
                    )
                continue
            styles[normalized] = TAG_STYLES[next_style % len(TAG_STYLES)]
            next_style += 1
            updated = True
    return styles, updated, warnings


def normalize_tag_name(tag: str) -> str:
    return tag.strip().strip("{}").strip().lower()


def choose_tag_style_interactive(
    tag: str,
    console: Console,
    render_tag_style_picker: Any,
    current_style: str | None = None,
    command_hint: str = "egdo color --tag TAG --style STYLE",
) -> str | None:
    """Run the full-screen keyboard picker and return a style or cancellation."""
    if not sys.stdin.isatty():
        raise ValueError(
            f"Interactive color picker requires a TTY. Use `{command_hint}`."
        )

    selected_index = TAG_STYLES.index(current_style) if current_style in TAG_STYLES else 0
    with console.screen(hide_cursor=True) as screen:
        screen.update(render_tag_style_picker(tag, selected_index, current_style))
        while True:
            key = read_picker_key()
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
            screen.update(render_tag_style_picker(tag, selected_index, current_style))


def read_picker_key() -> str:
    """Read one raw terminal key, translating arrows and vim keys to actions."""
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


def is_valid_style(style: str) -> bool:
    """Return whether Rich accepts a style expression."""
    try:
        Style.parse(style)
    except StyleSyntaxError:
        return False
    return True
