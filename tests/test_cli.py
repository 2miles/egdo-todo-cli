from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console

from egdo.cli import main
from egdo.dates import format_display_date, parse_future_date
from egdo.handlers import build_tag_styles, normalize_tag_name
from egdo.render import (
    render_list_header,
    render_separator,
    render_tag_style_picker,
    render_task_line,
    style_wrapped_task_line,
)


class CliTests(unittest.TestCase):
    def test_format_display_date_uses_short_weekday_month_and_ordinal(self) -> None:
        self.assertEqual(format_display_date(date(2026, 4, 4)), "Sat, Apr 4th")

    def test_format_display_date_handles_ordinal_exceptions(self) -> None:
        self.assertEqual(format_display_date(date(2026, 4, 11)), "Sat, Apr 11th")
        self.assertEqual(format_display_date(date(2026, 4, 12)), "Sun, Apr 12th")
        self.assertEqual(format_display_date(date(2026, 4, 13)), "Mon, Apr 13th")
        self.assertEqual(format_display_date(date(2026, 4, 21)), "Tue, Apr 21st")

    def test_render_list_header_plain_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_list_header(date(2026, 4, 4)))

        self.assertEqual(output.getvalue(), "Sat, Apr 4th\n")

    def test_render_separator_uses_requested_width(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_separator(12))

        self.assertEqual(output.getvalue(), "────────────\n")

    def test_render_task_line_plain_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(3, "{MINECRAFT} Add sorter", date(2026, 4, 4), {"minecraft": "green"})
        )

        self.assertEqual(output.getvalue(), "3. {MINECRAFT} Add sorter (Sat, Apr 4th)\n")

    def test_render_task_line_wraps_with_indented_continuation(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                "{MINECRAFT} Add dripstone farm overflow protection and sorter",
                date(2026, 4, 4),
                {"minecraft": "green"},
                wrap_width=40,
            )
        )

        self.assertEqual(
            output.getvalue(),
            "1. {MINECRAFT} Add dripstone farm\n"
            "   overflow protection and sorter\n"
            "   (Sat, Apr 4th)\n",
        )

    def test_style_wrapped_task_line_dims_date_when_date_is_only_continuation_content(self) -> None:
        styled = style_wrapped_task_line(
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
        styles, updated, warnings = build_tag_styles(
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
        styles, _, _ = build_tag_styles(
            [
                "[minecraft] Task",
                "[fun] Task",
                "[minecraft] Another task",
            ]
        )

        self.assertEqual(styles["minecraft"], styles["minecraft"])
        self.assertNotEqual(styles["minecraft"], styles["fun"])

    def test_build_tag_styles_never_uses_header_date_style(self) -> None:
        styles, _, _ = build_tag_styles(["{MINECRAFT} Task", "{CHORES} Task", "{HOME} Task"])
        for style in styles.values():
            self.assertNotEqual(style, "bold cyan")

    def test_build_tag_styles_preserves_existing_assignments(self) -> None:
        styles, updated, warnings = build_tag_styles(
            ["[minecraft] Task", "[fun] Task"],
            existing_styles={"minecraft": "red"},
        )

        self.assertTrue(updated)
        self.assertEqual(warnings, [])
        self.assertEqual(styles["minecraft"], "red")

    def test_build_tag_styles_reassigns_invalid_config_style(self) -> None:
        styles, updated, warnings = build_tag_styles(
            ["[minecraft] Task"],
            existing_styles={"minecraft": "not-a-real-style"},
        )

        self.assertTrue(updated)
        self.assertEqual(len(warnings), 1)
        self.assertNotEqual(styles["minecraft"], "not-a-real-style")

    def test_normalize_tag_name_strips_brackets_and_lowercases(self) -> None:
        self.assertEqual(normalize_tag_name(" {Chores} "), "chores")

    def test_parse_future_date_accepts_tomorrow(self) -> None:
        self.assertEqual(parse_future_date("tomorrow", date(2026, 4, 6)), date(2026, 4, 7))

    def test_parse_future_date_accepts_relative_days(self) -> None:
        self.assertEqual(parse_future_date("+3", date(2026, 4, 6)), date(2026, 4, 9))

    def test_parse_future_date_accepts_weekday_name_as_next_occurrence(self) -> None:
        self.assertEqual(parse_future_date("sunday", date(2026, 4, 6)), date(2026, 4, 12))
        self.assertEqual(parse_future_date("mon", date(2026, 4, 6)), date(2026, 4, 13))

    def test_parse_future_date_accepts_iso_date(self) -> None:
        self.assertEqual(parse_future_date("2026-04-10", date(2026, 4, 6)), date(2026, 4, 10))

    def test_parse_future_date_rejects_non_future_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "future date"):
            parse_future_date("2026-04-06", date(2026, 4, 6))

    def test_render_tag_style_picker_includes_current_marker(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_tag_style_picker("chores", 0, "medium_orchid3"))

        rendered = output.getvalue()
        self.assertIn("Choose a color for {CHORES}", rendered)
        self.assertIn("> {CHORES} medium_orchid3 current", rendered)

    def test_main_color_command_saves_style_override(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            exit_code = main(["color", "Chores", "--style", "green_yellow"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(config.tag_colors["chores"], "green_yellow")
        save_config_mock.assert_called_once_with(config)
        self.assertIn("Saved tag color: {CHORES} -> green_yellow", output.getvalue())

    def test_main_color_command_rejects_invalid_style(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            exit_code = main(["color", "chores", "--style", "not-a-real-style"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid style: not-a-real-style", stderr.getvalue())

    def test_main_edit_command_prints_updated_task(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        edited_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.edit_task", return_value=edited_task) as edit_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["edit", "2", "Buy oat milk"])

        self.assertEqual(exit_code, 0)
        edit_task_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, 2, "Buy oat milk")
        self.assertIn("Edited [2026-04-05] Buy oat milk", output.getvalue())

    def test_main_add_command_merges_repeated_tags_into_task_text(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": date(2026, 4, 6), "text": "{HOUSE} {CHORES} Do the dishes"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "--tag", "house", "--tag", "chores", "Do the dishes"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "{HOUSE} {CHORES} Do the dishes", done=False
        )
        self.assertIn("Added [2026-04-06] {HOUSE} {CHORES} Do the dishes", output.getvalue())

    def test_main_add_command_dedupes_inline_and_flag_tags(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": date(2026, 4, 6), "text": "{HOUSE} {CHORES} Do the dishes"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "--tag", "chores", "[house] Do the dishes"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "{HOUSE} {CHORES} Do the dishes", done=False
        )

    def test_main_move_command_prints_destination(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        moved_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.move_task", return_value=moved_task) as move_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["move", "2", "tomorrow"])

        self.assertEqual(exit_code, 0)
        move_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, 2, date(2026, 4, 7)
        )
        self.assertIn("Moved [2026-04-05] Buy oat milk -> 2026-04-07", output.getvalue())

    def test_main_future_command_renders_grouped_future_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        first_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "{CHORES} Buy milk"})()
        second_task = type("TaskStub", (), {"created": date(2026, 4, 4), "text": "Ship box"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch(
                "egdo.cli.list_future_tasks",
                return_value=[
                    (date(2026, 4, 7), first_task),
                    (date(2026, 4, 10), second_task),
                ],
            ) as list_future_tasks_mock,
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["future"])

        self.assertEqual(exit_code, 0)
        list_future_tasks_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, tag=None)
        save_config_mock.assert_called_once_with(config)
        rendered = output.getvalue()
        self.assertIn("Tue, Apr 7th", rendered)
        self.assertIn("Fri, Apr 10th", rendered)
        self.assertIn("1. {CHORES} Buy milk (Sun, Apr 5th)", rendered)
        self.assertIn("2. Ship box (Sat, Apr 4th)", rendered)

    def test_main_future_done_command_completes_by_future_index(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        done_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.complete_future_task", return_value=done_task) as complete_future_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["future", "done", "1"])

        self.assertEqual(exit_code, 0)
        complete_future_task_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, 1)
        self.assertIn("Completed [2026-04-06 <= 2026-04-05] Buy oat milk", output.getvalue())

    def test_main_future_move_command_uses_shared_date_parser(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        moved_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.move_future_task", return_value=moved_task) as move_future_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["future", "move", "2", "tomorrow"])

        self.assertEqual(exit_code, 0)
        move_future_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, 2, date(2026, 4, 7)
        )
        self.assertIn("Moved future [2026-04-05] Buy oat milk -> 2026-04-07", output.getvalue())

    def test_main_future_unmove_command_prints_destination(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        unmoved_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.unmove_task", return_value=unmoved_task) as unmove_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["future", "unmove", "1"])

        self.assertEqual(exit_code, 0)
        unmove_task_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, 1)
        self.assertIn("Unmoved [2026-04-05] Buy oat milk -> 2026-04-06", output.getvalue())

    def test_main_defaults_to_list_when_no_command_is_given(self) -> None:
        with (
            patch("egdo.cli.load_config") as load_config_mock,
            patch("egdo.cli.list_tasks", return_value=[]),
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            load_config_mock.return_value = type(
                "ConfigStub",
                (),
                {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
            )()

            exit_code = main([])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
