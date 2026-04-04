from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "egdo" / "config.toml"


@dataclass(slots=True)
class Config:
    notes_root: Path
    todos_root: str

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

    return Config(notes_root=notes_root, todos_root=todos_root)


def write_config(notes_root: Path, todos_root: str, path: Path = CONFIG_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f'notes_root = "{notes_root.expanduser()}"\n'
        f'todos_root = "{todos_root}"\n'
    )
    path.write_text(content, encoding="utf-8")
    return path


def _parse_toml(content: str) -> dict[str, str]:
    raw: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        raw[key.strip()] = value.strip().strip('"').strip("'")
    return raw
