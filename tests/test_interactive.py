"""Tests for guided terminal forms."""

from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console

from egdo.dates import parse_future_date
from egdo.interactive import prompt_add_form, prompt_done_form
from egdo.markdown_store import Task
from egdo.store import TaskRef


class InteractiveTests(unittest.TestCase):
    def test_done_form_accepts_nested_and_multiple_ids(self) -> None:
        today = date(2026, 7, 27)
        refs = [
            TaskRef(today, Task("Parent", today, False), "1", today),
            TaskRef(today, Task("Child", today, False, depth=1), "1a", today),
            TaskRef(date(2026, 7, 28), Task("Future", today, False), "2", today),
        ]
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch(
                "egdo.interactive.read_picker_key",
                side_effect=["down", "toggle", "down", "toggle", "enter"],
            ),
        ):
            selected = prompt_done_form(refs, today, console)

        self.assertEqual(selected, ["1a", "2"])
        self.assertIn("Child", output.getvalue())
        self.assertIn("2026-07-28", output.getvalue())

    def test_done_form_requires_a_selection(self) -> None:
        today = date(2026, 7, 27)
        refs = [TaskRef(today, Task("Task", today, False), "1", today)]
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("egdo.interactive.read_picker_key", side_effect=["enter", "toggle", "enter"]),
        ):
            selected = prompt_done_form(refs, today, console)

        self.assertEqual(selected, ["1"])

    def test_done_form_parent_selection_covers_descendants(self) -> None:
        today = date(2026, 7, 27)
        refs = [
            TaskRef(today, Task("Parent", today, False), "1", today),
            TaskRef(today, Task("Child", today, False, depth=1), "1a", today),
            TaskRef(today, Task("Grandchild", today, False, depth=2), "1a.a", today),
        ]
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("egdo.interactive.read_picker_key", side_effect=["toggle", "down", "toggle", "enter"]),
        ):
            selected = prompt_done_form(refs, today, console)

        self.assertEqual(selected, ["1"])

    def test_add_form_selects_existing_and_new_tags(self) -> None:
        config = type("ConfigStub", (), {"tag_colors": {"work": "blue", "home": "green"}})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(
                console,
                "input",
                side_effect=["Submit application", "career"],
            ),
            patch(
                "egdo.interactive.read_picker_key",
                side_effect=[
                    "down",
                    "down",
                    "toggle",
                    "new",
                    "enter",
                    "down",
                    "down",
                    "down",
                    "enter",
                    "down",
                    "enter",
                ],
            ),
        ):
            result = prompt_add_form(config, date(2026, 7, 27), console, parse_future_date)

        self.assertEqual(result.text, "Submit application")
        self.assertEqual(result.tags, ["career", "work"])
        self.assertEqual(result.priority, "high")
        self.assertEqual(result.scheduled, date(2026, 7, 28))

    def test_add_form_uses_blank_defaults(self) -> None:
        config = type("ConfigStub", (), {"tag_colors": {}})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", side_effect=["Buy milk"]),
            patch("egdo.interactive.read_picker_key", side_effect=["enter", "enter", "enter"]),
        ):
            result = prompt_add_form(config, date(2026, 7, 27), console, parse_future_date)

        self.assertEqual(result.tags, [])
        self.assertIsNone(result.priority)
        self.assertEqual(result.scheduled, date(2026, 7, 27))

    def test_no_tags_choice_clears_selected_tags(self) -> None:
        config = type("ConfigStub", (), {"tag_colors": {"work": "blue"}})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", side_effect=["Task"]),
            patch(
                "egdo.interactive.read_picker_key",
                side_effect=["down", "toggle", "up", "toggle", "enter", "enter", "enter"],
            ),
        ):
            result = prompt_add_form(config, date(2026, 7, 27), console, parse_future_date)

        self.assertEqual(result.tags, [])


if __name__ == "__main__":
    unittest.main()
