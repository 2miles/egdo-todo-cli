from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
import sys
import termios
import tty
from typing import Any

from egdo.dates import format_display_date
from egdo.markdown_store import (
    merge_priority_into_text,
    merge_tags_into_text,
    normalize_priority,
    split_task_prefix,
)
from egdo.render import TAG_STYLES
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text


@dataclass(slots=True)
class HandlerDeps:
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
    if args.command == "add":
        task_text = merge_tags_into_text(args.text, args.tag or [])
        task_text = merge_priority_into_text(task_text, args.priority)
        task = deps.create_task(config.root, target_date, task_text, done=args.done)
        action = "Added" if not args.done else "Added done"
        _print_task_message(console, action, task.created.isoformat(), task.text)
        return 0

    if args.command == "list":
        return _handle_list(args, config, target_date, console, deps)

    if args.command == "finished":
        return _handle_finished(args, config, target_date, console, deps)

    if args.command == "future" and args.future_command is None:
        return _handle_future_list(args, config, target_date, console, deps)

    if args.command == "future" and args.future_command == "unmove":
        tasks = deps.unmove_tasks(config.root, target_date, args.indexes)
        for task in tasks:
            _print_task_message(
                console,
                "Unmoved",
                task.created.isoformat(),
                task.text,
                suffix=f" -> {target_date.isoformat()}",
            )
        return 0

    if args.command == "future":
        args.command = args.future_command

    if args.command == "done":
        tasks = deps.complete_tasks(config.root, target_date, args.indexes)
        for task in tasks:
            _print_task_message(console, "Completed", target_date.isoformat(), task.text)
        return 0

    if args.command == "edit":
        task = deps.edit_task(config.root, target_date, args.index, args.text)
        _print_task_message(console, "Edited", task.created.isoformat(), task.text)
        return 0

    if args.command == "move":
        destination_date = deps.parse_future_date(args.when, target_date)
        tasks = deps.move_tasks(config.root, target_date, args.indexes, destination_date)
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
        tasks = deps.delete_tasks(config.root, target_date, args.indexes)
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
        tasks = deps.prioritize_tasks(config.root, target_date, args.indexes, args.level)
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
    indexed_refs = [
        (index, ref)
        for index, ref in enumerate(deps.list_task_refs(config.root, target_date), start=1)
        if args.tag is None or args.tag.strip().lower() in ref.task.tags
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
        console.print(Text("No active tasks.", style="dim"))
        return 0

    todays_tasks = [
        (index, ref.task)
        for index, ref in indexed_refs
        if ref.scheduled == target_date and ref.task.created == target_date
    ]
    old_tasks = [
        (index, ref.task)
        for index, ref in indexed_refs
        if ref.scheduled == target_date and ref.task.created != target_date
    ]
    future_tasks = [
        (index, ref.scheduled, ref.task)
        for index, ref in indexed_refs
        if ref.scheduled > target_date
    ]
    rendered_active_sections = False
    if todays_tasks:
        console.print(Text("Today", style="bold"))
        for index, task in todays_tasks:
            console.print(
                deps.render_task_line(
                    index,
                    task.text,
                    task.created,
                    tag_styles,
                    wrap_width=wrap_width,
                    priority_styles=priority_styles,
                )
            )
        rendered_active_sections = True
    if old_tasks:
        if rendered_active_sections:
            console.print()
        console.print(Text("Old", style="bold"))
        for index, task in old_tasks:
            console.print(
                deps.render_task_line(
                    index,
                    task.text,
                    task.created,
                    tag_styles,
                    wrap_width=wrap_width,
                    priority_styles=priority_styles,
                )
            )
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


def _handle_finished(
    args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps
) -> int:
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
    for idx, task in enumerate(tasks, start=1):
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
    return 0


def _handle_future_list(
    args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps
) -> int:
    future_tasks = [
        (index, ref.scheduled, ref.task)
        for index, ref in enumerate(deps.list_task_refs(config.root, target_date), start=1)
        if ref.scheduled > target_date
        and (args.tag is None or args.tag.strip().lower() in ref.task.tags)
    ]
    tag_styles, updated, warnings = build_tag_styles(
        (task.text for _, _, task in future_tasks), config.tag_colors
    )
    if updated:
        config.tag_colors = tag_styles
        deps.save_config(config)
    wrap_width = deps.task_wrap_width(console)
    priority_styles = getattr(config, "priority_styles", {})
    console.print()
    for warning in warnings:
        console.print(Text(warning, style="yellow"))
    if not future_tasks:
        console.print(Text("No future tasks.", style="dim"))
        return 0
    current_day: date | None = None
    for idx, scheduled_date, task in future_tasks:
        if scheduled_date != current_day:
            if current_day is not None:
                console.print()
            console.print(deps.render_list_header(scheduled_date))
            console.print(deps.render_separator(wrap_width))
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
    if scheduled_date.toordinal() == target_date.toordinal() + 1:
        return f"Tomorrow ({format_display_date(scheduled_date)})"
    return format_display_date(scheduled_date)


def handle_color(args: Any, config: Any, console: Console, deps: HandlerDeps) -> int:
    if args.priority is not None:
        for priority in args.priority:
            handle_priority_color(priority, args.style, config, console, deps)
        return 0

    for tag_value in args.tag:
        tag = normalize_tag_name(tag_value)
        if not tag:
            raise ValueError("Tag name cannot be empty")
        if args.style:
            selected_style = args.style.strip()
            if not is_valid_style(selected_style):
                raise ValueError(f"Invalid style: {selected_style}")
        else:
            selected_style = choose_tag_style_interactive(
                tag, console, deps.render_tag_style_picker, config.tag_colors.get(tag)
            )
            if selected_style is None:
                console.print("Canceled tag color update.")
                continue
        config.tag_colors[tag] = selected_style
        deps.save_config(config)
        preview = Text()
        preview.append(f"{{{tag.upper()}}}", style=selected_style)
        preview.append(f" -> {selected_style}", style="dim")
        console.print(Text("Saved tag color: ") + preview)
    return 0


def handle_priority_color(
    priority_value: str, style_value: str | None, config: Any, console: Console, deps: HandlerDeps
) -> int:
    priority = normalize_priority(priority_value)
    assert priority is not None
    if not hasattr(config, "priority_styles"):
        config.priority_styles = {}
    key = f"p{priority}"
    if style_value:
        selected_style = style_value.strip()
        if not is_valid_style(selected_style):
            raise ValueError(f"Invalid style: {selected_style}")
    else:
        selected_style = choose_tag_style_interactive(
            key,
            console,
            deps.render_priority_style_picker,
            config.priority_styles.get(key),
            command_hint=f"egdo color --priority {priority_value} --style STYLE",
        )
        if selected_style is None:
            console.print("Canceled priority style update.")
            return 0
    config.priority_styles[key] = selected_style
    deps.save_config(config)
    preview = Text(f"{key.upper()} -> ")
    preview.append(selected_style, style=selected_style)
    console.print(Text("Saved priority style: ") + preview)
    return 0


def _print_task_message(
    console: Console, action: str, date_label: str, text: str, suffix: str = ""
) -> None:
    message = Text(f"{action} [{date_label}] ")
    message.append(text)
    if suffix:
        message.append(suffix)
    console.print(message)


def _split_indexed_values(values: list[str], action: str) -> tuple[list[int], list[str]]:
    indexes: list[int] = []
    position = 0
    while position < len(values):
        try:
            indexes.append(int(values[position]))
        except ValueError:
            break
        position += 1
    remaining = values[position:]
    if not indexes:
        raise ValueError(f"At least one task index is required for {action}")
    if not remaining:
        raise ValueError(f"At least one value is required for {action}")
    return indexes, remaining


def _parse_indexes(values: list[str], action: str) -> list[int]:
    try:
        indexes = [int(value) for value in values]
    except ValueError as exc:
        raise ValueError(f"Only task indexes may appear before --remove for {action}") from exc
    if not indexes:
        raise ValueError(f"At least one task index is required for {action}")
    return indexes


def build_tag_styles(
    task_texts: list[str] | tuple[str, ...] | object, existing_styles: dict[str, str] | None = None
) -> tuple[dict[str, str], bool, list[str]]:
    styles = dict(existing_styles or {})
    updated = False
    warnings: list[str] = []
    valid_assigned = [style for style in styles.values() if is_valid_style(style)]
    next_style = len(valid_assigned)
    for task_text in task_texts:
        tags, _ = _split_leading_tags(task_text)
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
            if normalized not in styles:
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
    try:
        Style.parse(style)
    except StyleSyntaxError:
        return False
    return True


def _split_leading_tags(task_text: str) -> tuple[list[str], str]:
    _, tags, body = split_task_prefix(task_text)
    return tags, body


def _parse_tag_token(text: str) -> tuple[str, str] | None:
    if text.startswith("{"):
        closing = text.find("}")
        if closing <= 1:
            return None
        tag = text[1:closing].strip()
        if not tag:
            return None
        return (tag, text[closing + 1 :])
    return None
