"""Behavior tests for loading and saving egdo configuration."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.config import Config, load_config, save_config, write_config


class ConfigTests(unittest.TestCase):
    def test_load_config_reads_tag_colors_table(self) -> None:
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
                        "[tag_levels]",
                        "projects = 1",
                        "egdo = 2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config.tag_colors, {"minecraft": "green", "fun": "blue"})
            self.assertEqual(config.priority_styles, {"p1": "bold red", "p4": "grey37"})
            self.assertEqual(config.tag_levels, {"projects": 1, "egdo": 2})

    def test_save_config_writes_tag_colors_table(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            config = Config(
                root=Path("/tmp/notes/egdo"),
                tag_colors={"fun": "blue"},
                priority_styles={"p2": "orange3"},
                tag_levels={"egdo": 2, "projects": 1},
            )

            save_config(config, path)

            content = path.read_text(encoding="utf-8")
            self.assertIn("[tag_colors]", content)
            self.assertIn('fun = "blue"', content)
            self.assertIn("[priority_styles]", content)
            self.assertIn('p2 = "orange3"', content)
            self.assertIn("[tag_levels]", content)
            self.assertIn("projects = 1", content)
            self.assertIn("egdo = 2", content)

    def test_write_config_defaults_tag_colors_to_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"

            write_config(root=Path("/tmp/notes/egdo"), path=path)

            config = load_config(path)
            self.assertEqual(config.tag_colors, {})
            self.assertEqual(config.priority_styles, {})
            self.assertEqual(config.tag_levels, {})

    def test_load_config_rejects_invalid_tag_level(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'root = "/tmp/notes/egdo"\n\n[tag_levels]\nprojects = 0\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "positive integer"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
