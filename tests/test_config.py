"""Behavior tests for loading and saving egdo configuration."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.config import (
    Config,
    add_project,
    create_config,
    load_config,
    save_config,
    set_project_root,
    use_project,
)


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
            self.assertEqual(config.project_name, "Main")
            self.assertEqual(config.projects, {"Main": Path("/tmp/notes/egdo")})

    def test_save_config_writes_named_main_project(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            config = Config(projects={"Main": Path("/tmp/notes/egdo")})

            save_config(config, path)

            content = path.read_text(encoding="utf-8")
            self.assertEqual(
                content,
                'default_project = "Main"\n\n'
                '[projects]\n'
                '"Main" = "/tmp/notes/egdo"\n',
            )

    def test_save_config_migrates_legacy_root_and_preserves_unrelated_content(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            original = (
                '# Personal settings\nroot = "/old/root"\n\n'
                '[unrelated]\nvalue = "keep me"\nroot = "section value"\n'
            )
            path.write_text(original, encoding="utf-8")

            config = load_config(path)
            config = set_project_root(config, "Main", Path("/new/root"))
            save_config(config, path)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                'default_project = "Main"\n\n'
                '[projects]\n'
                '"Main" = "/new/root"\n\n'
                '# Personal settings\n\n'
                '[unrelated]\nvalue = "keep me"\nroot = "section value"\n',
            )
            self.assertEqual(
                path.with_suffix(".toml.bak").read_text(encoding="utf-8"),
                original,
            )

    def test_load_named_projects_and_select_case_insensitively(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'default_project = "Minecraft"\n\n'
                '[projects]\n'
                '"Main" = "/tmp/main"\n'
                '"Minecraft" = "/tmp/minecraft"\n',
                encoding="utf-8",
            )

            config = load_config(path)
            selected = config.select("MAIN")

            self.assertEqual(config.project_name, "Minecraft")
            self.assertEqual(config.root, Path("/tmp/minecraft"))
            self.assertEqual(selected.project_name, "Main")
            self.assertEqual(selected.root, Path("/tmp/main"))

    def test_add_and_use_project_preserve_display_name(self) -> None:
        config = Config(projects={"Main": Path("/tmp/main")})

        config = add_project(config, "Minecraft", Path("/tmp/minecraft"))
        config = use_project(config, "minecraft")

        self.assertEqual(config.default_project, "Minecraft")
        self.assertEqual(config.project_name, "Minecraft")
        self.assertEqual(config.root, Path("/tmp/minecraft"))

    def test_add_project_rejects_case_insensitive_duplicate(self) -> None:
        config = Config(projects={"Main": Path("/tmp/main")})
        config = add_project(config, "Minecraft", Path("/tmp/minecraft"))

        with self.assertRaisesRegex(ValueError, "already exists"):
            add_project(config, "MINECRAFT", Path("/tmp/other"))

    def test_create_config_uses_first_project_as_default(self) -> None:
        config = create_config("Minecraft", Path("/tmp/minecraft"))

        self.assertEqual(config.default_project, "Minecraft")
        self.assertEqual(config.project_name, "Minecraft")
        self.assertEqual(config.root, Path("/tmp/minecraft"))

    def test_set_project_root_updates_only_named_project(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Minecraft": Path("/tmp/minecraft")}
        )

        updated = set_project_root(config, "minecraft", Path("/tmp/new-minecraft"))

        self.assertEqual(updated.projects["Main"], Path("/tmp/main"))
        self.assertEqual(updated.projects["Minecraft"], Path("/tmp/new-minecraft"))


if __name__ == "__main__":
    unittest.main()
