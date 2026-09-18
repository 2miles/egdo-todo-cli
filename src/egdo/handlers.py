"""Execute parsed commands and coordinate storage with Rich terminal output."""

from __future__ import annotations

from datetime import date
import re
from collections.abc import Iterable
from typing import Any

from egdo import dates, interactive, render, store
from egdo.markdown_store import (
    merge_priority_into_text,
    merge_tag_into_text,
    task_identifiers,
)
from rich.console import Console
from rich.text import Text


def dispatch_command(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Route one parsed command to its command-specific handler."""
    if args.command == "add":
        return _handle_add(args, config, target_date, console)
    if args.command == "list":
        return _handle_list(args, config, target_date, console)
    if args.command == "search":
        return _handle_search(args, config, console)
    if args.command == "done":
        return _handle_done(args, config, target_date, console)
    if args.command == "edit":
        return _handle_edit(args, config, target_date, console)
    if args.command == "move":
        return _handle_move(args, config, target_date, console)
    if args.command == "delete":
        return _handle_delete(args, config, target_date, console)
    if args.command == "tag":
        return _handle_tag(args, config, target_date, console)
    if args.command == "priority":
        return _handle_priority(args, config, target_date, console)
    if args.command == "note":
        return _handle_note(args, config, target_date, console)
    raise ValueError(f"Unknown command: {args.command}")


def _handle_add(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Create a task from direct arguments or the interactive add form."""
    scheduled = target_date
    text = args.text
    tag = args.tag
    priority = args.priority
    if text is None:
        known_tags = {
            ref.task.tag
            for ref in store.list_task_refs(config.root, target_date)
            if ref.task.tag is not None
        }
        form = interactive.prompt_add_form(
            config,
            target_date,
            console,
            dates.parse_future_date,
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
    task = store.create_task(config.root, target_date, task_text, **create_kwargs)
    action = "Added" if not args.done else "Added completed task"
    destination = scheduled.isoformat() if scheduled != target_date else ""
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [(action, task.created.isoformat(), task.text, destination)],
    )


def _handle_done(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Complete tasks selected directly or through the interactive form."""
    indexes = args.indexes
    if not indexes:
        indexes = interactive.prompt_done_form(
            store.list_task_refs(config.root, target_date),
            target_date,
            console,
            project_name=_project_name(config),
        )
        if not indexes:
            console.print("Canceled task completion.")
            return 0
    tasks = store.complete_tasks(config.root, target_date, _normalize_task_ids(indexes))
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [("Completed", target_date.isoformat(), task.text, "") for task in tasks],
    )


def _handle_edit(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Edit a task selected directly or through the interactive form."""
    if args.index is None or args.text is None:
        form = interactive.prompt_edit_form(
            store.list_task_refs(config.root, target_date),
            target_date,
            console,
            _project_name(config),
            initial_identifier=str(args.index) if args.index is not None else None,
        )
        if form is None:
            console.print("Canceled task editing.")
            return 0
        args.index, args.text = form.identifier, form.text
    task = store.edit_task(
        config.root,
        target_date,
        _parse_task_id(str(args.index)),
        args.text,
    )
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [("Edited", task.created.isoformat(), task.text, "")],
    )


def _handle_move(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Move tasks to a date supplied directly or through the interactive form."""
    if not args.indexes or args.when is None:
        initial_scheduled = None
        if args.when is not None:
            initial_scheduled = (
                target_date
                if args.when.strip().lower() == "today"
                else dates.parse_future_date(args.when, target_date)
            )
        form = interactive.prompt_move_form(
            store.list_task_refs(config.root, target_date),
            target_date,
            console,
            _project_name(config),
            dates.parse_future_date,
            initial_identifiers=[str(value) for value in args.indexes] or None,
            initial_scheduled=initial_scheduled,
        )
        if form is None:
            console.print("Canceled task move.")
            return 0
        args.indexes, args.when = form.identifiers, form.scheduled.isoformat()
    destination_date = (
        target_date
        if args.when.strip().lower() == "today"
        else dates.parse_future_date(args.when, target_date)
    )
    tasks = store.move_tasks(
        config.root, target_date, _normalize_task_ids(args.indexes), destination_date
    )
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [
            ("Moved", task.created.isoformat(), task.text, destination_date.isoformat())
            for task in tasks
        ],
    )


def _handle_delete(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Delete tasks selected directly or through the interactive form."""
    if not args.indexes:
        args.indexes = interactive.prompt_delete_form(
            store.list_task_refs(config.root, target_date),
            target_date,
            console,
            _project_name(config),
        )
        if not args.indexes:
            console.print("Canceled task deletion.")
            return 0
    tasks = store.delete_tasks(config.root, target_date, _normalize_task_ids(args.indexes))
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [("Deleted", target_date.isoformat(), task.text, "") for task in tasks],
    )


def _handle_tag(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Set or remove tags using direct values or the interactive form."""
    interactive_tag = not args.values or (
        not args.remove and all(TASK_ID_RE.fullmatch(value.lower()) for value in args.values)
    )
    if interactive_tag:
        refs = store.list_task_refs(config.root, target_date)
        known_tags = sorted({ref.task.tag for ref in refs if ref.task.tag is not None})
        form = interactive.prompt_tag_form(
            refs,
            target_date,
            console,
            _project_name(config),
            known_tags,
            remove_only=args.remove,
            initial_identifiers=args.values or None,
        )
        if form is None:
            console.print("Canceled task tagging.")
            return 0
        args.values = form.identifiers
        args.remove = form.tag is None
        if form.tag is not None:
            args.values = [*args.values, form.tag]
    if args.remove:
        indexes = _parse_indexes(args.values, "tag removal")
        tasks = store.untag_tasks(config.root, target_date, indexes)
        action = "Untagged"
    else:
        indexes, tags = _split_indexed_values(args.values, "tag")
        if len(tags) != 1:
            raise ValueError("Exactly one tag is required")
        tasks = store.tag_tasks(config.root, target_date, indexes, tags[0])
        action = "Tagged"
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [(action, target_date.isoformat(), task.text, "") for task in tasks],
    )


def _handle_priority(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Set task priority using direct values or the interactive form."""
    if not args.indexes or args.level is None:
        form = interactive.prompt_priority_form(
            store.list_task_refs(config.root, target_date),
            target_date,
            console,
            _project_name(config),
            initial_identifiers=[str(value) for value in args.indexes] or None,
        )
        if form is None:
            console.print("Canceled task prioritization.")
            return 0
        args.indexes, args.level = form.identifiers, form.priority
    tasks = store.prioritize_tasks(
        config.root, target_date, _normalize_task_ids(args.indexes), args.level
    )
    return _finish_task_mutation(
        config,
        target_date,
        console,
        [("Prioritized", target_date.isoformat(), task.text, "") for task in tasks],
    )


def _handle_note(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Add a note supplied directly or through the interactive editor."""
    if args.text is None:
        args.text = interactive.prompt_note_form(console, _project_name(config), target_date)
        if args.text is None:
            console.print("Canceled note creation.")
            return 0
    store.add_note(config.root, target_date, args.text)
    _print_task_message(
        console,
        "Noted",
        target_date.isoformat(),
        args.text,
        project=_confirmation_project(config),
    )
    return 0


def _handle_list(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Render filtered task refs without renumbering their global indexes."""
    if args.all_projects:
        return _handle_all_projects(args, config, target_date, console)
    if args.completed:
        return _handle_completed(args, config, target_date, console)
    indexed_refs = _filter_indexed_refs(
        store.list_task_refs(config.root, target_date), args, target_date
    )
    return _render_active_list(indexed_refs, args, config, target_date, console)


def _handle_search(args: Any, config: Any, console: Console) -> int:
    """Search one or every project and render non-actionable archive results."""
    query = args.query.strip() if args.query is not None else None
    tag = args.tag.strip() if args.tag is not None else None
    if not query and not tag:
        raise ValueError("Search requires TEXT or --tag TAG")
    if args.notes and (tag or args.completed):
        raise ValueError("--notes cannot be combined with --tag or --completed")
    if args.all_projects and getattr(args, "selected_project", None) is not None:
        raise ValueError("--project cannot be combined with --all-projects")

    projects = (
        config.projects.items() if args.all_projects else [(_project_name(config), config.root)]
    )
    rendered = False
    for name, root in projects:
        try:
            results = store.search_archive(
                root,
                query,
                tag=tag,
                completed_only=args.completed,
                include_tasks=not args.notes,
                include_notes=not args.tasks and tag is None and not args.completed,
            )
        except (OSError, ValueError) as exc:
            if args.all_projects:
                raise ValueError(f"Project “{name}” at {root}: {exc}") from exc
            raise
        if not results.tasks and not results.notes:
            continue
        _render_search_results(name, results, console)
        rendered = True

    if not rendered:
        console.print()
        console.print(Text("No matching tasks or notes.", style="dim"))
    return 0


def _render_search_results(project_name: str, results: Any, console: Console) -> None:
    """Render one project's search results grouped by stored journal day."""
    wrap_width = render.task_wrap_width(console)
    console.print()
    heading = Text("Project: ", style="dim")
    heading.append(project_name, style="bold cyan")
    console.print(heading)
    days = sorted({result.day for result in results.tasks + results.notes}, reverse=True)
    for position, day in enumerate(days):
        if position:
            console.print()
        label = day.strftime("%A, %B ") + f"{day.day}, {day.year}"
        console.print(render.render_section_header(label, wrap_width))
        for result in results.tasks:
            if result.day == day:
                console.print(
                    render.render_search_task_line(
                        result.task.text,
                        result.task.done,
                        wrap_width=wrap_width,
                        depth=result.task.depth,
                    )
                )
        for result in results.notes:
            if result.day == day:
                console.print(render.render_search_note(result.text, wrap_width=wrap_width))


def _filter_indexed_refs(refs: list[Any], args: Any, target_date: date) -> list[tuple[str, Any]]:
    """Filter refs while retaining identifiers from the unfiltered project list."""
    return [
        (ref.identifier or str(position), ref)
        for position, ref in enumerate(refs, start=1)
        if (not args.future or ref.scheduled > target_date)
        and (args.tag is None or args.tag.strip().lower() == ref.task.tag)
    ]


def _render_active_list(
    indexed_refs: list[tuple[str, Any]],
    args: Any,
    config: Any,
    target_date: date,
    console: Console,
) -> int:
    """Render one project's already-loaded active task refs."""
    wrap_width = render.task_wrap_width(console)
    console.print()
    console.print(render.render_list_header(target_date, _project_name(config)))
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
        console.print(render.render_section_header("Today", wrap_width))
        _render_indexed_tasks(
            console,
            todays_tasks,
            wrap_width,
            show_created=False,
        )
        rendered_active_sections = True
    if old_tasks:
        if rendered_active_sections:
            console.print()
        console.print(render.render_section_header("Carried forward", wrap_width))
        _render_indexed_tasks(console, old_tasks, wrap_width)
        rendered_active_sections = True
    if future_tasks:
        if rendered_active_sections:
            console.print()
        _render_future_groups(
            console,
            target_date,
            future_tasks,
            wrap_width,
        )
    return 0


def _handle_all_projects(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Render independent project snapshots without modifying any archive."""
    if getattr(args, "selected_project", None) is not None:
        raise ValueError("--project cannot be combined with --all-projects")
    if args.future or args.completed or args.tag is not None:
        raise ValueError("--all-projects cannot be combined with --future, --completed, or --tag")

    rendered = False
    for name, root in config.projects.items():
        project_config = config.select(name)
        try:
            indexed_refs = _filter_indexed_refs(
                store.list_task_refs_readonly(root, target_date), args, target_date
            )
            if not indexed_refs:
                continue
            _render_active_list(
                indexed_refs,
                args,
                project_config,
                target_date,
                console,
            )
        except (OSError, ValueError) as exc:
            raise ValueError(f"Project “{name}” at {root}: {exc}") from exc
        rendered = True

    if not rendered:
        console.print()
        console.print(Text("No tasks across projects.", style="dim"))
    return 0


def _render_indexed_tasks(
    console: Console,
    tasks: Iterable[tuple[int, Any]],
    wrap_width: int,
    show_created: bool = True,
) -> None:
    """Render tasks whose indexes were assigned before grouping or filtering."""
    for index, task in tasks:
        console.print(
            render.render_task_line(
                index,
                task.text,
                task.created,
                wrap_width=wrap_width,
                depth=getattr(task, "depth", 0),
                show_created=show_created,
            )
        )


def _handle_completed(args: Any, config: Any, target_date: date, console: Console) -> int:
    """Load completed tasks and render them through the shared collection path."""
    tasks = store.list_completed_tasks(config.root, target_date, tag=args.tag)
    return _render_task_collection(
        console,
        config,
        target_date,
        tasks,
        empty_message="No completed tasks.",
    )


def _render_task_collection(
    console: Console,
    config: Any,
    target_date: date,
    tasks: list[Any],
    empty_message: str,
) -> int:
    """Render a simple dated task collection."""
    wrap_width = render.task_wrap_width(console)
    console.print()
    console.print(render.render_list_header(target_date, _project_name(config)))
    console.print(render.render_separator(wrap_width))
    if not tasks:
        console.print(Text(empty_message, style="dim"))
        return 0
    _render_indexed_tasks(
        console,
        zip(task_identifiers(tasks), tasks),
        wrap_width,
    )
    return 0


def _render_future_groups(
    console: Console,
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
                render.render_section_header(
                    _future_group_label(target_date, scheduled_date), wrap_width
                )
            )
            current_day = scheduled_date
        console.print(
            render.render_task_line(
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
    console: Console,
    action: str,
    _date_label: str,
    text: str,
    destination: str = "",
    project: str | None = None,
) -> None:
    """Print a compact, consistently styled confirmation banner."""
    console.print(
        render.render_confirmation(
            action,
            text,
            destination=destination or None,
            project=project,
        )
    )


def _finish_task_mutation(
    config: Any,
    target_date: date,
    console: Console,
    messages: list[tuple[str, str, str, str]],
) -> int:
    """Confirm a successful task change and refresh interactive terminals."""
    refresh = console.is_terminal and getattr(config, "refresh_after_mutation", True)
    if refresh:
        console.clear()
    project = None if refresh else _confirmation_project(config)
    for action, date_label, text, destination in messages:
        _print_task_message(
            console,
            action,
            date_label,
            text,
            destination=destination,
            project=project,
        )
    if not refresh:
        return 0
    list_args = type(
        "ListArgs",
        (),
        {"future": False, "completed": False, "tag": None, "all_projects": False},
    )()
    return _handle_list(list_args, config, target_date, console)


def _project_name(config: Any) -> str:
    """Support project-aware configs while keeping simple test doubles useful."""
    return getattr(config, "project_name", "Main")


def _confirmation_project(config: Any) -> str | None:
    """Name the selected project only when multiple projects create ambiguity."""
    projects = getattr(config, "projects", {})
    return _project_name(config) if len(projects) > 1 else None


TASK_ID_RE = re.compile(r"^\d+[a-z]{0,2}$")


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
        raise ValueError(f"At least one task ID is required for {action}")
    if not remaining:
        raise ValueError(f"At least one value is required for {action}")
    return indexes, remaining


def _parse_indexes(values: list[str], action: str) -> list[str | int]:
    """Validate positionals that must contain only task IDs."""
    if any(not TASK_ID_RE.fullmatch(value.lower()) for value in values):
        raise ValueError(f"Only task IDs may appear before --remove for {action}")
    indexes = [_parse_task_id(value) for value in values]
    if not indexes:
        raise ValueError(f"At least one task ID is required for {action}")
    return indexes


def _parse_task_id(value: str) -> str | int:
    normalized = value.lower()
    return int(normalized) if normalized.isdigit() else normalized


def _normalize_task_ids(values: list[str | int]) -> list[str | int]:
    return [_parse_task_id(str(value)) for value in values]
