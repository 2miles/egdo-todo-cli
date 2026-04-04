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
                        'notes_root = "/tmp/notes"',
                        'todos_root = "egdo"',
                        "",
                        "[tag_colors]",
                        'minecraft = "green"',
                        'fun = "blue"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config.tag_colors, {"minecraft": "green", "fun": "blue"})

    def test_save_config_writes_tag_colors_table(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            config = Config(notes_root=Path("/tmp/notes"), todos_root="egdo", tag_colors={"fun": "blue"})

            save_config(config, path)

            content = path.read_text(encoding="utf-8")
            self.assertIn("[tag_colors]", content)
            self.assertIn('fun = "blue"', content)

    def test_write_config_defaults_tag_colors_to_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"

            write_config(notes_root=Path("/tmp/notes"), todos_root="egdo", path=path)

            config = load_config(path)
            self.assertEqual(config.tag_colors, {})


if __name__ == "__main__":
    unittest.main()
