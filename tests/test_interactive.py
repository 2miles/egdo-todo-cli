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
from egdo.interactive import (
    _picker_hint,
    prompt_add_form,
    prompt_done_form,
    prompt_note_form,
)
from egdo.markdown_store import Task
from egdo.store import TaskRef


class InteractiveTests(unittest.TestCase):
    def test_note_editor_preserves_multiline_markdown(self) -> None:
        console = Console(file=StringIO(), force_terminal=False, color_system=None)
        edited_path = None

        def edit_note(command, check):
            nonlocal edited_path
            self.assertEqual(command[0], "vim")
            self.assertFalse(check)
            edited_path = Path(command[-1])
            edited_path.write_text(
                "First paragraph.\n\n- one\n- two\n\n## Heading\n",
                encoding="utf-8",
            )
            return type("Result", (), {"returncode": 0})()

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.dict("os.environ", {"VISUAL": "vim", "EDITOR": "nano"}),
            patch("egdo.interactive.subprocess.run", side_effect=edit_note),
        ):
            result = prompt_note_form(console, "Main", date(2026, 9, 8))

        self.assertEqual(
            result, "First paragraph.\n\n- one\n- two\n\n## Heading"
        )
        self.assertIsNotNone(edited_path)
        self.assertFalse(edited_path.exists())

    def test_note_editor_cancels_when_instruction_buffer_is_unchanged(self) -> None:
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.dict("os.environ", {"VISUAL": "vim"}),
            patch(
                "egdo.interactive.subprocess.run",
                return_value=type("Result", (), {"returncode": 0})(),
            ),
        ):
            result = prompt_note_form(console, "Main", date(2026, 9, 8))

        self.assertIsNone(result)

    def test_note_editor_reports_nonzero_exit_and_removes_temporary_file(self) -> None:
        console = Console(file=StringIO(), force_terminal=False, color_system=None)
        edited_path = None

        def fail_editor(command, check):
            nonlocal edited_path
            edited_path = Path(command[-1])
            return type("Result", (), {"returncode": 2})()

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.dict("os.environ", {"VISUAL": "nano"}),
            patch("egdo.interactive.subprocess.run", side_effect=fail_editor),
            self.assertRaisesRegex(RuntimeError, "status 2"),
        ):
            prompt_note_form(console, "Main", date(2026, 9, 8))

        self.assertIsNotNone(edited_path)
        self.assertFalse(edited_path.exists())

    def test_picker_hint_styles_keys_separately_from_actions(self) -> None:
        hint = _picker_hint(("Space", "Select"), ("q/Esc", "Cancel"))

        self.assertEqual(hint.plain, "Space Select  •  q/Esc Cancel")
        styled_parts = [
            (hint.plain[span.start : span.end], str(span.style))
            for span in hint.spans
        ]
        self.assertIn(("Space", "bright_white"), styled_parts)
        self.assertIn((" Select", "dim"), styled_parts)
        self.assertIn(("q/Esc", "bright_white"), styled_parts)
        self.assertIn((" Cancel", "dim"), styled_parts)
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
        config = type("ConfigStub", (), {})()
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
                    "enter",
                    "down",
                    "enter",
                ],
            ),
        ):
            result = prompt_add_form(
                config,
                date(2026, 7, 27),
                console,
                parse_future_date,
                known_tags=["work", "home"],
            )

        self.assertEqual(result.text, "Submit application")
        self.assertEqual(result.tag, "career")
        self.assertEqual(result.priority, "important")
        self.assertEqual(result.scheduled, date(2026, 7, 28))

    def test_add_form_uses_blank_defaults(self) -> None:
        config = type("ConfigStub", (), {})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", side_effect=["Buy milk"]),
            patch("egdo.interactive.read_picker_key", side_effect=["enter", "enter", "enter"]),
        ):
            result = prompt_add_form(config, date(2026, 7, 27), console, parse_future_date)

        self.assertIsNone(result.tag)
        self.assertEqual(result.priority, "normal")
        self.assertEqual(result.scheduled, date(2026, 7, 27))

    def test_add_form_can_cancel_from_task_text_prompt(self) -> None:
        config = type("ConfigStub", (), {})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", return_value="/cancel"),
            patch("egdo.interactive.read_picker_key") as key_mock,
        ):
            result = prompt_add_form(
                config, date(2026, 7, 27), console, parse_future_date
            )

        self.assertIsNone(result)
        key_mock.assert_not_called()

    def test_focused_tag_uses_bright_cyan(self) -> None:
        config = type("ConfigStub", (), {})()
        output = StringIO()
        console = Console(
            file=output,
            force_terminal=True,
            color_system="standard",
            no_color=False,
        )

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", return_value="Task"),
            patch(
                "egdo.interactive.read_picker_key",
                side_effect=["down", "escape"],
            ),
        ):
            result = prompt_add_form(
                config,
                date(2026, 7, 27),
                console,
                parse_future_date,
                known_tags=["work"],
            )

        self.assertIsNone(result)
        self.assertIn("\x1b[1;96mWORK", output.getvalue())

    def test_add_form_can_cancel_from_new_tag_prompt(self) -> None:
        config = type("ConfigStub", (), {})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", side_effect=["Task", "/cancel"]),
            patch("egdo.interactive.read_picker_key", return_value="new"),
        ):
            result = prompt_add_form(
                config, date(2026, 7, 27), console, parse_future_date
            )

        self.assertIsNone(result)

    def test_add_form_can_cancel_from_custom_schedule_prompt(self) -> None:
        config = type("ConfigStub", (), {})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", side_effect=["Task", "/cancel"]),
            patch(
                "egdo.interactive.read_picker_key",
                side_effect=["enter", "enter", *("down" for _ in range(9)), "enter"],
            ),
        ):
            result = prompt_add_form(
                config, date(2026, 7, 27), console, parse_future_date
            )

        self.assertIsNone(result)

    def test_no_tags_choice_clears_selected_tags(self) -> None:
        config = type("ConfigStub", (), {})()
        console = Console(file=StringIO(), force_terminal=False, color_system=None)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch.object(console, "input", side_effect=["Task"]),
            patch(
                "egdo.interactive.read_picker_key",
                side_effect=["down", "toggle", "up", "toggle", "enter", "enter", "enter"],
            ),
        ):
            result = prompt_add_form(
                config,
                date(2026, 7, 27),
                console,
                parse_future_date,
                known_tags=["work"],
            )

        self.assertIsNone(result.tag)


if __name__ == "__main__":
    unittest.main()
