from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from egdo.markdown_store import DayState
from egdo.markdown_store import FileState
from egdo.markdown_store import Task
from egdo.markdown_store import ensure_state
from egdo.markdown_store import file_path
from egdo.markdown_store import format_task_text
from egdo.markdown_store import is_month_file
from egdo.markdown_store import normalize_tags
from egdo.markdown_store import normalize_priority
from egdo.markdown_store import split_task_prefix
from egdo.markdown_store import write_state


@dataclass(frozen=True, slots=True)
class TaskRef:
    scheduled: date
    task: Task


def add_task(notes_dir: Path, target_date: date, text: str) -> Task:
    return create_task(notes_dir, target_date, text, done=False)


def create_task(notes_dir: Path, target_date: date, text: str, done: bool) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    task = Task(text=text, created=target_date, done=done)
    day.tasks.append(task)
    write_state(path, state)
    return task


def add_note(notes_dir: Path, target_date: date, text: str) -> list[str]:
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    if day.notes and day.notes[-1].strip():
        day.notes.append("")
    day.notes.extend(text.splitlines() or [""])
    write_state(path, state)
    return day.notes


def list_tasks(notes_dir: Path, target_date: date, tag: str | None = None) -> list[Task]:
    rollover(notes_dir, target_date)
    state = ensure_state(file_path(notes_dir, target_date))
    day = state.days.get(target_date)
    if day is None:
        return []
    tasks = _active_tasks_for_list(day, target_date)
    if tag is None:
        return tasks
    normalized_tag = tag.strip().lower()
    return [task for task in tasks if normalized_tag in task.tags]


def list_finished_tasks(notes_dir: Path, target_date: date, tag: str | None = None) -> list[Task]:
    rollover(notes_dir, target_date)
    state = ensure_state(file_path(notes_dir, target_date))
    day = state.days.get(target_date)
    if day is None:
        return []
    tasks = [task for task in day.tasks if task.done]
    if tag is None:
        return tasks
    normalized_tag = tag.strip().lower()
    return [task for task in tasks if normalized_tag in task.tags]


def list_future_tasks(
    notes_dir: Path, target_date: date, tag: str | None = None
) -> list[tuple[date, Task]]:
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
    active = [TaskRef(target_date, task) for task in list_tasks(notes_dir, target_date)]
    future = [TaskRef(scheduled, task) for scheduled, task in list_future_tasks(notes_dir, target_date)]
    return active + future


def complete_task(notes_dir: Path, target_date: date, index: int) -> Task:
    return complete_tasks(notes_dir, target_date, [index])[0]


def complete_tasks(notes_dir: Path, target_date: date, indexes: list[int]) -> list[Task]:
    refs = _select_task_refs(notes_dir, target_date, indexes)
    _mutate_refs(notes_dir, refs, lambda task: setattr(task, "done", True))
    for ref in refs:
        ref.task.done = True
    return [ref.task for ref in refs]


def delete_task(notes_dir: Path, target_date: date, index: int) -> Task:
    return delete_tasks(notes_dir, target_date, [index])[0]


def delete_tasks(notes_dir: Path, target_date: date, indexes: list[int]) -> list[Task]:
    refs = _select_task_refs(notes_dir, target_date, indexes)
    for scheduled, selected in _group_refs(refs).items():
        path = file_path(notes_dir, scheduled)
        state = ensure_state(path)
        day = state.days.setdefault(scheduled, DayState())
        keys = {ref.task.key() for ref in selected}
        day.tasks = [task for task in day.tasks if task.done or task.key() not in keys]
        write_state(path, state)
    return [ref.task for ref in refs]


def edit_task(notes_dir: Path, target_date: date, index: int, text: str) -> Task:
    ref = _select_task_refs(notes_dir, target_date, [index])[0]
    _mutate_refs(notes_dir, [ref], lambda task: setattr(task, "text", text))
    ref.task.text = text
    return ref.task


def move_task(notes_dir: Path, target_date: date, index: int, destination_date: date) -> Task:
    return move_tasks(notes_dir, target_date, [index], destination_date)[0]


def move_tasks(
    notes_dir: Path, target_date: date, indexes: list[int], destination_date: date
) -> list[Task]:
    if destination_date <= target_date:
        raise ValueError("Move destination must be a future date")
    refs = _select_task_refs(notes_dir, target_date, indexes)
    if any(ref.scheduled == destination_date for ref in refs):
        raise ValueError("Move destination must be different from the current scheduled date")
    _move_refs(notes_dir, refs, destination_date)
    return [ref.task for ref in refs]


def unmove_task(notes_dir: Path, target_date: date, index: int) -> Task:
    return unmove_tasks(notes_dir, target_date, [index])[0]


def unmove_tasks(notes_dir: Path, target_date: date, indexes: list[int]) -> list[Task]:
    refs = _select_task_refs(notes_dir, target_date, indexes)
    if any(ref.scheduled <= target_date for ref in refs):
        raise ValueError("Only future tasks can be unmoved")
    _move_refs(notes_dir, refs, target_date)
    return [ref.task for ref in refs]


def tag_task(notes_dir: Path, target_date: date, index: int, tags: list[str]) -> Task:
    return tag_tasks(notes_dir, target_date, [index], tags)[0]


def tag_tasks(
    notes_dir: Path, target_date: date, indexes: list[int], tags: list[str]
) -> list[Task]:
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        raise ValueError("At least one non-empty tag is required")
    refs = _select_task_refs(notes_dir, target_date, indexes)

    def add_tags(task: Task) -> None:
        priority, existing, body = split_task_prefix(task.text)
        merged = existing + [tag for tag in normalized_tags if tag not in existing]
        task.text = format_task_text(priority, merged, body)

    _mutate_refs(notes_dir, refs, add_tags)
    for ref in refs:
        add_tags(ref.task)
    return [ref.task for ref in refs]


def untag_tasks(
    notes_dir: Path, target_date: date, indexes: list[int], tags: list[str]
) -> list[Task]:
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        raise ValueError("At least one non-empty tag is required")
    refs = _select_task_refs(notes_dir, target_date, indexes)

    def remove_tags(task: Task) -> None:
        priority, existing, body = split_task_prefix(task.text)
        remaining = [tag for tag in existing if tag not in normalized_tags]
        task.text = format_task_text(priority, remaining, body)

    _mutate_refs(notes_dir, refs, remove_tags)
    for ref in refs:
        remove_tags(ref.task)
    return [ref.task for ref in refs]


def prioritize_task(notes_dir: Path, target_date: date, index: int, priority: str | int) -> Task:
    return prioritize_tasks(notes_dir, target_date, [index], priority)[0]


def prioritize_tasks(
    notes_dir: Path, target_date: date, indexes: list[int], priority: str | int
) -> list[Task]:
    normalized = normalize_priority(priority, allow_none=True)
    refs = _select_task_refs(notes_dir, target_date, indexes)

    def set_priority(task: Task) -> None:
        _, tags, body = split_task_prefix(task.text)
        task.text = format_task_text(normalized, tags, body)

    _mutate_refs(notes_dir, refs, set_priority)
    for ref in refs:
        set_priority(ref.task)
    return [ref.task for ref in refs]


def rollover(notes_dir: Path, target_date: date) -> None:
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
            day.tasks.append(Task(text=task.text, created=task.created, done=False))

    previous_day.tasks = [task for task in previous_day.tasks if task.done]
    if previous_path == target_path:
        write_state(target_path, state)
        return state

    write_state(previous_path, previous_state)
    write_state(target_path, state)
    return state


def _find_latest_prior_day(notes_dir: Path, target_date: date) -> tuple[Path, date] | None:
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


def _select_task_refs(notes_dir: Path, target_date: date, indexes: list[int]) -> list[TaskRef]:
    refs = list_task_refs(notes_dir, target_date)
    selected_indexes = _validated_indexes(indexes, len(refs))
    return [refs[index - 1] for index in selected_indexes]


def _group_refs(refs: list[TaskRef]) -> dict[date, list[TaskRef]]:
    grouped: dict[date, list[TaskRef]] = {}
    for ref in refs:
        grouped.setdefault(ref.scheduled, []).append(ref)
    return grouped


def _mutate_refs(notes_dir: Path, refs: list[TaskRef], mutate) -> None:
    for scheduled, selected in _group_refs(refs).items():
        path = file_path(notes_dir, scheduled)
        state = ensure_state(path)
        day = state.days.setdefault(scheduled, DayState())
        keys = {ref.task.key() for ref in selected}
        matched = 0
        for task in day.tasks:
            if task.key() in keys and not task.done:
                mutate(task)
                matched += 1
        if matched < len(selected):
            raise RuntimeError("Task disappeared before update")
        write_state(path, state)


def _move_refs(notes_dir: Path, refs: list[TaskRef], destination: date) -> None:
    paths = {file_path(notes_dir, ref.scheduled) for ref in refs}
    paths.add(file_path(notes_dir, destination))
    states = {path: ensure_state(path) for path in paths}

    for scheduled, selected in _group_refs(refs).items():
        source_day = states[file_path(notes_dir, scheduled)].days.setdefault(scheduled, DayState())
        keys = {ref.task.key() for ref in selected}
        original_count = len(source_day.tasks)
        source_day.tasks = [
            task for task in source_day.tasks if task.done or task.key() not in keys
        ]
        if original_count - len(source_day.tasks) < len(selected):
            raise RuntimeError("Task disappeared before moving")

    destination_day = states[file_path(notes_dir, destination)].days.setdefault(
        destination, DayState()
    )
    existing_keys = {task.key() for task in destination_day.tasks}
    for ref in refs:
        if ref.task.key() in existing_keys:
            raise ValueError(f"Task already exists on {destination.isoformat()}")
        destination_day.tasks.append(
            Task(text=ref.task.text, created=ref.task.created, done=False)
        )
        existing_keys.add(ref.task.key())

    for path, state in states.items():
        write_state(path, state)


def _active_tasks_for_list(day: DayState, target_date: date) -> list[Task]:
    active = [task for task in day.tasks if not task.done]
    todays_tasks = [task for task in active if task.created == target_date]
    carried_tasks = [task for task in active if task.created != target_date]
    return todays_tasks + carried_tasks


def _dedupe_indexes(indexes: list[int]) -> list[int]:
    deduped: list[int] = []
    seen: set[int] = set()
    for index in indexes:
        if index in seen:
            continue
        deduped.append(index)
        seen.add(index)
    return deduped


def _validated_indexes(indexes: list[int], task_count: int) -> list[int]:
    unique_indexes = _dedupe_indexes(indexes)
    if not unique_indexes:
        raise ValueError("At least one task index is required")
    for index in unique_indexes:
        if index < 1 or index > task_count:
            raise IndexError(f"Task index {index} is out of range")
    return unique_indexes
