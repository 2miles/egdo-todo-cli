"""Behavior tests for loading and saving egdo configuration."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.config import (
    Config,
    initialize_local_marker,
    load_config,
    read_local_project,
    register_initialized_project,
    remove_project,
    save_config,
    use_project,
)


class ConfigTests(unittest.TestCase):
    def test_load_config_ignores_unknown_tables(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                "\n".join(
                    [
                        'active_project = "Main"',
                        "",
                        "[projects]",
                        'Main = "/tmp/notes/egdo"',
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
                'active_project = "Main"\n\n'
                '[projects]\n'
                '"Main" = "/tmp/notes/egdo"\n',
            )

    def test_save_config_preserves_unrelated_content_and_creates_backup(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            original = (
                'active_project = "Main"\n\n'
                '[projects]\nMain = "/old/root"\n\n'
                '[unrelated]\n# Personal settings\nvalue = "keep me"\n'
            )
            path.write_text(original, encoding="utf-8")

            config = Config(projects={"Main": Path("/new/root")})
            save_config(config, path)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                'active_project = "Main"\n\n'
                '[projects]\n'
                '"Main" = "/new/root"\n\n'
                '[unrelated]\n# Personal settings\nvalue = "keep me"\n',
            )
            self.assertEqual(
                path.with_suffix(".toml.bak").read_text(encoding="utf-8"),
                original,
            )

    def test_load_config_rejects_removed_single_root_format(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('root = "/tmp/notes/egdo"\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "at least one project"):
                load_config(path)

    def test_load_named_projects_and_select_case_insensitively(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'active_project = "Minecraft"\n\n'
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

    def test_load_config_accepts_previous_default_project_key(self) -> None:
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

            self.assertEqual(config.active_project, "Minecraft")

    def test_use_project_preserves_display_name(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Minecraft": Path("/tmp/minecraft")}
        )
        config = use_project(config, "minecraft")

        self.assertEqual(config.active_project, "Minecraft")
        self.assertEqual(config.project_name, "Minecraft")
        self.assertEqual(config.root, Path("/tmp/minecraft"))

    def test_remove_project_preserves_files_and_other_projects(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Demo": Path("/tmp/demo")}
        )

        updated = remove_project(config, "demo")

        self.assertEqual(updated.projects, {"Main": Path("/tmp/main")})
        self.assertEqual(updated.active_project, "Main")
        self.assertEqual(config.projects["Demo"], Path("/tmp/demo"))

    def test_remove_active_project_promotes_first_remaining_project(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Minecraft": Path("/tmp/minecraft")},
            active_project="Main",
        )

        updated = remove_project(config, "Main")

        self.assertEqual(updated.active_project, "Minecraft")
        self.assertEqual(updated.project_name, "Minecraft")

    def test_remove_project_rejects_only_configured_project(self) -> None:
        config = Config(projects={"Main": Path("/tmp/main")})

        with self.assertRaisesRegex(ValueError, "only configured project"):
            remove_project(config, "Main")

    def test_initialize_local_marker_creates_archive_without_fake_history(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / "minecraft"

            root, created = initialize_local_marker(directory, "Minecraft")

            self.assertTrue(created)
            self.assertEqual(root, (directory / "egdo").resolve())
            self.assertEqual(
                (directory / ".egdo.toml").read_text(encoding="utf-8"),
                'project = "Minecraft"\n',
            )
            self.assertEqual(list(root.iterdir()), [])

    def test_initialize_local_marker_is_idempotent_for_same_project(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            initialize_local_marker(directory, "Minecraft")

            root, created = initialize_local_marker(directory, "minecraft")

            self.assertFalse(created)
            self.assertEqual(root, (directory / "egdo").resolve())

    def test_initialize_local_marker_rejects_different_project(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            initialize_local_marker(directory, "Minecraft")

            with self.assertRaisesRegex(ValueError, "already identifies"):
                initialize_local_marker(directory, "Main")

    def test_local_marker_resolves_archive_relative_to_its_current_location(self) -> None:
        with TemporaryDirectory() as tmp:
            original = Path(tmp) / "old" / "minecraft"
            initialize_local_marker(original, "Minecraft")
            moved = Path(tmp) / "new" / "minecraft"
            moved.parent.mkdir(parents=True)
            original.rename(moved)

            local_project = read_local_project(moved / ".egdo.toml")

            self.assertEqual(local_project.name, "Minecraft")
            self.assertEqual(local_project.root, (moved / "egdo").resolve())

    def test_register_initialized_project_makes_first_project_active(self) -> None:
        config, changed = register_initialized_project(
            None, "Minecraft", Path("/tmp/minecraft/egdo")
        )

        self.assertTrue(changed)
        self.assertEqual(config.active_project, "Minecraft")
        self.assertEqual(config.root, Path("/tmp/minecraft/egdo").resolve())

    def test_register_initialized_project_relinks_when_old_location_is_gone(self) -> None:
        config = Config(
            projects={"Minecraft": Path("/tmp/old/egdo")},
            active_project="Minecraft",
        )

        updated, changed = register_initialized_project(
            config, "minecraft", Path("/tmp/new/egdo")
        )

        self.assertTrue(changed)
        self.assertEqual(
            updated.projects["Minecraft"], Path("/tmp/new/egdo").resolve()
        )


if __name__ == "__main__":
    unittest.main()
