from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re


DAY_HEADER_RE = re.compile(r"^## ([A-Za-z]{3})-(\d{2}) ([A-Za-z]{3})$")
TASK_LINE_RE = re.compile(r"^- \[( |x)\] (.*?)(?: \((\d{2}-\d{2})\))?$")
MONTH_FILE_RE = re.compile(r"^(\d{4})_(\d{2})_([a-z]{3})$")
TASKS_HEADING = "### Tasks"
NOTES_HEADING = "### Notes"


@dataclass(slots=True)
class Task:
    text: str
    created: date
    done: bool

    @property
    def tags(self) -> tuple[str, ...]:
        return parse_leading_tags(self.text)

    def key(self) -> tuple[str, date]:
        return (self.text, self.created)


@dataclass(slots=True)
class DayState:
    tasks: list[Task] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FileState:
    prefix: str
    days: dict[date, DayState]
    normalized: bool = False


def file_path(notes_dir: Path, target_date: date) -> Path:
    month_name = target_date.strftime("%b").lower()
    return notes_dir / f"{target_date:%Y}" / f"{target_date:%Y_%m}_{month_name}.md"


def parse_file(content: str, default_year: int | None = None) -> FileState:
    lines = content.splitlines()
    prefix_lines: list[str] = []
    days: dict[date, DayState] = {}
    current_day: DayState | None = None
    section: str | None = None

    for line in lines:
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
            current_day.tasks.append(parse_task_line(line, current_date))
            continue

        if section == "notes":
            if not current_day.notes and not line.strip():
                continue
            current_day.notes.append(line)
            continue

    return FileState(prefix="\n".join(prefix_lines), days=days, normalized=False)


def render_file(state: FileState) -> str:
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
    return parse_file(path.read_text(encoding="utf-8"), default_year=file_year_from_path(path))


def write_state(path: Path, state: FileState) -> None:
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
    return f"- [{status}] {task.text} ({task.created:%m-%d})"


def parse_task_line(line: str, section_date: date) -> Task:
    match = TASK_LINE_RE.match(line)
    if match is None:
        raise ValueError(f"Invalid task line: {line}")
    done = match.group(1) == "x"
    text = match.group(2)
    date_token = match.group(3)
    created = parse_compact_date(date_token, section_date) if date_token else section_date
    return Task(text=text, created=created, done=done)


def parse_compact_date(value: str, section_date: date) -> date:
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


def parse_leading_tags(text: str) -> tuple[str, ...]:
    tags, _ = split_leading_tags_and_body(text)
    return tuple(tags)


def split_leading_tags_and_body(text: str) -> tuple[list[str], str]:
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
    body = remaining.lstrip()
    if not body:
        body = text.strip()
    return tags, body


def normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip().strip("[]").strip().lower()
        if not value:
            continue
        if value not in normalized:
            normalized.append(value)
    return normalized
