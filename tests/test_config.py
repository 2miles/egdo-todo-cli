"""Behavior tests for loading and saving egdo configuration."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.config import (
    Config,
    find_local_project,
    initialize_local_marker,
    load_config,
    register_initialized_project,
    remove_project,
    save_config,
    select_project_for_directory,
    use_project,
)


class ConfigTests(unittest.TestCase):
    def test_load_config_ignores_unknown_tables(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                "\n".join(
                    [
                        'default_project = "Main"',
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
                'default_project = "Main"\n\n'
                '[projects]\n'
                '"Main" = "/tmp/notes/egdo"\n',
            )

    def test_save_config_preserves_unrelated_content_and_creates_backup(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            original = (
                'default_project = "Main"\n\n'
                '[projects]\nMain = "/old/root"\n\n'
                '[unrelated]\n# Personal settings\nvalue = "keep me"\n'
            )
            path.write_text(original, encoding="utf-8")

            config = Config(projects={"Main": Path("/new/root")})
            save_config(config, path)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                'default_project = "Main"\n\n'
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

    def test_use_project_preserves_display_name(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Minecraft": Path("/tmp/minecraft")}
        )
        config = use_project(config, "minecraft")

        self.assertEqual(config.default_project, "Minecraft")
        self.assertEqual(config.project_name, "Minecraft")
        self.assertEqual(config.root, Path("/tmp/minecraft"))

    def test_remove_project_preserves_files_and_other_projects(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Demo": Path("/tmp/demo")}
        )

        updated = remove_project(config, "demo")

        self.assertEqual(updated.projects, {"Main": Path("/tmp/main")})
        self.assertEqual(updated.default_project, "Main")
        self.assertEqual(config.projects["Demo"], Path("/tmp/demo"))

    def test_remove_default_project_promotes_first_remaining_project(self) -> None:
        config = Config(
            projects={"Main": Path("/tmp/main"), "Minecraft": Path("/tmp/minecraft")},
            default_project="Main",
        )

        updated = remove_project(config, "Main")

        self.assertEqual(updated.default_project, "Minecraft")
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

    def test_find_local_project_uses_nearest_parent_marker(self) -> None:
        with TemporaryDirectory() as tmp:
            notes = Path(tmp) / "Notes"
            minecraft = notes / "topics" / "gaming" / "minecraft"
            child = minecraft / "server" / "plugins"
            child.mkdir(parents=True)
            initialize_local_marker(notes, "Main")
            initialize_local_marker(minecraft, "Minecraft")

            self.assertEqual(find_local_project(child).name, "Minecraft")
            self.assertEqual(find_local_project(notes / "personal").name, "Main")

    def test_local_marker_resolves_archive_relative_to_its_current_location(self) -> None:
        with TemporaryDirectory() as tmp:
            original = Path(tmp) / "old" / "minecraft"
            initialize_local_marker(original, "Minecraft")
            moved = Path(tmp) / "new" / "minecraft"
            moved.parent.mkdir(parents=True)
            original.rename(moved)

            local_project = find_local_project(moved / "server")

            self.assertEqual(local_project.name, "Minecraft")
            self.assertEqual(local_project.root, (moved / "egdo").resolve())

    def test_directory_selection_relinks_a_moved_project(self) -> None:
        with TemporaryDirectory() as tmp:
            original = Path(tmp) / "old" / "minecraft"
            initialize_local_marker(original, "Minecraft")
            config = Config(
                projects={"Minecraft": original / "egdo"},
                default_project="Minecraft",
            )
            moved = Path(tmp) / "new" / "minecraft"
            moved.parent.mkdir(parents=True)
            original.rename(moved)

            selected, changed = select_project_for_directory(config, None, moved)

            self.assertTrue(changed)
            self.assertEqual(selected.root, (moved / "egdo").resolve())

    def test_directory_selection_rejects_two_live_markers_for_one_project(self) -> None:
        with TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            initialize_local_marker(first, "Minecraft")
            initialize_local_marker(second, "Minecraft")
            config = Config(
                projects={"Minecraft": first / "egdo"},
                default_project="Minecraft",
            )

            with self.assertRaisesRegex(ValueError, "also active"):
                select_project_for_directory(config, None, second)

    def test_directory_selection_prefers_explicit_then_marker_then_default(self) -> None:
        with TemporaryDirectory() as tmp:
            notes = Path(tmp) / "Notes"
            minecraft = notes / "minecraft"
            initialize_local_marker(notes, "Main")
            initialize_local_marker(minecraft, "Minecraft")
            config = Config(
                projects={
                    "Main": notes / "egdo",
                    "Minecraft": minecraft / "egdo",
                }
            )

            explicit, explicit_changed = select_project_for_directory(
                config, "Main", minecraft
            )
            detected, detected_changed = select_project_for_directory(
                config, None, minecraft
            )
            fallback, fallback_changed = select_project_for_directory(
                config, None, Path(tmp)
            )

            self.assertEqual(explicit.project_name, "Main")
            self.assertEqual(detected.project_name, "Minecraft")
            self.assertEqual(fallback.project_name, "Main")
            self.assertFalse(explicit_changed)
            self.assertFalse(detected_changed)
            self.assertFalse(fallback_changed)

    def test_explicit_selection_bypasses_an_unregistered_local_marker(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / ".egdo.toml").write_text(
                'project = "Unknown"\n', encoding="utf-8"
            )
            config = Config(projects={"Main": Path("/tmp/main/egdo")})

            selected, changed = select_project_for_directory(config, "Main", directory)

            self.assertEqual(selected.project_name, "Main")
            self.assertFalse(changed)

    def test_register_initialized_project_makes_first_project_default(self) -> None:
        config, changed = register_initialized_project(
            None, "Minecraft", Path("/tmp/minecraft/egdo")
        )

        self.assertTrue(changed)
        self.assertEqual(config.default_project, "Minecraft")
        self.assertEqual(config.root, Path("/tmp/minecraft/egdo").resolve())

    def test_register_initialized_project_relinks_when_old_location_is_gone(self) -> None:
        config = Config(
            projects={"Minecraft": Path("/tmp/old/egdo")},
            default_project="Minecraft",
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
