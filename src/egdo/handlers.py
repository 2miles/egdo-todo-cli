"""Execute parsed commands and coordinate storage with Rich terminal output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from collections.abc import Iterable
from typing import Any

from egdo.markdown_store import (
    merge_priority_into_text,
    merge_tag_into_text,
    split_task_prefix,
    task_identifiers,
)
from rich.console import Console
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
    prompt_add_form: Any
    prompt_done_form: Any
    prioritize_tasks: Any
    render_list_header: Any
    render_separator: Any
    render_section_header: Any
    render_task_line: Any
    tag_tasks: Any
    task_wrap_width: Any
    untag_tasks: Any
    unmove_tasks: Any


def dispatch_command(args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps) -> int:
    """Route one parsed command while keeping process setup out of handlers."""
    if args.command == "add":
        scheduled = target_date
        text = args.text
        tag = args.tag
        priority = args.priority
        if text is None:
            known_tags = {
                ref.task.tag
                for ref in deps.list_task_refs(config.root, target_date)
                if ref.task.tag is not None
            }
            form = deps.prompt_add_form(
                config,
                target_date,
                console,
                deps.parse_future_date,
                initial_tag=tag,
                initial_priority=priority,
                known_tags=sorted(known_tags),
            )
            if form is None:
                console.print("Canceled task creation.")
                return 0
            text, tag, priority, scheduled = (
                form.text,
                form.tag,
                form.priority,
                form.scheduled,
            )
        task_text = merge_tag_into_text(text, tag)
        task_text = merge_priority_into_text(task_text, priority)
        create_kwargs = {"done": args.done}
        if args.parent is not None:
            create_kwargs["parent"] = args.parent
        if scheduled != target_date:
            create_kwargs["scheduled_date"] = scheduled
        task = deps.create_task(config.root, target_date, task_text, **create_kwargs)
        action = "Added" if not args.done else "Added done"
        suffix = f" -> {scheduled.isoformat()}" if scheduled != target_date else ""
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [(action, task.created.isoformat(), task.text, suffix)],
        )

    if args.command == "list":
        return _handle_list(args, config, target_date, console, deps)

    if args.command == "finished":
        return _handle_finished(args, config, target_date, console, deps)

    if args.command == "unmove":
        tasks = deps.unmove_tasks(config.root, target_date, _normalize_task_ids(args.indexes))
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [
                ("Unmoved", task.created.isoformat(), task.text, f" -> {target_date.isoformat()}")
                for task in tasks
            ],
        )

    if args.command == "done":
        indexes = args.indexes
        if not indexes:
            indexes = deps.prompt_done_form(
                deps.list_task_refs(
                    config.root, target_date
                ),
                target_date,
                console,
            )
            if not indexes:
                console.print("Canceled task completion.")
                return 0
        tasks = deps.complete_tasks(config.root, target_date, _normalize_task_ids(indexes))
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [("Completed", target_date.isoformat(), task.text, "") for task in tasks],
        )

    if args.command == "edit":
        task = deps.edit_task(
            config.root,
            target_date,
            _parse_task_id(str(args.index)),
            args.text,
        )
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [("Edited", task.created.isoformat(), task.text, "")],
        )

    if args.command == "move":
        destination_date = deps.parse_future_date(args.when, target_date)
        tasks = deps.move_tasks(
            config.root, target_date, _normalize_task_ids(args.indexes), destination_date
        )
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [
                ("Moved", task.created.isoformat(), task.text, f" -> {destination_date.isoformat()}")
                for task in tasks
            ],
        )

    if args.command == "delete":
        tasks = deps.delete_tasks(config.root, target_date, _normalize_task_ids(args.indexes))
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [("Deleted", target_date.isoformat(), task.text, "") for task in tasks],
        )

    if args.command == "tag":
        if args.remove:
            indexes = _parse_indexes(args.values, "tag removal")
            tasks = deps.untag_tasks(
                config.root,
                target_date,
                indexes,
            )
            action = "Untagged"
        else:
            indexes, tags = _split_indexed_values(args.values, "tag")
            if len(tags) != 1:
                raise ValueError("Exactly one tag is required")
            tasks = deps.tag_tasks(
                config.root,
                target_date,
                indexes,
                tags[0],
            )
            action = "Tagged"
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [(action, target_date.isoformat(), task.text, "") for task in tasks],
        )

    if args.command == "priority":
        tasks = deps.prioritize_tasks(
            config.root, target_date, _normalize_task_ids(args.indexes), args.level
        )
        return _finish_task_mutation(
            config,
            target_date,
            console,
            deps,
            [("Prioritized", target_date.isoformat(), task.text, "") for task in tasks],
        )

    if args.command == "note":
        deps.add_note(config.root, target_date, args.text)
        _print_task_message(console, "Noted", target_date.isoformat(), args.text)
        return 0

    raise ValueError(f"Unknown command: {args.command}")


def _handle_list(args: Any, config: Any, target_date: date, console: Console, deps: HandlerDeps) -> int:
    """Render filtered task refs without renumbering their global indexes."""
    indexed_refs = [
        (ref.identifier or str(position), ref)
        for position, ref in enumerate(
            deps.list_task_refs(
                config.root, target_date
            ),
            start=1,
        )
        if (not args.future or ref.scheduled > target_date)
        and (args.tag is None or args.tag.strip().lower() == ref.task.tag)
    ]
    wrap_width = deps.task_wrap_width(console)
    console.print()
    console.print(deps.render_list_header(target_date))
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
        console.print(deps.render_section_header("Today", wrap_width))
        _render_indexed_tasks(
            console,
            deps,
            todays_tasks,
            wrap_width,
            show_created=False,
        )
        rendered_active_sections = True
    if old_tasks:
        if rendered_active_sections:
            console.print()
        console.print(deps.render_section_header("Carried forward", wrap_width))
        _render_indexed_tasks(console, deps, old_tasks, wrap_width)
        rendered_active_sections = True
    if future_tasks:
        if rendered_active_sections:
            console.print()
        _render_future_groups(
            console,
            deps,
            target_date,
            future_tasks,
            wrap_width,
        )
    return 0


def _render_indexed_tasks(
    console: Console,
    deps: HandlerDeps,
    tasks: Iterable[tuple[int, Any]],
    wrap_width: int,
    show_created: bool = True,
) -> None:
    """Render tasks whose indexes were assigned before grouping or filtering."""
    for index, task in tasks:
        console.print(
            deps.render_task_line(
                index,
                task.text,
                task.created,
                wrap_width=wrap_width,
                depth=getattr(task, "depth", 0),
                show_created=show_created,
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
    """Render a simple dated task collection."""
    wrap_width = deps.task_wrap_width(console)
    console.print()
    console.print(deps.render_list_header(target_date))
    console.print(deps.render_separator(wrap_width))
    if not tasks:
        console.print(Text(empty_message, style="dim"))
        return 0
    _render_indexed_tasks(
        console,
        deps,
        zip(task_identifiers(tasks), tasks),
        wrap_width,
    )
    return 0


def _render_future_groups(
    console: Console,
    deps: HandlerDeps,
    target_date: date,
    future_tasks: list[tuple[int, date, Any]],
    wrap_width: int,
) -> None:
    """Render future refs grouped by scheduled date, preserving global indexes."""
    current_day: date | None = None
    for idx, scheduled_date, task in future_tasks:
        if scheduled_date != current_day:
            if current_day is not None:
                console.print()
            console.print(
                deps.render_section_header(
                    _future_group_label(target_date, scheduled_date), wrap_width
                )
            )
            current_day = scheduled_date
        console.print(
            deps.render_task_line(
                idx,
                task.text,
                task.created,
                wrap_width=wrap_width,
                show_created=False,
            )
        )


def _future_group_label(target_date: date, scheduled_date: date) -> str:
    """Give future task groups friendly, full-length date labels."""
    if scheduled_date.toordinal() == target_date.toordinal() + 1:
        return scheduled_date.strftime("Tomorrow, %B ") + str(scheduled_date.day)
    return scheduled_date.strftime("%A, %B ") + str(scheduled_date.day)


def _print_task_message(
    console: Console, action: str, _date_label: str, text: str, suffix: str = ""
) -> None:
    """Print a compact, consistently styled confirmation banner."""
    message = Text("✓ ", style="bold green")
    message.append(action, style="bold")
    message.append(f" “{text}”")
    if suffix:
        destination = suffix.removeprefix(" -> ")
        message.append(f" → {destination}", style="dim")
    console.print(message)


def _finish_task_mutation(
    config: Any,
    target_date: date,
    console: Console,
    deps: HandlerDeps,
    messages: list[tuple[str, str, str, str]],
) -> int:
    """Confirm a successful task change and refresh interactive terminals."""
    if console.is_terminal:
        console.clear()
    for action, date_label, text, suffix in messages:
        _print_task_message(console, action, date_label, text, suffix=suffix)
    if not console.is_terminal:
        return 0
    list_args = type("ListArgs", (), {"future": False, "tag": None})()
    return _handle_list(list_args, config, target_date, console, deps)


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
