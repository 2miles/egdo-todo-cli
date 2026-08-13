"""Parse and deterministically rewrite egdo's monthly Markdown files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re


DAY_HEADER_RE = re.compile(r"^## ([A-Za-z]{3})-(\d{2}) ([A-Za-z]{3})$")
TASK_LINE_RE = re.compile(r"^( *)- \[( |x)\] (.*?)(?: \((\d{2}-\d{2})\))?$")
MONTH_FILE_RE = re.compile(r"^(\d{4})_(\d{2})_([a-z]{3})$")
IMPORTANT_TOKEN_RE = re.compile(r"^!(?:\s+|$)")
TASKS_HEADING = "### Tasks"
NOTES_HEADING = "### Notes"


@dataclass(slots=True)
class Task:
    """A checklist item with its original creation date."""
    text: str
    created: date
    done: bool
    depth: int = 0

    @property
    def tag(self) -> str | None:
        return parse_leading_tag(self.text)

    def key(self) -> tuple[str, date, int]:
        return (self.text, self.created, self.depth)


@dataclass(slots=True)
class DayState:
    """The tasks and free-form notes stored under one daily heading."""
    tasks: list[Task] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FileState:
    """Parsed month content, including text before the first managed day."""
    prefix: str
    days: dict[date, DayState]
    normalized: bool = False


def file_path(notes_dir: Path, target_date: date) -> Path:
    month_name = target_date.strftime("%b").lower()
    return notes_dir / f"{target_date:%Y}" / f"{target_date:%Y_%m}_{month_name}.md"


def parse_file(content: str, default_year: int | None = None) -> FileState:
    """Parse day sections while preserving content before the first day header."""
    lines = content.splitlines()
    prefix_lines: list[str] = []
    days: dict[date, DayState] = {}
    current_day: DayState | None = None
    section: str | None = None

    for line_number, line in enumerate(lines, start=1):
        header = DAY_HEADER_RE.match(line)
        if header:
            if default_year is None:
                raise ValueError("Month file year is required to parse day headers")
            month = datetime.strptime(header.group(1), "%b").month
            day_of_month = int(header.group(2))
            current_date = date(default_year, month, day_of_month)
            current_day = days.setdefault(current_date, DayState())
            section = None
            continue

        if current_day is None:
            prefix_lines.append(line)
            continue

        if line == TASKS_HEADING:
            section = "tasks"
            continue
        if line == NOTES_HEADING:
            section = "notes"
            continue

        if section == "tasks":
            if not line.strip():
                continue
            try:
                task = parse_task_line(line, current_date)
            except ValueError as exc:
                raise ValueError(f"Line {line_number}: {exc}") from exc
            if task.depth and not current_day.tasks:
                raise ValueError("A nested task must follow a parent task")
            if current_day.tasks and task.depth > current_day.tasks[-1].depth + 1:
                raise ValueError("Task nesting cannot skip a level")
            current_day.tasks.append(task)
            continue

        if section == "notes":
            if not current_day.notes and not line.strip():
                continue
            current_day.notes.append(line)
            continue

    for day in days.values():
        _complete_descendants_of_done_tasks(day.tasks)
    return FileState(prefix="\n".join(prefix_lines), days=days, normalized=False)


def render_file(state: FileState) -> str:
    """Render populated bounds deterministically, including empty days between them."""
    sections: list[str] = []
    prefix = state.prefix.strip()
    if prefix:
        sections.append(prefix)

    populated_days = [
        day_date for day_date, day in state.days.items() if day.tasks or notes_have_content(day.notes)
    ]
    if populated_days:
        for day_date in day_range(min(populated_days), max(populated_days)):
            day = state.days.get(day_date, DayState())
            sections.append(render_day(day_date, day))

    if not sections:
        return ""
    return "\n\n".join(sections).rstrip() + "\n"


def ensure_state(path: Path) -> FileState:
    if not path.exists():
        return FileState(prefix="", days={})
    try:
        return parse_file(
            path.read_text(encoding="utf-8"), default_year=file_year_from_path(path)
        )
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def write_state(path: Path, state: FileState) -> None:
    """Persist a state, removing the month file when it has no content."""
    content = render_file(state)
    if not content:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def is_month_file(path: Path) -> bool:
    return MONTH_FILE_RE.match(path.stem) is not None


def file_year_from_path(path: Path) -> int | None:
    match = MONTH_FILE_RE.match(path.stem)
    if match is None:
        return None
    return int(match.group(1))


def render_day(day_date: date, day: DayState) -> str:
    """Render one canonical day section, omitting empty subsections."""
    lines = [f"## {day_date:%b-%d} {day_date.strftime('%a')}"]
    if day.tasks:
        lines.extend(["", TASKS_HEADING, ""])
        lines.extend(render_task(task) for task in day.tasks)
    if notes_have_content(day.notes):
        lines.extend(["", NOTES_HEADING, ""])
        lines.extend(day.notes)
    return "\n".join(lines).rstrip()


def render_task(task: Task) -> str:
    status = "x" if task.done else " "
    return f"{'  ' * task.depth}- [{status}] {task.text} ({task.created:%m-%d})"


def parse_task_line(line: str, section_date: date) -> Task:
    """Parse a checklist line, defaulting a missing creation date to its section."""
    match = TASK_LINE_RE.match(line)
    if match is None:
        raise ValueError(f"Invalid task line: {line}")
    indent = match.group(1)
    if len(indent) % 2:
        raise ValueError("Nested tasks must use two spaces per level")
    depth = len(indent) // 2
    if depth > 2:
        raise ValueError("Tasks may be nested at most three levels deep")
    done = match.group(2) == "x"
    text = match.group(3)
    important, tag, body = split_task_prefix(text)
    text = format_task_text(important, tag, body)
    date_token = match.group(4)
    created = parse_compact_date(date_token, section_date) if date_token else section_date
    return Task(text=text, created=created, done=done, depth=depth)


def _complete_descendants_of_done_tasks(tasks: list[Task]) -> None:
    """Enforce that a completed parent owns no unfinished descendants."""
    completed_depth: int | None = None
    for task in tasks:
        if completed_depth is not None and task.depth > completed_depth:
            task.done = True
            continue
        completed_depth = task.depth if task.done else None


def parse_compact_date(value: str, section_date: date) -> date:
    """Infer the creation year, allowing December tasks to roll into January."""
    month = int(value[:2])
    day = int(value[3:5])
    candidate = date(section_date.year, month, day)
    if candidate > section_date:
        return date(section_date.year - 1, month, day)
    return candidate


def notes_have_content(lines: list[str]) -> bool:
    return any(line.strip() for line in lines)


def day_range(start: date, end: date) -> list[date]:
    dates: list[date] = []
    current = start
    while current <= end:
        dates.append(current)
        current = current.fromordinal(current.toordinal() + 1)
    return dates


def parse_leading_tag(text: str) -> str | None:
    _, tag, _ = split_task_prefix(text)
    return tag


def task_identifiers(tasks: list[Task]) -> list[str]:
    """Assign numeric, lettered, and dotted display IDs to a preorder task list."""
    identifiers: list[str] = []
    top_index = 0
    child_counts = [0, 0, 0]
    parent_ids = ["", "", ""]
    for task in tasks:
        depth = getattr(task, "depth", 0)
        if depth == 0:
            top_index += 1
            identifier = str(top_index)
            child_counts = [0, 0, 0]
        else:
            child_counts[depth] += 1
            if child_counts[depth] > 26:
                raise ValueError("A task may have at most 26 direct subtasks")
            child_counts[depth + 1 :] = [0] * (2 - depth)
            letter = chr(ord("a") + child_counts[depth] - 1)
            separator = "" if depth == 1 else "."
            identifier = f"{parent_ids[depth - 1]}{separator}{letter}"
        parent_ids[depth] = identifier
        identifiers.append(identifier)
    return identifiers


def split_task_prefix(text: str) -> tuple[bool, str | None, str]:
    """Extract the leading priority and optional tag from a task body."""
    important = False
    tag: str | None = None
    remaining = text.lstrip()
    while True:
        important_match = IMPORTANT_TOKEN_RE.match(remaining)
        if important_match is not None:
            important = True
            remaining = remaining[important_match.end() :].lstrip()
            continue
        parsed = _parse_tag_token(remaining)
        if parsed is None:
            break
        parsed_tag, tag_remaining = parsed
        if tag is not None:
            break
        tag = parsed_tag
        remaining = tag_remaining
        remaining = remaining.lstrip()
    body = remaining.lstrip()
    if not body and not important and tag is None:
        body = text.strip()
    return important, tag, body


def normalize_priority(value: str | int | None) -> bool | None:
    """Map the two supported priority names to important or normal."""
    if value is None:
        return None
    normalized = str(value).strip().lower()
    aliases = {
        "important": True,
        "normal": False,
    }
    if normalized not in aliases:
        raise ValueError(f"Invalid priority `{value}`. Use important or normal.")
    return aliases[normalized]


def merge_priority_into_text(text: str, value: str | int | None) -> str:
    """Replace a task's priority while preserving its tags and body."""
    existing_priority, tag, body = split_task_prefix(text)
    priority = existing_priority if value is None else normalize_priority(value)
    assert priority is not None
    return format_task_text(priority, tag, body)


def format_task_text(priority: bool, tag: str | None, body: str) -> str:
    """Rebuild task text in canonical priority, tag, then body order."""
    parts: list[str] = []
    if priority:
        parts.append("!")
    if tag is not None:
        parts.append(_format_tag(tag))
    if body:
        parts.append(body)
    return " ".join(parts)


def merge_tag_into_text(text: str, tag: str | None) -> str:
    """Set one optional tag while preserving priority and task body."""
    priority, existing_tag, body = split_task_prefix(text)
    if tag is None:
        return format_task_text(priority, existing_tag, body)
    normalized = _normalize_tag_value(tag)
    if not normalized:
        raise ValueError("Tag cannot be empty")
    return format_task_text(priority, normalized, body)


def _format_tag(tag: str) -> str:
    return f"{{{tag.upper()}}}"


def _normalize_tag_value(tag: str) -> str:
    return tag.strip().strip("{}").strip().lower()


def _parse_tag_token(text: str) -> tuple[str, str] | None:
    """Consume one leading brace tag and return its unparsed remainder."""
    if text.startswith("{"):
        closing = text.find("}")
        if closing <= 1:
            return None
        tag = _normalize_tag_value(text[1:closing])
        if not tag:
            return None
        return (tag, text[closing + 1 :])
    return None
