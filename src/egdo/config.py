"""Read and write egdo's small TOML-like user configuration file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "egdo" / "config.toml"


@dataclass(slots=True)
class Config:
    root: Path
    tag_colors: dict[str, str]
    priority_styles: dict[str, str] = field(default_factory=dict)


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load the storage root and optional style tables from disk."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `egdo init --root /path/to/egdo`."
        )

    raw = _parse_toml(path.read_text(encoding="utf-8"))

    try:
        root = Path(raw["root"]).expanduser()
    except KeyError as exc:
        raise ValueError(f"Missing config key: {exc.args[0]}") from exc

    tag_colors = _parse_tag_colors(raw)
    priority_styles = _parse_priority_styles(raw)

    return Config(root=root, tag_colors=tag_colors, priority_styles=priority_styles)


def write_config(
    root: Path,
    path: Path = CONFIG_PATH,
    tag_colors: dict[str, str] | None = None,
    priority_styles: dict[str, str] | None = None,
) -> Path:
    """Rewrite configuration deterministically with alphabetized style keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'root = "{root.expanduser()}"\n'
    if tag_colors:
        content += "\n[tag_colors]\n"
        for tag, color in sorted(tag_colors.items()):
            content += f'{tag} = "{color}"\n'
    if priority_styles:
        content += "\n[priority_styles]\n"
        for priority, style in sorted(priority_styles.items()):
            content += f'{priority} = "{style}"\n'
    path.write_text(content, encoding="utf-8")
    return path


def save_config(config: Config, path: Path = CONFIG_PATH) -> Path:
    return write_config(
        root=config.root,
        path=path,
        tag_colors=config.tag_colors,
        priority_styles=config.priority_styles,
    )


def _parse_toml(content: str) -> dict[str, object]:
    """Parse only the TOML subset emitted by egdo, avoiding a runtime dependency."""
    raw: dict[str, object] = {}
    section: str | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            if section in {"tag_colors", "priority_styles"} and section not in raw:
                raw[section] = {}
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed_value = value.strip().strip('"').strip("'")
        if section in {"tag_colors", "priority_styles"}:
            values = raw.setdefault(section, {})
            assert isinstance(values, dict)
            values[key.strip()] = parsed_value
        else:
            raw[key.strip()] = parsed_value
    return raw


def _parse_tag_colors(raw: dict[str, object]) -> dict[str, str]:
    """Validate the tag-color table and normalize its keys for lookup."""
    value = raw.get("tag_colors")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Config key `tag_colors` must be a table")
    tag_colors: dict[str, str] = {}
    for tag, color in value.items():
        tag_colors[str(tag).lower()] = str(color)
    return tag_colors


def _parse_priority_styles(raw: dict[str, object]) -> dict[str, str]:
    value = raw.get("priority_styles")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Config key `priority_styles` must be a table")
    return {str(priority).lower(): str(style) for priority, style in value.items()}
