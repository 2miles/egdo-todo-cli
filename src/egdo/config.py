"""Read and write egdo's named project roots."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
import shutil


CONFIG_PATH = Path.home() / ".config" / "egdo" / "config.toml"
LOCAL_CONFIG_NAME = ".egdo.toml"
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


@dataclass(frozen=True, slots=True)
class LocalProject:
    """A project identity and root resolved from a local marker."""

    name: str
    root: Path
    marker_path: Path


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load the named project registry."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `egdo init Main` in your notes directory."
        )

    raw = _parse_toml(path.read_text(encoding="utf-8"))
    raw_projects = raw.get("projects")
    if not isinstance(raw_projects, dict) or not raw_projects:
        raise ValueError('Missing config: define at least one project in [projects]')
    projects = {
        str(name): Path(str(root)).expanduser()
        for name, root in raw_projects.items()
    }
    requested_default = str(raw.get("default_project", MAIN_PROJECT))
    default_project = resolve_project_name(projects, requested_default)
    return Config(projects=projects, default_project=default_project)


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


def register_initialized_project(
    config: Config | None, name: str, root: Path
) -> tuple[Config, bool]:
    """Register an initialized root, allowing an identical existing registration."""
    cleaned_name = _clean_project_name(name)
    normalized_root = root.expanduser().resolve()
    if config is None:
        return Config(
            projects={cleaned_name: normalized_root},
            default_project=cleaned_name,
        ), True

    matching_name = next(
        (
            existing
            for existing in config.projects
            if existing.casefold() == cleaned_name.casefold()
        ),
        None,
    )
    if matching_name is not None:
        if config.projects[matching_name].resolve() != normalized_root:
            if _registered_project_is_live(config.projects[matching_name], matching_name):
                raise ValueError(
                    f'Project "{matching_name}" is already active at '
                    f"{config.projects[matching_name]}"
                )
            projects = dict(config.projects)
            projects[matching_name] = normalized_root
            return replace(config, projects=projects), True
        return config, False

    for existing_name, existing_root in config.projects.items():
        if existing_root.resolve() == normalized_root:
            raise ValueError(
                f"Project root {normalized_root} is already registered as "
                f'"{existing_name}"'
            )
    projects = dict(config.projects)
    projects[cleaned_name] = normalized_root
    return replace(config, projects=projects), True


def initialize_local_marker(directory: Path, name: str) -> tuple[Path, bool]:
    """Create a local project marker and archive directory without fake history."""
    cleaned_name = _clean_project_name(name)
    directory = directory.expanduser().resolve()
    marker_path = directory / LOCAL_CONFIG_NAME
    root = directory / "egdo"
    canonical_content = f"project = {json.dumps(cleaned_name)}\n"

    if marker_path.exists():
        existing = read_local_project(marker_path)
        if existing.name.casefold() != cleaned_name.casefold():
            raise ValueError(
                f'{marker_path} already identifies project "{existing.name}"'
            )
        canonical_content = f"project = {json.dumps(existing.name)}\n"
        root.mkdir(parents=True, exist_ok=True)
        if marker_path.read_text(encoding="utf-8") != canonical_content:
            marker_path.write_text(canonical_content, encoding="utf-8")
            return root, True
        return root, False

    directory.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(canonical_content, encoding="utf-8")
    return root, True


def find_local_project(start: Path) -> LocalProject | None:
    """Find the nearest project marker at or above a working directory."""
    current = start.expanduser().resolve()
    for directory in (current, *current.parents):
        marker_path = directory / LOCAL_CONFIG_NAME
        if marker_path.exists():
            return read_local_project(marker_path)
    return None


def read_local_project(path: Path) -> LocalProject:
    """Read one local project identity and derive its sibling archive root."""
    raw = _parse_toml(path.read_text(encoding="utf-8"))
    project = raw.get("project")
    if not isinstance(project, str) or not project.strip():
        raise ValueError(f'{path} must define a non-empty "project" value')
    marker_directory = path.parent.resolve()
    root = marker_directory / "egdo"
    return LocalProject(project.strip(), root, path.resolve())


def select_project_for_directory(
    config: Config, explicit_project: str | None, directory: Path
) -> tuple[Config, bool]:
    """Apply explicit, nearest-marker, then default project precedence."""
    if explicit_project is not None:
        return config.select(explicit_project), False
    local_project = find_local_project(directory)
    if local_project is not None:
        try:
            project_name = resolve_project_name(config.projects, local_project.name)
        except ValueError as exc:
            raise ValueError(
                f'Local project "{local_project.name}" is not registered. '
                f"Run `egdo init {local_project.name}` from its directory."
            ) from exc
        registered_root = config.projects[project_name].resolve()
        if registered_root != local_project.root:
            if _registered_project_is_live(registered_root, project_name):
                raise ValueError(
                    f'Project "{project_name}" is also active at {registered_root}. '
                    "Remove the duplicate marker before relocating it."
                )
            projects = dict(config.projects)
            projects[project_name] = local_project.root
            return replace(config, projects=projects, project_name=project_name), True
        return config.select(project_name), False
    return config, False


def _registered_project_is_live(root: Path, name: str) -> bool:
    marker_path = root.expanduser().resolve().parent / LOCAL_CONFIG_NAME
    if not marker_path.exists():
        return False
    try:
        local_project = read_local_project(marker_path)
    except (OSError, ValueError):
        return False
    return (
        local_project.name.casefold() == name.casefold()
        and local_project.root == root.expanduser().resolve()
    )


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


def _clean_project_name(name: str) -> str:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Project name cannot be empty")
    return cleaned_name


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
        if section is None and re.match(r"^\s*default_project\s*=", line):
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
    """Decode quoted strings while allowing simple bare TOML keys and values."""
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
