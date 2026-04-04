from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

SECTION_HEADING = "## Egdo"
SECTION_START = "<!-- EGDO:START -->"
SECTION_END = "<!-- EGDO:END -->"


@dataclass(slots=True)
class Task:
    text: str
    created: date
    completed: date | None

    @property
    def done(self) -> bool:
        return self.completed is not None

    @property
    def tags(self) -> tuple[str, ...]:
        return _parse_leading_tags(self.text)

    def key(self) -> tuple[str, date]:
        return (self.text, self.created)


@dataclass(slots=True)
class FileState:
    prefix: str
    tasks: list[Task]
    suffix: str
    normalized: bool = False


def file_path(notes_dir: Path, target_date: date) -> Path:
    return notes_dir / f"{target_date:%Y}" / f"{target_date:%m}" / f"{target_date:%Y-%m-%d}.md"


def parse_task_block(lines: list[str], default_date: date | None) -> tuple[Task, bool]:
    if not lines:
        raise ValueError("Empty task block")
    first = lines[0]
    if not first.startswith("- ["):
        raise ValueError(f"Invalid task line: {first}")

    done = first.startswith("- [x] ")
    if done:
        text = first[len("- [x] ") :]
    else:
        text = first[len("- [ ] ") :]

    metadata: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        payload = stripped[2:]
        if ":" not in payload:
            continue
        key, value = payload.split(":", 1)
        metadata[key.strip()] = value.strip()

    normalized = False

    created = _parse_date(metadata.get("created"))
    completed = _parse_date(metadata.get("completed"))

    if created is None:
        if default_date is None:
            raise ValueError(f"Task is missing required created date: {lines}")
        created = default_date
        normalized = True

    if done and completed is None:
        if default_date is None:
            raise ValueError(f"Completed task is missing completion date: {lines}")
        completed = default_date
        normalized = True
    if not done:
        completed = None

    return Task(text=text, created=created, completed=completed), normalized


def parse_file(content: str, default_date: date | None = None) -> FileState:
    if SECTION_START not in content or SECTION_END not in content:
        return FileState(prefix=content, tasks=[], suffix="", normalized=False)

    start = content.index(SECTION_START)
    end = content.index(SECTION_END)
    if end < start:
        raise ValueError("Invalid egdo markers")

    prefix = _strip_managed_heading(content[:start])
    section = content[start + len(SECTION_START) : end]
    suffix = content[end + len(SECTION_END) :]

    lines = [line.rstrip("\n") for line in section.splitlines()]
    tasks: list[Task] = []
    normalized = False
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                task, task_normalized = parse_task_block(current, default_date)
                tasks.append(task)
                normalized = normalized or task_normalized
                current = []
            continue
        if line.startswith("- ["):
            if current:
                task, task_normalized = parse_task_block(current, default_date)
                tasks.append(task)
                normalized = normalized or task_normalized
            current = [line]
        elif current:
            current.append(line)
    if current:
        task, task_normalized = parse_task_block(current, default_date)
        tasks.append(task)
        normalized = normalized or task_normalized

    return FileState(prefix=prefix, tasks=tasks, suffix=suffix, normalized=normalized)


def render_file(state: FileState) -> str:
    section = _render_section(state.tasks)
    if SECTION_START in state.prefix or SECTION_END in state.suffix:
        raise ValueError("Unexpected marker duplication")
    if not state.prefix:
        return section
    return f"{state.prefix.rstrip()}\n\n{section}{state.suffix}"


def ensure_state(path: Path) -> FileState:
    if not path.exists():
        return FileState(prefix="", tasks=[], suffix="")
    return parse_file(path.read_text(encoding="utf-8"), default_date=_file_date_from_path(path))


def write_state(path: Path, state: FileState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_file(state), encoding="utf-8")


def add_task(notes_dir: Path, target_date: date, text: str) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    task = Task(text=text, created=target_date, completed=None)
    state.tasks.append(task)
    write_state(path, state)
    return task


def list_tasks(notes_dir: Path, target_date: date, tag: str | None = None) -> list[Task]:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    if state.normalized:
        write_state(path, state)
    tasks = [task for task in state.tasks if not task.done]
    if tag is None:
        return tasks
    normalized_tag = tag.strip().lower()
    return [task for task in tasks if normalized_tag in task.tags]


def complete_task(notes_dir: Path, target_date: date, index: int) -> Task:
    rollover(notes_dir, target_date)
    path = file_path(notes_dir, target_date)
    state = ensure_state(path)
    active = [task for task in state.tasks if not task.done]
    if index < 1 or index > len(active):
        raise IndexError(f"Task index {index} is out of range")

    selected_key = active[index - 1].key()
    for task in state.tasks:
        if task.key() == selected_key and not task.done:
            task.completed = target_date
            write_state(path, state)
            return task
    raise RuntimeError("Active task disappeared before completion")


def rollover(notes_dir: Path, target_date: date) -> None:
    target_path = file_path(notes_dir, target_date)
    target_state = ensure_state(target_path)
    if any(not task.done for task in target_state.tasks):
        return

    previous_path = _find_latest_prior_file(notes_dir, target_date)
    if previous_path is None:
        if target_path.exists() or target_state.tasks:
            write_state(target_path, target_state)
        return

    previous_state = ensure_state(previous_path)
    carry = [task for task in previous_state.tasks if not task.done]
    if not carry:
        if target_path.exists() or target_state.tasks:
            write_state(target_path, target_state)
        return

    existing_keys = {task.key() for task in target_state.tasks}
    for task in carry:
        if task.key() not in existing_keys:
            target_state.tasks.append(
                Task(
                    text=task.text,
                    created=task.created,
                    completed=None,
                )
            )

    previous_state.tasks = [task for task in previous_state.tasks if task.done]
    write_state(previous_path, previous_state)
    write_state(target_path, target_state)


def _find_latest_prior_file(notes_dir: Path, target_date: date) -> Path | None:
    if not notes_dir.exists():
        return None

    candidates: list[Path] = []
    for path in notes_dir.rglob("*.md"):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < target_date:
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stem)


def _file_date_from_path(path: Path) -> date | None:
    try:
        return datetime.strptime(path.stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def _strip_managed_heading(prefix: str) -> str:
    stripped = prefix.rstrip()
    if not stripped.endswith(SECTION_HEADING):
        return prefix
    heading_start = stripped.rfind(SECTION_HEADING)
    return stripped[:heading_start].rstrip()


def _render_section(tasks: Iterable[Task]) -> str:
    blocks = "\n\n".join(_render_task(task) for task in tasks)
    if blocks:
        blocks = f"\n\n{blocks}\n"
    else:
        blocks = "\n"
    return f"{SECTION_HEADING}\n{SECTION_START}{blocks}{SECTION_END}\n"


def _render_task(task: Task) -> str:
    status = "x" if task.done else " "
    completed = task.completed.isoformat() if task.completed else ""
    return "\n".join(
        [
            f"- [{status}] {task.text}",
            f"  - created: {task.created.isoformat()}",
            f"  - completed: {completed}",
        ]
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _parse_leading_tags(text: str) -> tuple[str, ...]:
    tags: list[str] = []
    remaining = text.lstrip()
    while remaining.startswith("["):
        closing = remaining.find("]")
        if closing <= 1:
            break
        tag = remaining[1:closing].strip().lower()
        if not tag:
            break
        if tag not in tags:
            tags.append(tag)
        remaining = remaining[closing + 1 :]
    return tuple(tags)
