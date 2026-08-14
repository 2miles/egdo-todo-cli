"""Behavior tests for loading and saving egdo configuration."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.config import Config, load_config, save_config, write_config


class ConfigTests(unittest.TestCase):
    def test_load_config_ignores_unknown_tables(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                "\n".join(
                    [
                        'root = "/tmp/notes/egdo"',
                        "",
                        "[tag_colors]",
                        'minecraft = "green"',
                        'fun = "blue"',
                        "",
                        "[priority_styles]",
                        'p1 = "bold red"',
                        'p4 = "grey37"',
                        "",
                        "[unrelated]",
                        'value = "ignored"',
                        "egdo = 2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config.root, Path("/tmp/notes/egdo"))

    def test_save_config_writes_only_root(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            config = Config(root=Path("/tmp/notes/egdo"))

            save_config(config, path)

            content = path.read_text(encoding="utf-8")
            self.assertEqual(content, 'root = "/tmp/notes/egdo"\n')

    def test_write_config_round_trips_root(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"

            write_config(root=Path("/tmp/notes/egdo"), path=path)

            config = load_config(path)
            self.assertEqual(config.root, Path("/tmp/notes/egdo"))

    def test_write_config_preserves_existing_content_and_creates_backup(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            original = (
                '# Personal settings\nroot = "/old/root"\n\n'
                '[unrelated]\nvalue = "keep me"\n'
            )
            path.write_text(original, encoding="utf-8")

            write_config(root=Path("/new/root"), path=path)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                '# Personal settings\nroot = "/new/root"\n\n'
                '[unrelated]\nvalue = "keep me"\n',
            )
            self.assertEqual(
                path.with_suffix(".toml.bak").read_text(encoding="utf-8"),
                original,
            )


if __name__ == "__main__":
    unittest.main()
