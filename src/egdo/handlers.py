from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
import sys
import termios
import tty
from typing import Any

from egdo.markdown_store import merge_tags_into_text
from egdo.render import TAG_STYLES
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text


@dataclass(slots=True)
class HandlerDeps:
    add_note: Any
    complete_future_task: Any
    complete_task: Any
    create_task: Any
    delete_future_task: Any
    delete_task: Any
    edit_future_task: Any
    edit_task: Any
    list_future_tasks: Any
    list_tasks: Any
    move_future_task: Any
    move_task: Any
    parse_future_date: Any
    render_list_header: Any
    render_separator: Any
    render_tag_style_picker: Any
    render_task_line: Any
    save_config: Any
    tag_future_task: Any
    tag_task: Any
    task_wrap_width: Any
    unmove_task: Any


def dispatch_command(args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps) -> int:
    if args.command == "add":
        task_text = merge_tags_into_text(args.text, args.tag or [])
        task = deps.create_task(config.root, target_date, task_text, done=args.done)
        action = "Added" if not args.done else "Added done"
        _print_task_message(console, action, task.created.isoformat(), task.text)
        return 0

    if args.command == "list":
        return _handle_list(args, config, target_date, console, deps)

    if args.command == "future" and args.future_command is None:
        return _handle_future_list(args, config, target_date, console, deps)

    if args.command == "future" and args.future_command == "done":
        task = deps.complete_future_task(config.root, target_date, args.index)
        _print_task_message(
            console,
            "Completed",
            f"{target_date.isoformat()} <= {task.created.isoformat()}",
            task.text,
        )
        return 0

    if args.command == "future" and args.future_command == "delete":
        task = deps.delete_future_task(config.root, target_date, args.index)
        _print_task_message(console, "Deleted future", task.created.isoformat(), task.text)
        return 0

    if args.command == "future" and args.future_command == "edit":
        task = deps.edit_future_task(config.root, target_date, args.index, args.text)
        _print_task_message(console, "Edited future", task.created.isoformat(), task.text)
        return 0

    if args.command == "future" and args.future_command == "move":
        destination_date = deps.parse_future_date(args.when, target_date)
        task = deps.move_future_task(config.root, target_date, args.index, destination_date)
        _print_task_message(
            console,
            "Moved future",
            task.created.isoformat(),
            task.text,
            suffix=f" -> {destination_date.isoformat()}",
        )
        return 0

    if args.command == "future" and args.future_command == "tag":
        task = deps.tag_future_task(config.root, target_date, args.index, args.tags)
        _print_task_message(console, "Tagged future", task.created.isoformat(), task.text)
        return 0

    if args.command == "future" and args.future_command == "unmove":
        task = deps.unmove_task(config.root, target_date, args.index)
        _print_task_message(
            console, "Unmoved", task.created.isoformat(), task.text, suffix=f" -> {target_date.isoformat()}"
        )
        return 0

    if args.command == "done":
        task = deps.complete_task(config.root, target_date, args.index)
        _print_task_message(console, "Completed", target_date.isoformat(), task.text)
        return 0

    if args.command == "edit":
        task = deps.edit_task(config.root, target_date, args.index, args.text)
        _print_task_message(console, "Edited", task.created.isoformat(), task.text)
        return 0

    if args.command == "move":
        destination_date = deps.parse_future_date(args.when, target_date)
        task = deps.move_task(config.root, target_date, args.index, destination_date)
        _print_task_message(
            console, "Moved", task.created.isoformat(), task.text, suffix=f" -> {destination_date.isoformat()}"
        )
        return 0

    if args.command == "delete":
        task = deps.delete_task(config.root, target_date, args.index)
        _print_task_message(console, "Deleted", target_date.isoformat(), task.text)
        return 0

    if args.command == "tag":
        task = deps.tag_task(config.root, target_date, args.index, args.tags)
        _print_task_message(console, "Tagged", target_date.isoformat(), task.text)
        return 0

    if args.command == "note":
        deps.add_note(config.root, target_date, args.text)
        _print_task_message(console, "Noted", target_date.isoformat(), args.text)
        return 0

    if args.command == "color":
        return handle_color(args, config, console, deps)

    raise ValueError(f"Unknown command: {args.command}")


def _handle_list(args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps) -> int:
    tasks = deps.list_tasks(config.root, target_date, tag=args.tag)
    tag_styles, updated, warnings = build_tag_styles((task.text for task in tasks), config.tag_colors)
    if updated:
        config.tag_colors = tag_styles
        deps.save_config(config)
    wrap_width = deps.task_wrap_width(console)
    console.print()
    console.print(deps.render_list_header(target_date))
    console.print(deps.render_separator(wrap_width))
    for warning in warnings:
        console.print(Text(warning, style="yellow"))
    if not tasks:
        console.print(Text("No active tasks.", style="dim"))
        return 0
    for idx, task in enumerate(tasks, start=1):
        console.print(deps.render_task_line(idx, task.text, task.created, tag_styles, wrap_width=wrap_width))
    return 0


def _handle_future_list(
    args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps
) -> int:
    future_tasks = deps.list_future_tasks(config.root, target_date, tag=args.tag)
    tag_styles, updated, warnings = build_tag_styles(
        (task.text for _, task in future_tasks), config.tag_colors
    )
    if updated:
        config.tag_colors = tag_styles
        deps.save_config(config)
    wrap_width = deps.task_wrap_width(console)
    console.print()
    for warning in warnings:
        console.print(Text(warning, style="yellow"))
    if not future_tasks:
        console.print(Text("No future tasks.", style="dim"))
        return 0
    current_day: date | None = None
    for idx, (scheduled_date, task) in enumerate(future_tasks, start=1):
        if scheduled_date != current_day:
            if current_day is not None:
                console.print()
            console.print(deps.render_list_header(scheduled_date))
            console.print(deps.render_separator(wrap_width))
            current_day = scheduled_date
        console.print(deps.render_task_line(idx, task.text, task.created, tag_styles, wrap_width=wrap_width))
    return 0


def handle_color(args: Any, config: Any, console: Console, deps: HandlerDeps) -> int:
    tag = normalize_tag_name(args.tag)
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
            return 0
    config.tag_colors[tag] = selected_style
    deps.save_config(config)
    preview = Text()
    preview.append(f"{{{tag.upper()}}}", style=selected_style)
    preview.append(f" -> {selected_style}", style="dim")
    console.print(Text("Saved tag color: ") + preview)
    return 0


def _print_task_message(
    console: Console, action: str, date_label: str, text: str, suffix: str = ""
) -> None:
    message = Text(f"{action} [{date_label}] ")
    message.append(text)
    if suffix:
        message.append(suffix)
    console.print(message)


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
) -> str | None:
    if not sys.stdin.isatty():
        raise ValueError(
            "Interactive color picker requires a TTY. Use `egdo color TAG --style STYLE`."
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
    tags: list[str] = []
    remaining = task_text.lstrip()
    while True:
        parsed = _parse_tag_token(remaining)
        if parsed is None:
            break
        tag, remaining = parsed
        tags.append(tag)
        remaining = remaining.lstrip()
    return tags, remaining.lstrip()


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
