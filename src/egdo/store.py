"""Provide task operations over the Markdown persistence layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from egdo.markdown_store import (
    DayState,
    FileState,
    Task,
    ensure_state,
    file_path,
    format_task_text,
    is_month_file,
    normalize_priority,
    normalize_tags,
    split_task_prefix,
    task_identifiers,
    write_state,
)


@dataclass(frozen=True, slots=True)
class TaskRef:
    """Pair a task with its scheduled date in the global index space."""
    scheduled: date
    task: Task
    identifier: str = ""
    root_created: date | None = None


def add_task(notes_dir: Path, target_date: date, text: str) -> Task:
    return create_task(notes_dir, target_date, text, done=False)


def create_task(
    notes_dir: Path, target_date: date, text: str, done: bool, parent: str | None = None
) -> Task:
    """Roll unfinished work forward, then append a task to the target day."""
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    task = Task(text=text, created=target_date, done=done)
    if parent is None:
        day.tasks.append(task)
    else:
        parent_ref = _select_task_refs(notes_dir, target_date, [parent])[0]
        if parent_ref.scheduled != target_date:
            raise ValueError("New subtasks can only be added to tasks scheduled for today")
        if parent_ref.task.depth >= 2:
            raise ValueError("Tasks may be nested at most three levels deep")
        parent_position = _find_task_position(day.tasks, parent_ref.task.key())
        insert_at = _subtree_end(day.tasks, parent_position)
        direct_children = sum(
            child.depth == parent_ref.task.depth + 1
            for child in day.tasks[parent_position + 1 : insert_at]
        )
        if direct_children >= 26:
            raise ValueError("A task may have at most 26 direct subtasks")
        task.depth = parent_ref.task.depth + 1
        day.tasks.insert(insert_at, task)
    write_state(path, state)
    return task


def add_note(notes_dir: Path, target_date: date, text: str) -> list[str]:
    """Roll unfinished work forward, then append a note paragraph."""
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    if day.notes and day.notes[-1].strip():
        day.notes.append("")
    day.notes.extend(text.splitlines() or [""])
    write_state(path, state)
    return day.notes


def list_tasks(notes_dir: Path, target_date: date, tag: str | None = None) -> list[Task]:
    """Return today's incomplete tasks after rollover, ordered Today then Old."""
    rollover(notes_dir, target_date)
    state = ensure_state(file_path(notes_dir, target_date))
    day = state.days.get(target_date)
    if day is None:
        return []
    tasks = _active_tasks_for_list(day, target_date)
    return _filter_tasks_by_tag(tasks, tag)


def list_finished_tasks(notes_dir: Path, target_date: date, tag: str | None = None) -> list[Task]:
    """Return completed tasks stored on the target day."""
    rollover(notes_dir, target_date)
    state = ensure_state(file_path(notes_dir, target_date))
    day = state.days.get(target_date)
    if day is None:
        return []
    tasks = [task for task in day.tasks if task.done]
    _normalize_task_depths(tasks)
    return _filter_tasks_by_tag(tasks, tag)


def list_future_tasks(
    notes_dir: Path, target_date: date, tag: str | None = None
) -> list[tuple[date, Task]]:
    """Scan month files for incomplete tasks scheduled after the target day."""
    if not notes_dir.exists():
        return []

    future_tasks: list[tuple[date, Task]] = []
    normalized_tag = tag.strip().lower() if tag is not None else None
    for path in sorted(notes_dir.rglob("*.md")):
        if not is_month_file(path):
            continue
        state = ensure_state(path)
        for day_date in sorted(state.days):
            if day_date <= target_date:
                continue
            day = state.days[day_date]
            for task in day.tasks:
                if task.done:
                    continue
                if normalized_tag is not None and normalized_tag not in task.tags:
                    continue
                future_tasks.append((day_date, task))
    return future_tasks


def list_task_refs(notes_dir: Path, target_date: date) -> list[TaskRef]:
    """Create the single active-then-future sequence used by every task index."""
    pairs = [(target_date, task) for task in list_tasks(notes_dir, target_date)]
    pairs.extend(list_future_tasks(notes_dir, target_date))
    return _identify_task_refs(pairs)


def complete_task(notes_dir: Path, target_date: date, index: str | int) -> Task:
    return complete_tasks(notes_dir, target_date, [index])[0]


def complete_tasks(notes_dir: Path, target_date: date, indexes: list[str | int]) -> list[Task]:
    """Complete several global indexes without index shifting between updates."""
    refs = _select_task_refs(notes_dir, target_date, indexes)
    _mutate_refs(notes_dir, refs, lambda task: setattr(task, "done", True))
    return [ref.task for ref in refs]


def delete_task(notes_dir: Path, target_date: date, index: str | int) -> Task:
    return delete_tasks(notes_dir, target_date, [index])[0]


def delete_tasks(notes_dir: Path, target_date: date, indexes: list[str | int]) -> list[Task]:
    """Remove selected incomplete tasks from each scheduled day."""
    refs = _select_task_refs(notes_dir, target_date, indexes)
    for scheduled, selected in _group_refs(refs).items():
        path = file_path(notes_dir, scheduled)
        state = ensure_state(path)
        day = state.days.setdefault(scheduled, DayState())
        positions = _selected_subtree_positions(day.tasks, selected)
        day.tasks = [task for position, task in enumerate(day.tasks) if position not in positions]
        write_state(path, state)
    return [ref.task for ref in refs]


def edit_task(notes_dir: Path, target_date: date, index: str | int, text: str) -> Task:
    """Replace task text while retaining scheduling and creation dates."""
    ref = _select_task_refs(notes_dir, target_date, [index])[0]
    _mutate_refs(notes_dir, [ref], lambda task: setattr(task, "text", text), cascade=False)
    return ref.task


def move_task(notes_dir: Path, target_date: date, index: str | int, destination_date: date) -> Task:
    return move_tasks(notes_dir, target_date, [index], destination_date)[0]


def move_tasks(
    notes_dir: Path, target_date: date, indexes: list[str | int], destination_date: date
) -> list[Task]:
    """Relocate selected global indexes to one future scheduled date."""
    if destination_date <= target_date:
        raise ValueError("Move destination must be a future date")
    refs = _select_task_refs(notes_dir, target_date, indexes)
    if any(ref.scheduled == destination_date for ref in refs):
        raise ValueError("Move destination must be different from the current scheduled date")
    _move_refs(notes_dir, refs, destination_date)
    return [ref.task for ref in refs]


def unmove_task(notes_dir: Path, target_date: date, index: str | int) -> Task:
    return unmove_tasks(notes_dir, target_date, [index])[0]


def unmove_tasks(notes_dir: Path, target_date: date, indexes: list[str | int]) -> list[Task]:
    """Bring selected future tasks back to the target day's active list."""
    refs = _select_task_refs(notes_dir, target_date, indexes)
    if any(ref.scheduled <= target_date for ref in refs):
        raise ValueError("Only future tasks can be unmoved")
    _move_refs(notes_dir, refs, target_date)
    return [ref.task for ref in refs]


def tag_task(notes_dir: Path, target_date: date, index: str | int, tags: list[str]) -> Task:
    return tag_tasks(notes_dir, target_date, [index], tags)[0]


def tag_tasks(
    notes_dir: Path, target_date: date, indexes: list[str | int], tags: list[str]
) -> list[Task]:
    """Add normalized unique tags while preserving priority and task body."""
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        raise ValueError("At least one non-empty tag is required")
    refs = _select_task_refs(notes_dir, target_date, indexes)

    def add_tags(task: Task) -> None:
        priority, existing, body = split_task_prefix(task.text)
        merged = existing + [tag for tag in normalized_tags if tag not in existing]
        task.text = format_task_text(priority, merged, body)

    _mutate_refs(notes_dir, refs, add_tags)
    return [ref.task for ref in refs]


def untag_tasks(
    notes_dir: Path, target_date: date, indexes: list[str | int], tags: list[str]
) -> list[Task]:
    """Remove matching tags while preserving priority and unrelated tags."""
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        raise ValueError("At least one non-empty tag is required")
    refs = _select_task_refs(notes_dir, target_date, indexes)

    def remove_tags(task: Task) -> None:
        priority, existing, body = split_task_prefix(task.text)
        remaining = [tag for tag in existing if tag not in normalized_tags]
        task.text = format_task_text(priority, remaining, body)

    _mutate_refs(notes_dir, refs, remove_tags)
    return [ref.task for ref in refs]


def prioritize_task(notes_dir: Path, target_date: date, index: str | int, priority: str | int) -> Task:
    return prioritize_tasks(notes_dir, target_date, [index], priority)[0]


def prioritize_tasks(
    notes_dir: Path, target_date: date, indexes: list[str | int], priority: str | int
) -> list[Task]:
    """Set or clear priority on multiple globally indexed tasks."""
    normalized = normalize_priority(priority, allow_none=True)
    refs = _select_task_refs(notes_dir, target_date, indexes)

    def set_priority(task: Task) -> None:
        _, tags, body = split_task_prefix(task.text)
        task.text = format_task_text(normalized, tags, body)

    _mutate_refs(notes_dir, refs, set_priority)
    return [ref.task for ref in refs]


def rollover(notes_dir: Path, target_date: date) -> None:
    """Move all earlier unfinished work into ``target_date`` exactly once."""
    target_path = file_path(notes_dir, target_date)
    target_state = ensure_state(target_path)

    while True:
        prior = _find_latest_prior_day(notes_dir, target_date)
        if prior is None:
            return
        previous_path, previous_date = prior
        target_state = _carry_tasks_forward(target_path, target_state, previous_path, previous_date, target_date)


def _carry_tasks_forward(
    target_path: Path,
    target_state: FileState,
    previous_path: Path,
    previous_date: date,
    target_date: date,
) -> FileState:
    """Transfer unfinished tasks from one prior day, preserving creation dates."""
    if previous_path == target_path:
        state = target_state
        previous_state = state
    else:
        state = target_state
        previous_state = ensure_state(previous_path)

    previous_day = previous_state.days[previous_date]
    carry = [task for task in previous_day.tasks if not task.done]
    day = state.days.setdefault(target_date, DayState())
    existing_keys = {task.key() for task in day.tasks}
    for task in carry:
        if task.key() not in existing_keys:
            day.tasks.append(
                Task(text=task.text, created=task.created, done=False, depth=task.depth)
            )

    previous_day.tasks = [task for task in previous_day.tasks if task.done]
    _normalize_task_depths(previous_day.tasks)
    if previous_path == target_path:
        write_state(target_path, state)
        return state

    write_state(previous_path, previous_state)
    write_state(target_path, state)
    return state


def _find_latest_prior_day(notes_dir: Path, target_date: date) -> tuple[Path, date] | None:
    """Find the newest earlier day that still contains unfinished work."""
    if not notes_dir.exists():
        return None

    latest: tuple[Path, date] | None = None
    for path in notes_dir.rglob("*.md"):
        if not is_month_file(path):
            continue
        state = ensure_state(path)
        for day_date, day in state.days.items():
            if day_date >= target_date:
                continue
            if not any(not task.done for task in day.tasks):
                continue
            if latest is None or day_date > latest[1]:
                latest = (path, day_date)
    return latest


def _select_task_refs(
    notes_dir: Path, target_date: date, indexes: list[str | int]
) -> list[TaskRef]:
    """Resolve and validate global one-based indexes before any mutation occurs."""
    refs = list_task_refs(notes_dir, target_date)
    identifiers = _validated_indexes(indexes, refs)
    by_identifier = {ref.identifier: ref for ref in refs}
    return [by_identifier[identifier] for identifier in identifiers]


def _group_refs(refs: list[TaskRef]) -> dict[date, list[TaskRef]]:
    """Group selections by physical day so each month state is rewritten once."""
    grouped: dict[date, list[TaskRef]] = {}
    for ref in refs:
        grouped.setdefault(ref.scheduled, []).append(ref)
    return grouped


def _mutate_refs(notes_dir: Path, refs: list[TaskRef], mutate, *, cascade: bool = True) -> None:
    """Apply one mutation to persisted tasks and synchronize returned snapshots."""
    for scheduled, selected in _group_refs(refs).items():
        path = file_path(notes_dir, scheduled)
        state = ensure_state(path)
        day = state.days.setdefault(scheduled, DayState())
        positions = (
            _selected_subtree_positions(day.tasks, selected)
            if cascade
            else {_find_task_position(day.tasks, ref.task.key()) for ref in selected}
        )
        for position in positions:
            mutate(day.tasks[position])
        write_state(path, state)
    for ref in refs:
        mutate(ref.task)


def _move_refs(notes_dir: Path, refs: list[TaskRef], destination: date) -> None:
    """Load all affected files before relocating tasks and writing each once."""
    paths = {file_path(notes_dir, ref.scheduled) for ref in refs}
    paths.add(file_path(notes_dir, destination))
    states = {path: ensure_state(path) for path in paths}

    for scheduled, selected in _group_refs(refs).items():
        source_day = states[file_path(notes_dir, scheduled)].days.setdefault(scheduled, DayState())
        roots = _selected_root_positions(source_day.tasks, selected)
        positions = _positions_for_roots(source_day.tasks, roots)
        moving: list[Task] = []
        for position, task in enumerate(source_day.tasks):
            if position not in positions:
                continue
            root = max(root for root in roots if root <= position)
            moving.append(
                Task(task.text, task.created, task.done, task.depth - source_day.tasks[root].depth)
            )
        source_day.tasks = [
            task for position, task in enumerate(source_day.tasks) if position not in positions
        ]
        destination_day = states[file_path(notes_dir, destination)].days.setdefault(
            destination, DayState()
        )
        destination_day.tasks.extend(moving)

    for path, state in states.items():
        write_state(path, state)


def _active_tasks_for_list(day: DayState, target_date: date) -> list[Task]:
    """Order incomplete tasks created today before carried-forward tasks."""
    subtrees: list[list[Task]] = []
    for task in day.tasks:
        if task.depth == 0:
            subtrees.append([])
        if not task.done:
            subtrees[-1].append(task)
    today = [tree for tree in subtrees if tree and tree[0].created == target_date]
    old = [tree for tree in subtrees if tree and tree[0].created != target_date]
    return [task for tree in today + old for task in tree]


def _filter_tasks_by_tag(tasks: list[Task], tag: str | None) -> list[Task]:
    if tag is None:
        return tasks
    normalized_tag = tag.strip().lower()
    return [task for task in tasks if normalized_tag in task.tags]


def _normalize_task_depths(tasks: list[Task]) -> None:
    """Promote tasks whose ancestors were removed without changing relative nesting."""
    ancestor_depths: list[int] = []
    for task in tasks:
        original_depth = task.depth
        while ancestor_depths and ancestor_depths[-1] >= original_depth:
            ancestor_depths.pop()
        task.depth = len(ancestor_depths)
        ancestor_depths.append(original_depth)


def _dedupe_indexes(indexes: list[str | int]) -> list[str]:
    """Keep the first occurrence of each index so an action runs only once."""
    deduped: list[str] = []
    seen: set[str] = set()
    for index in indexes:
        identifier = str(index).lower()
        if identifier in seen:
            continue
        deduped.append(identifier)
        seen.add(identifier)
    return deduped


def _validated_indexes(indexes: list[str | int], refs: list[TaskRef]) -> list[str]:
    """Deduplicate and validate one-based indexes as a complete batch."""
    unique_indexes = _dedupe_indexes(indexes)
    if not unique_indexes:
        raise ValueError("At least one task index is required")
    valid = {ref.identifier for ref in refs}
    for index in unique_indexes:
        if index not in valid:
            raise IndexError(f"Task index {index} is out of range")
    return unique_indexes


def _identify_task_refs(pairs: list[tuple[date, Task]]) -> list[TaskRef]:
    refs: list[TaskRef] = []
    root_created: date | None = None
    active_pairs = [(scheduled, task) for scheduled, task in pairs if not task.done]
    identifiers = task_identifiers([task for _, task in active_pairs])
    for (scheduled, task), identifier in zip(active_pairs, identifiers):
        if task.depth == 0:
            root_created = task.created
        refs.append(TaskRef(scheduled, task, identifier, root_created))
    return refs


def _find_task_position(tasks: list[Task], key: tuple[str, date, int]) -> int:
    for position, task in enumerate(tasks):
        if task.key() == key:
            return position
    raise RuntimeError("Task disappeared before update")


def _subtree_end(tasks: list[Task], position: int) -> int:
    depth = tasks[position].depth
    end = position + 1
    while end < len(tasks) and tasks[end].depth > depth:
        end += 1
    return end


def _selected_subtree_positions(tasks: list[Task], refs: list[TaskRef]) -> set[int]:
    return _positions_for_roots(tasks, _selected_root_positions(tasks, refs))


def _selected_root_positions(tasks: list[Task], refs: list[TaskRef]) -> list[int]:
    candidates = sorted(_find_task_position(tasks, ref.task.key()) for ref in refs)
    roots: list[int] = []
    for position in candidates:
        if roots and position < _subtree_end(tasks, roots[-1]):
            continue
        roots.append(position)
    return roots


def _positions_for_roots(tasks: list[Task], roots: list[int]) -> set[int]:
    positions: set[int] = set()
    for start in roots:
        positions.update(range(start, _subtree_end(tasks, start)))
    return positions
