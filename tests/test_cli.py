from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console

from egdo.cli import (
    _build_tag_styles,
    _format_display_date,
    _render_list_header,
    _render_separator,
    _render_task_line,
    _style_wrapped_task_line,
    main,
)


class CliTests(unittest.TestCase):
    def test_format_display_date_uses_short_weekday_month_and_ordinal(self) -> None:
        self.assertEqual(_format_display_date(date(2026, 4, 4)), "Sat, Apr 4th")

    def test_format_display_date_handles_ordinal_exceptions(self) -> None:
        self.assertEqual(_format_display_date(date(2026, 4, 11)), "Sat, Apr 11th")
        self.assertEqual(_format_display_date(date(2026, 4, 12)), "Sun, Apr 12th")
        self.assertEqual(_format_display_date(date(2026, 4, 13)), "Mon, Apr 13th")
        self.assertEqual(_format_display_date(date(2026, 4, 21)), "Tue, Apr 21st")

    def test_render_list_header_plain_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(_render_list_header(date(2026, 4, 4)))

        self.assertEqual(output.getvalue(), "Sat, Apr 4th\n")

    def test_render_separator_uses_requested_width(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(_render_separator(12))

        self.assertEqual(output.getvalue(), "────────────\n")

    def test_render_task_line_plain_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            _render_task_line(3, "[minecraft] Add sorter", date(2026, 4, 4), {"minecraft": "green"})
        )

        self.assertEqual(output.getvalue(), "3. [minecraft] Add sorter (Sat, Apr 4th)\n")

    def test_render_task_line_wraps_with_indented_continuation(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            _render_task_line(
                1,
                "[minecraft] Add dripstone farm overflow protection and sorter",
                date(2026, 4, 4),
                {"minecraft": "green"},
                wrap_width=40,
            )
        )

        self.assertEqual(
            output.getvalue(),
            "1. [minecraft] Add dripstone farm\n"
            "   overflow protection and sorter\n"
            "   (Sat, Apr 4th)\n",
        )

    def test_style_wrapped_task_line_dims_date_when_date_is_only_continuation_content(self) -> None:
        styled = _style_wrapped_task_line(
            "   (Sat, Apr 4th)",
            "1. ",
            " (Sat, Apr 4th)",
            {"minecraft": "green"},
        )

        self.assertEqual(styled.plain, "   (Sat, Apr 4th)")
        self.assertEqual(len(styled.spans), 2)
        self.assertEqual(styled.spans[0].style, "dim")
        self.assertEqual(styled.spans[0].start, 0)
        self.assertEqual(styled.spans[0].end, 3)
        self.assertEqual(styled.spans[1].style, "dim")
        self.assertEqual(styled.spans[1].start, 3)
        self.assertEqual(styled.spans[1].end, len(styled.plain))

    def test_build_tag_styles_assigns_distinct_colors_until_palette_runs_out(self) -> None:
        styles, updated, warnings = _build_tag_styles(
            [
                "[minecraft] Task",
                "[fun] Task",
                "[important] Task",
            ]
        )

        self.assertTrue(updated)
        self.assertEqual(warnings, [])
        self.assertEqual(len(set(styles.values())), 3)

    def test_build_tag_styles_reuses_existing_assignment_for_repeat_tags(self) -> None:
        styles, _, _ = _build_tag_styles(
            [
                "[minecraft] Task",
                "[fun] Task",
                "[minecraft] Another task",
            ]
        )

        self.assertEqual(styles["minecraft"], styles["minecraft"])
        self.assertNotEqual(styles["minecraft"], styles["fun"])

    def test_build_tag_styles_never_uses_header_date_style(self) -> None:
        styles, _, _ = _build_tag_styles(["[minecraft] Task", "[chores] Task", "[home] Task"])
        for style in styles.values():
            self.assertNotEqual(style, "bold cyan")

    def test_build_tag_styles_preserves_existing_assignments(self) -> None:
        styles, updated, warnings = _build_tag_styles(
            ["[minecraft] Task", "[fun] Task"],
            existing_styles={"minecraft": "red"},
        )

        self.assertTrue(updated)
        self.assertEqual(warnings, [])
        self.assertEqual(styles["minecraft"], "red")

    def test_build_tag_styles_reassigns_invalid_config_style(self) -> None:
        styles, updated, warnings = _build_tag_styles(
            ["[minecraft] Task"],
            existing_styles={"minecraft": "not-a-real-style"},
        )

        self.assertTrue(updated)
        self.assertEqual(len(warnings), 1)
        self.assertNotEqual(styles["minecraft"], "not-a-real-style")

    def test_main_defaults_to_list_when_no_command_is_given(self) -> None:
        with (
            patch("egdo.cli.load_config") as load_config_mock,
            patch("egdo.cli.list_tasks", return_value=[]),
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            load_config_mock.return_value = type(
                "ConfigStub",
                (),
                {"notes_dir": Path("/tmp/notes"), "tag_colors": {}},
            )()

            exit_code = main([])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
