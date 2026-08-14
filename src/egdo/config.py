"""Read and write egdo's small TOML-like user configuration file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil


CONFIG_PATH = Path.home() / ".config" / "egdo" / "config.toml"


@dataclass(slots=True)
class Config:
    root: Path


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load the storage root from disk."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Run `egdo config --root ~/Notes/egdo`."
        )

    raw = _parse_toml(path.read_text(encoding="utf-8"))

    try:
        root = Path(raw["root"]).expanduser()
    except KeyError as exc:
        raise ValueError(f"Missing config key: {exc.args[0]}") from exc

    return Config(root=root)


def write_config(
    root: Path,
    path: Path = CONFIG_PATH,
) -> Path:
    """Set the root while preserving existing config content and making a backup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    root_line = f'root = "{root.expanduser()}"'
    if path.exists():
        original = path.read_text(encoding="utf-8")
        shutil.copy2(path, path.with_suffix(f"{path.suffix}.bak"))
        lines = original.splitlines()
        section_seen = False
        replaced = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_seen = True
            if not section_seen and re.match(r"^\s*root\s*=", line):
                lines[index] = root_line
                replaced = True
                break
        if not replaced:
            lines.insert(0, root_line)
        content = "\n".join(lines) + "\n"
    else:
        content = f"{root_line}\n"
    path.write_text(content, encoding="utf-8")
    return path


def save_config(config: Config, path: Path = CONFIG_PATH) -> Path:
    return write_config(
        root=config.root,
        path=path,
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
            if section not in raw:
                raw[section] = {}
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed_value = value.strip().strip('"').strip("'")
        if section is not None:
            values = raw.setdefault(section, {})
            assert isinstance(values, dict)
            values[key.strip()] = parsed_value
        else:
            raw[key.strip()] = parsed_value
    return raw
