from __future__ import annotations

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
from egdo.markdown_store import parse_file
from egdo.markdown_store import split_task_prefix
from egdo.markdown_store import write_state


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


def complete_future_task(notes_dir: Path, target_date: date, index: int) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    path = file_path(notes_dir, source_date)
    state = ensure_state(path)
    day = state.days.setdefault(source_date, DayState())
    for task in day.tasks:
        if task.key() == selected_task.key() and not task.done:
            task.done = True
            write_state(path, state)
            return task
    raise RuntimeError("Future task disappeared before completion")


def delete_future_task(notes_dir: Path, target_date: date, index: int) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    path = file_path(notes_dir, source_date)
    state = ensure_state(path)
    day = state.days.setdefault(source_date, DayState())
    for task_index, task in enumerate(day.tasks):
        if task.key() == selected_task.key() and not task.done:
            removed = day.tasks.pop(task_index)
            write_state(path, state)
            return removed
    raise RuntimeError("Future task disappeared before deletion")


def edit_future_task(notes_dir: Path, target_date: date, index: int, text: str) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    path = file_path(notes_dir, source_date)
    state = ensure_state(path)
    day = state.days.setdefault(source_date, DayState())
    for task in day.tasks:
        if task.key() == selected_task.key() and not task.done:
            task.text = text
            write_state(path, state)
            return task
    raise RuntimeError("Future task disappeared before editing")


def move_future_task(notes_dir: Path, target_date: date, index: int, destination_date: date) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    if destination_date <= target_date:
        raise ValueError("Move destination must be a future date")
    if destination_date == source_date:
        raise ValueError("Move destination must be different from the current future date")

    return _move_task_by_key(notes_dir, source_date, selected_task, destination_date)


def tag_future_task(notes_dir: Path, target_date: date, index: int, tags: list[str]) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    path = file_path(notes_dir, source_date)
    state = ensure_state(path)
    day = state.days.setdefault(source_date, DayState())
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        raise ValueError("At least one non-empty tag is required")

    for task in day.tasks:
        if task.key() == selected_task.key() and not task.done:
            priority, existing_tags, body = split_task_prefix(task.text)
            merged_tags = list(existing_tags)
            for tag in normalized_tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)
            task.text = format_task_text(priority, merged_tags, body)
            write_state(path, state)
            return task
    raise RuntimeError("Future task disappeared before tagging")


def prioritize_future_task(
    notes_dir: Path, target_date: date, index: int, priority: str | int
) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    path = file_path(notes_dir, source_date)
    state = ensure_state(path)
    day = state.days.setdefault(source_date, DayState())
    return _set_task_priority(path, state, day, selected_task, priority)


def complete_task(notes_dir: Path, target_date: date, index: int) -> Task:
    return complete_tasks(notes_dir, target_date, [index])[0]


def complete_tasks(notes_dir: Path, target_date: date, indexes: list[int]) -> list[Task]:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    active = _active_tasks_for_list(day, target_date)

    unique_indexes = _dedupe_indexes(indexes)
    if not unique_indexes:
        raise ValueError("At least one task index is required")
    for index in unique_indexes:
        if index < 1 or index > len(active):
            raise IndexError(f"Task index {index} is out of range")

    selected_tasks = [active[index - 1] for index in unique_indexes]
    selected_ids = {id(task) for task in selected_tasks}
    completed: list[Task] = []
    for task in day.tasks:
        if id(task) in selected_ids:
            task.done = True
            completed.append(task)

    if len(completed) != len(selected_tasks):
        raise RuntimeError("Active task disappeared before completion")

    write_state(path, state)
    return selected_tasks


def delete_task(notes_dir: Path, target_date: date, index: int) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    active = _active_tasks_for_list(day, target_date)
    if index < 1 or index > len(active):
        raise IndexError(f"Task index {index} is out of range")

    selected_task = active[index - 1]
    for idx, task in enumerate(day.tasks):
        if task is selected_task:
            removed = day.tasks.pop(idx)
            write_state(path, state)
            return removed
    raise RuntimeError("Active task disappeared before deletion")


def edit_task(notes_dir: Path, target_date: date, index: int, text: str) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    active = _active_tasks_for_list(day, target_date)
    if index < 1 or index > len(active):
        raise IndexError(f"Task index {index} is out of range")

    selected_task = active[index - 1]
    for task in day.tasks:
        if task is selected_task:
            task.text = text
            write_state(path, state)
            return task
    raise RuntimeError("Active task disappeared before editing")


def move_task(notes_dir: Path, source_date: date, index: int, destination_date: date) -> Task:
    if destination_date <= source_date:
        raise ValueError("Move destination must be a future date")

    rollover(notes_dir, source_date)
    source_path = file_path(notes_dir, source_date)
    source_state = ensure_state(source_path)
    source_day = source_state.days.setdefault(source_date, DayState())
    active = _active_tasks_for_list(source_day, source_date)
    if index < 1 or index > len(active):
        raise IndexError(f"Task index {index} is out of range")

    selected_task = active[index - 1]

    return _move_task_by_key(notes_dir, source_date, selected_task, destination_date)


def unmove_task(notes_dir: Path, target_date: date, index: int) -> Task:
    source_date, selected_task = _resolve_future_task_index(notes_dir, target_date, index)
    if source_date <= target_date:
        raise ValueError("Only future tasks can be unmoved")
    return _move_task_by_key(notes_dir, source_date, selected_task, target_date, rollover_target=True)


def tag_task(notes_dir: Path, target_date: date, index: int, tags: list[str]) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    active = _active_tasks_for_list(day, target_date)
    if index < 1 or index > len(active):
        raise IndexError(f"Task index {index} is out of range")

    selected_task = active[index - 1]
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        raise ValueError("At least one non-empty tag is required")

    for task in day.tasks:
        if task is selected_task:
            priority, existing_tags, body = split_task_prefix(task.text)
            merged_tags = list(existing_tags)
            for tag in normalized_tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)
            task.text = format_task_text(priority, merged_tags, body)
            write_state(path, state)
            return task
    raise RuntimeError("Active task disappeared before tagging")


def prioritize_task(notes_dir: Path, target_date: date, index: int, priority: str | int) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    day = state.days.setdefault(target_date, DayState())
    active = _active_tasks_for_list(day, target_date)
    if index < 1 or index > len(active):
        raise IndexError(f"Task index {index} is out of range")
    return _set_task_priority(path, state, day, active[index - 1], priority)


def _set_task_priority(
    path: Path,
    state: FileState,
    day: DayState,
    selected_task: Task,
    priority_value: str | int,
) -> Task:
    priority = normalize_priority(priority_value, allow_none=True)
    for task in day.tasks:
        if task is selected_task or task.key() == selected_task.key():
            _, tags, body = split_task_prefix(task.text)
            task.text = format_task_text(priority, tags, body)
            write_state(path, state)
            return task
    raise RuntimeError("Task disappeared before setting priority")


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


def _resolve_future_task_index(notes_dir: Path, target_date: date, index: int) -> tuple[date, Task]:
    future_tasks = list_future_tasks(notes_dir, target_date)
    if index < 1 or index > len(future_tasks):
        raise IndexError(f"Future task index {index} is out of range")
    return future_tasks[index - 1]


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


def _move_task_by_key(
    notes_dir: Path,
    source_date: date,
    selected_task: Task,
    destination_date: date,
    rollover_target: bool = False,
) -> Task:
    if rollover_target:
        rollover(notes_dir, destination_date)

    source_path = file_path(notes_dir, source_date)
    destination_path = file_path(notes_dir, destination_date)
    source_state = ensure_state(source_path)
    source_day = source_state.days.setdefault(source_date, DayState())

    selected_index: int | None = None
    for task_index, task in enumerate(source_day.tasks):
        if task.key() == selected_task.key() and not task.done:
            selected_index = task_index
            break
    if selected_index is None:
        raise RuntimeError("Task disappeared before moving")

    if source_path == destination_path:
        state = source_state
        destination_day = state.days.setdefault(destination_date, DayState())
        if any(task.key() == selected_task.key() for task in destination_day.tasks):
            raise ValueError(f"Task already exists on {destination_date.isoformat()}")
        source_day.tasks.pop(selected_index)
        destination_day.tasks.append(
            Task(text=selected_task.text, created=selected_task.created, done=False)
        )
        write_state(source_path, state)
        return selected_task

    destination_state = ensure_state(destination_path)
    destination_day = destination_state.days.setdefault(destination_date, DayState())
    if any(task.key() == selected_task.key() for task in destination_day.tasks):
        raise ValueError(f"Task already exists on {destination_date.isoformat()}")

    source_day.tasks.pop(selected_index)
    destination_day.tasks.append(
        Task(text=selected_task.text, created=selected_task.created, done=False)
    )
    write_state(source_path, source_state)
    write_state(destination_path, destination_state)
    return selected_task
