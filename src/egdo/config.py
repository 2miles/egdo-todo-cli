from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "egdo" / "config.toml"


@dataclass(slots=True)
class Config:
    notes_root: Path
    todos_root: str
    tag_colors: dict[str, str]

    @property
    def notes_dir(self) -> Path:
        return self.notes_root / self.todos_root


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `egdo init --notes-root /path/to/notes --todos-root egdo`."
        )

    raw = _parse_toml(path.read_text(encoding="utf-8"))

    try:
        notes_root = Path(raw["notes_root"]).expanduser()
        todos_root = raw["todos_root"]
    except KeyError as exc:
        raise ValueError(f"Missing config key: {exc.args[0]}") from exc

    tag_colors = _parse_tag_colors(raw)

    return Config(notes_root=notes_root, todos_root=todos_root, tag_colors=tag_colors)


def write_config(
    notes_root: Path,
    todos_root: str,
    path: Path = CONFIG_PATH,
    tag_colors: dict[str, str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f'notes_root = "{notes_root.expanduser()}"\n'
        f'todos_root = "{todos_root}"\n'
    )
    if tag_colors:
        content += "\n[tag_colors]\n"
        for tag, color in sorted(tag_colors.items()):
            content += f'{tag} = "{color}"\n'
    path.write_text(content, encoding="utf-8")
    return path


def save_config(config: Config, path: Path = CONFIG_PATH) -> Path:
    return write_config(
        notes_root=config.notes_root,
        todos_root=config.todos_root,
        path=path,
        tag_colors=config.tag_colors,
    )


def _parse_toml(content: str) -> dict[str, object]:
    raw: dict[str, object] = {}
    section: str | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            if section == "tag_colors" and section not in raw:
                raw[section] = {}
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed_value = value.strip().strip('"').strip("'")
        if section == "tag_colors":
            tag_colors = raw.setdefault("tag_colors", {})
            assert isinstance(tag_colors, dict)
            tag_colors[key.strip()] = parsed_value
        else:
            raw[key.strip()] = parsed_value
    return raw


def _parse_tag_colors(raw: dict[str, object]) -> dict[str, str]:
    value = raw.get("tag_colors")
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Config key `tag_colors` must be a table")
    tag_colors: dict[str, str] = {}
    for tag, color in value.items():
        tag_colors[str(tag).lower()] = str(color)
    return tag_colors
