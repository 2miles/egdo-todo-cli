"""Read and write egdo's named project roots."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
import shutil


CONFIG_PATH = Path.home() / ".config" / "egdo" / "config.toml"
MAIN_PROJECT = "Main"


@dataclass(slots=True)
class Config:
    """The active project plus every named storage root."""

    projects: dict[str, Path]
    default_project: str = MAIN_PROJECT
    project_name: str | None = None

    def __post_init__(self) -> None:
        if not self.projects:
            raise ValueError("At least one project is required")
        self.projects = {
            name: project_root.expanduser()
            for name, project_root in self.projects.items()
        }
        self.default_project = resolve_project_name(
            self.projects, self.default_project
        )
        self.project_name = resolve_project_name(
            self.projects, self.project_name or self.default_project
        )

    @property
    def root(self) -> Path:
        """Return the selected project's root without storing duplicate state."""
        assert self.project_name is not None
        return self.projects[self.project_name]

    def select(self, name: str) -> Config:
        """Return a copy with the case-insensitively named project active."""
        project_name = resolve_project_name(self.projects, name)
        return replace(
            self,
            project_name=project_name,
        )


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load named projects, treating a legacy root as the Main project."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `egdo project add Main ~/Notes/egdo`."
        )

    raw = _parse_toml(path.read_text(encoding="utf-8"))
    raw_projects = raw.get("projects")
    if isinstance(raw_projects, dict) and raw_projects:
        projects = {
            str(name): Path(str(root)).expanduser()
            for name, root in raw_projects.items()
        }
        requested_default = str(raw.get("default_project", MAIN_PROJECT))
        default_project = resolve_project_name(projects, requested_default)
        return Config(
            projects=projects,
            default_project=default_project,
        )

    try:
        root = Path(str(raw["root"])).expanduser()
    except KeyError as exc:
        raise ValueError("Missing config: define [projects] or a legacy root") from exc
    return Config(projects={MAIN_PROJECT: root})


def save_config(config: Config, path: Path = CONFIG_PATH) -> Path:
    """Write project settings, preserving unrelated content and making a backup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    remaining = ""
    if path.exists():
        original = path.read_text(encoding="utf-8")
        shutil.copy2(path, path.with_suffix(f"{path.suffix}.bak"))
        remaining = _remove_managed_settings(original).strip("\n")

    lines = [f"default_project = {json.dumps(config.default_project)}", "", "[projects]"]
    for name, root in config.projects.items():
        lines.append(f"{json.dumps(name)} = {json.dumps(str(root.expanduser()))}")
    if remaining:
        lines.extend(["", remaining])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def add_project(config: Config, name: str, root: Path) -> Config:
    """Add a uniquely named project without changing the active default."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Project name cannot be empty")
    if any(existing.casefold() == cleaned_name.casefold() for existing in config.projects):
        raise ValueError(f'Project "{cleaned_name}" already exists')
    projects = dict(config.projects)
    projects[cleaned_name] = root.expanduser()
    return replace(config, projects=projects)


def create_config(name: str, root: Path) -> Config:
    """Create the first project configuration."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Project name cannot be empty")
    return Config(
        projects={cleaned_name: root.expanduser()},
        default_project=cleaned_name,
    )


def set_project_root(config: Config, name: str, root: Path) -> Config:
    """Change one project's location without moving any files."""
    project_name = resolve_project_name(config.projects, name)
    projects = dict(config.projects)
    projects[project_name] = root.expanduser()
    return replace(config, projects=projects)


def use_project(config: Config, name: str) -> Config:
    """Select a project and make it the persistent default."""
    selected = config.select(name)
    return replace(selected, default_project=selected.project_name)


def resolve_project_name(projects: dict[str, Path], requested: str) -> str:
    """Resolve a project name without making display capitalization significant."""
    normalized = requested.strip().casefold()
    for name in projects:
        if name.casefold() == normalized:
            return name
    available = ", ".join(projects) or "none"
    raise ValueError(f'Unknown project "{requested}". Available projects: {available}')


def _remove_managed_settings(content: str) -> str:
    """Remove root/project settings while retaining unrelated TOML content."""
    output: list[str] = []
    section: str | None = None
    in_projects = False
    for line in content.splitlines():
        stripped = line.strip()
        section_match = re.match(r"^\[([^]]+)]$", stripped)
        if section_match:
            section = section_match.group(1).strip()
            in_projects = section == "projects"
            if in_projects:
                continue
        if in_projects:
            continue
        if section is None and re.match(r"^\s*(?:root|default_project)\s*=", line):
            continue
        output.append(line)
    return "\n".join(output)


def _parse_toml(content: str) -> dict[str, object]:
    """Parse the small TOML subset used by egdo configuration."""
    raw: dict[str, object] = {}
    section: str | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            raw.setdefault(section, {})
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed_key = _parse_string(key.strip())
        parsed_value = _parse_string(value.strip())
        if section is not None:
            values = raw.setdefault(section, {})
            assert isinstance(values, dict)
            values[parsed_key] = parsed_value
        else:
            raw[parsed_key] = parsed_value
    return raw


def _parse_string(value: str) -> str:
    """Decode the quoted strings emitted by egdo, accepting legacy bare values."""
    if value.startswith('"') and value.endswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid quoted config value: {value}") from exc
        if isinstance(parsed, str):
            return parsed
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value
