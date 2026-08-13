"""Behavior tests for CLI parsing, dispatch, styling, and rendered output."""

from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console

from egdo.cli import build_parser, main
from egdo.dates import format_display_date, parse_future_date
from egdo.interactive import AddFormResult
from egdo.store import TaskRef
from egdo.render import (
    render_list_header,
    render_section_header,
    render_separator,
    render_task_line,
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

        self.assertEqual(output.getvalue(), "Saturday, April 4\n")
        self.assertEqual(render_list_header(date(2026, 4, 4)).spans[0].style, "bold")

    def test_render_separator_uses_requested_width(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_separator(12))

        self.assertEqual(output.getvalue(), "────────────\n")

    def test_render_section_header_uses_requested_width(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_section_header("Today", 20))

        self.assertEqual(output.getvalue(), "── Today ───────────\n")

        header = render_section_header("Today", 20)
        label_span = next(
            (span for span in header.spans if header.plain[span.start : span.end] == " Today "),
            None,
        )
        self.assertIsNone(label_span)

    def test_render_task_line_plain_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                3,
                "{MINECRAFT} Add sorter",
                date(2026, 4, 4),
                wrap_width=60,
            )
        )

        self.assertEqual(output.getvalue(), " 3.       MINECRAFT   Add sorter                      Apr  4\n")

    def test_render_nested_task_uses_hierarchical_id_and_indentation(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                "6a",
                "Add tests",
                date(2026, 7, 27),
                wrap_width=60,
                depth=1,
            )
        )

        self.assertEqual(
            output.getvalue(),
            " 6a.                  · Add tests                     Jul 27\n",
        )

    def test_important_nested_task_uses_priority_marker_instead_of_subtask_dot(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                "6a",
                "! Important child",
                date(2026, 7, 27),
                wrap_width=60,
                depth=1,
            )
        )

        self.assertIn("6a.   ●              · Important child", output.getvalue())

    def test_render_task_line_displays_priority_before_tags(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                "! {WORK} Submit application",
                date(2026, 4, 4),
                wrap_width=60,
            )
        )

        self.assertEqual(
            output.getvalue(),
            " 1.    ●  WORK        Submit application              Apr  4\n",
        )

    def test_normal_task_leaves_priority_column_empty(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_task_line(2, "Task", date(2026, 4, 4), wrap_width=50))

        self.assertIn("2.                   Task", output.getvalue())

    def test_render_task_line_wraps_with_indented_continuation(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                "{MINECRAFT} Add dripstone farm overflow protection and sorter",
                date(2026, 4, 4),
                wrap_width=50,
            )
        )

        self.assertEqual(
            [line.rstrip() for line in output.getvalue().splitlines()],
            [
                " 1.       MINECRAFT   Add dripstone farm    Apr  4",
                "                      overflow protection",
                "                      and sorter",
            ],
        )

    def test_render_task_line_capitalizes_first_task_letter_for_display(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                '{PROJECTS} "finish the parser"',
                date(2026, 8, 1),
                wrap_width=60,
                show_created=False,
            )
        )

        self.assertIn('PROJECTS    "Finish the parser"', output.getvalue())

    def test_render_task_line_truncates_only_the_displayed_tag(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                "{EXTRAORDINARYLONGTAG} Keep the stored tag intact",
                date(2026, 8, 1),
                wrap_width=72,
            )
        )

        rendered = output.getvalue()
        self.assertIn("EXTRAORDI…", rendered)
        self.assertNotIn("EXTRAORDINARYLONGTAG", rendered)

    def test_task_dates_align_regardless_of_visible_tags_or_priority(self) -> None:
        rows = []
        for index, text in enumerate(
            [
                "No tag",
                "{WORK} One tag",
                "{PROJECTS} Long tag",
                "! {PERSONAL} Important task",
            ],
            start=1,
        ):
            output = StringIO()
            console = Console(file=output, force_terminal=False, color_system=None)
            console.print(render_task_line(index, text, date(2026, 8, 1), wrap_width=72))
            rows.append(output.getvalue().rstrip("\n"))

        self.assertEqual({row.index("Aug  1") for row in rows}, {66})

        nested_output = StringIO()
        nested_console = Console(
            file=nested_output, force_terminal=False, color_system=None
        )
        nested_console.print(
            render_task_line(
                "4a",
                "{WORK} Nested task",
                date(2026, 8, 1),
                wrap_width=72,
                depth=1,
            )
        )
        self.assertEqual(nested_output.getvalue().index("Aug  1"), 66)

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

    def test_main_edit_command_prints_updated_task(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
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
        edit_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, 2, "Buy oat milk"
        )
        self.assertIn("✓ Edited “Buy oat milk”", output.getvalue())

    def test_main_add_command_sets_one_tag(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": date(2026, 4, 6), "text": "{CHORES} Do the dishes"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "--tag", "chores", "Do the dishes"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "{CHORES} Do the dishes", done=False
        )
        self.assertIn("✓ Added “{CHORES} Do the dishes”", output.getvalue())

    def test_successful_task_mutation_clears_and_relists_in_a_terminal(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": mocked_today, "text": "Buy milk", "depth": 0}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task),
            patch(
                "egdo.cli.list_task_refs",
                return_value=[TaskRef(mocked_today, created_task)],
            ) as list_task_refs_mock,
            patch(
                "egdo.cli.console",
                Console(file=output, force_terminal=True, color_system=None, width=80),
            ),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "Buy milk"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today)
        rendered = output.getvalue()
        self.assertIn("\x1b[2J", rendered)
        self.assertLess(rendered.index("✓ Added “Buy milk”"), rendered.index("Today"))
        self.assertIn("1.                   Buy milk", rendered)

    def test_main_add_without_text_uses_interactive_form(self) -> None:
        config = type(
            "ConfigStub", (), {"root": Path("/tmp/notes/egdo")}
        )()
        output = StringIO()
        mocked_today = date(2026, 7, 27)
        scheduled = date(2026, 7, 28)
        form = AddFormResult("Submit application", "work", "important", scheduled)
        created_task = type(
            "TaskStub", (), {"created": mocked_today, "text": "! {WORK} Submit application"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.prompt_add_form", return_value=form) as prompt_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add"])

        self.assertEqual(exit_code, 0)
        prompt_mock.assert_called_once()
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"),
            mocked_today,
            "! {WORK} Submit application",
            done=False,
            scheduled_date=scheduled,
        )
        self.assertIn("→ 2026-07-28", output.getvalue())

    def test_main_add_command_adds_named_priority_before_tags(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": mocked_today, "text": "! {WORK} Submit application"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "-p", "important", "-t", "work", "Submit application"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"),
            mocked_today,
            "! {WORK} Submit application",
            done=False,
        )

    def test_main_add_command_flag_tag_replaces_inline_tag(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": date(2026, 4, 6), "text": "{CHORES} Do the dishes"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "--tag", "chores", "{HOUSE} Do the dishes"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "{CHORES} Do the dishes", done=False
        )

    def test_main_add_command_can_create_done_task_with_tag(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": date(2026, 4, 6), "text": "{ERRANDS} Call the DMV"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "--done", "-t", "errands", "Call the DMV"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "{ERRANDS} Call the DMV", done=True
        )
        self.assertIn("✓ Added done “{ERRANDS} Call the DMV”", output.getvalue())

    def test_main_move_command_prints_destination(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        moved_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()
        second_moved_task = type("TaskStub", (), {"created": date(2026, 4, 6), "text": "Ship box"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.move_tasks", return_value=[moved_task, second_moved_task]) as move_tasks_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["move", "2", "3", "tomorrow"])

        self.assertEqual(exit_code, 0)
        move_tasks_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, [2, 3], date(2026, 4, 7)
        )
        self.assertIn("✓ Moved “Buy oat milk” → 2026-04-07", output.getvalue())
        self.assertIn("✓ Moved “Ship box” → 2026-04-07", output.getvalue())

    def test_main_delete_command_deletes_multiple_indexes(self) -> None:
        config = type("ConfigStub", (), {"root": Path("/tmp/notes/egdo")})()
        mocked_today = date(2026, 4, 6)
        tasks = [
            type("TaskStub", (), {"text": "One"})(),
            type("TaskStub", (), {"text": "Six"})(),
        ]

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.delete_tasks", return_value=tasks) as delete_tasks_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["delete", "1", "6"])

        self.assertEqual(exit_code, 0)
        delete_tasks_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, [1, 6])

    def test_main_tag_remove_removes_tags_from_multiple_indexes(self) -> None:
        config = type("ConfigStub", (), {"root": Path("/tmp/notes/egdo")})()
        mocked_today = date(2026, 4, 6)
        tasks = [
            type("TaskStub", (), {"text": "One"})(),
            type("TaskStub", (), {"text": "Two"})(),
        ]

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.untag_tasks", return_value=tasks) as untag_tasks_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["tag", "3", "6", "7", "--remove"])

        self.assertEqual(exit_code, 0)
        untag_tasks_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, [3, 6, 7]
        )

    def test_main_list_future_flag_renders_only_grouped_future_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        first_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "{CHORES} Buy milk"})()
        second_task = type("TaskStub", (), {"created": date(2026, 4, 4), "text": "Ship box"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch(
                "egdo.cli.list_task_refs",
                return_value=[
                    TaskRef(mocked_today, object()),
                    TaskRef(mocked_today, object()),
                    TaskRef(date(2026, 4, 7), first_task),
                    TaskRef(date(2026, 4, 10), second_task),
                ],
            ) as list_task_refs_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["list", "--future"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today)
        rendered = output.getvalue()
        self.assertNotIn("Upcoming", rendered)
        self.assertIn("── Tomorrow, April 7 ─", rendered)
        self.assertIn("── Friday, April 10 ─", rendered)
        self.assertNotIn("Today\n", rendered)
        self.assertNotIn("Carried forward\n", rendered)
        self.assertIn("3.       CHORES", rendered)
        self.assertIn("Buy milk", rendered)
        self.assertNotIn("Apr 5", rendered)
        self.assertIn("4.                   Ship box", rendered)
        self.assertNotIn("Apr 4", rendered)

    def test_main_finished_command_renders_completed_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        finished_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "{CHORES} Buy milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.list_finished_tasks", return_value=[finished_task]) as list_finished_tasks_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["finished"])

        self.assertEqual(exit_code, 0)
        list_finished_tasks_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, tag=None)
        rendered = output.getvalue()
        self.assertIn("Monday, April 6", rendered)
        self.assertIn("1.       CHORES", rendered)
        self.assertIn("Buy milk", rendered)
        self.assertIn("Apr  5", rendered)

    def test_main_list_groups_today_and_carried_forward_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        todays_task = type("TaskStub", (), {"created": date(2026, 4, 6), "text": "{CHORES} Wash the car"})()
        carried_task = type(
            "TaskStub", (), {"created": date(2026, 4, 5), "text": "{MINECRAFT} Add sorter"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch(
                "egdo.cli.list_task_refs",
                return_value=[
                    TaskRef(mocked_today, todays_task),
                    TaskRef(mocked_today, carried_task),
                ],
            ) as list_task_refs_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["list"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today)
        rendered = output.getvalue()
        self.assertIn("Today", rendered)
        self.assertIn("Carried forward", rendered)
        self.assertNotIn("Old", rendered)
        self.assertIn("1.       CHORES", rendered)
        self.assertIn("Wash the car", rendered)
        self.assertIn("2.       MINECRAFT", rendered)
        self.assertIn("Add sorter", rendered)
        self.assertIn("Apr  5", rendered)

    def test_main_list_includes_grouped_future_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        todays_task = type("TaskStub", (), {"created": date(2026, 4, 6), "text": "Wash the car"})()
        tomorrow_task = type("TaskStub", (), {"created": date(2026, 4, 6), "text": "{CHORES} Buy milk"})()
        later_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Ship box"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch(
                "egdo.cli.list_task_refs",
                return_value=[
                    TaskRef(mocked_today, todays_task),
                    TaskRef(date(2026, 4, 7), tomorrow_task),
                    TaskRef(date(2026, 4, 10), later_task),
                ],
            ) as list_task_refs_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["list"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today)
        rendered = output.getvalue()
        self.assertIn("Today", rendered)
        self.assertIn("1.                   Wash the car", rendered)
        self.assertNotIn("Upcoming", rendered)
        self.assertIn("── Tomorrow, April 7 ─", rendered)
        self.assertIn("2.       CHORES", rendered)
        self.assertIn("Buy milk", rendered)
        self.assertIn("── Friday, April 10 ─", rendered)
        self.assertIn("3.                   Ship box", rendered)

    def test_future_is_not_a_standalone_command(self) -> None:
        parser = build_parser()

        with (
            patch("sys.stderr", new_callable=StringIO),
            self.assertRaises(SystemExit),
        ):
            parser.parse_args(["future"])

    def test_main_done_command_completes_multiple_indexes(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        first_task = type("TaskStub", (), {"text": "Buy oat milk"})()
        second_task = type("TaskStub", (), {"text": "Ship box"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.complete_tasks", return_value=[first_task, second_task]) as complete_tasks_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["done", "1", "3"])

        self.assertEqual(exit_code, 0)
        complete_tasks_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, [1, 3])
        self.assertIn("✓ Completed “Buy oat milk”", output.getvalue())
        self.assertIn("✓ Completed “Ship box”", output.getvalue())

    def test_main_done_without_indexes_uses_interactive_form(self) -> None:
        config = type(
            "ConfigStub", (), {"root": Path("/tmp/notes/egdo")}
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        task = type("TaskStub", (), {"text": "Buy milk"})()
        ref = TaskRef(mocked_today, task, "1", mocked_today)

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.list_task_refs", return_value=[ref]),
            patch("egdo.cli.prompt_done_form", return_value=["1"]) as prompt_mock,
            patch("egdo.cli.complete_tasks", return_value=[task]) as complete_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["done"])

        self.assertEqual(exit_code, 0)
        prompt_mock.assert_called_once()
        complete_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, [1])

    def test_main_done_sends_combined_indexes_through_one_store_operation(self) -> None:
        config = type("ConfigStub", (), {"root": Path("/tmp/notes/egdo")})()
        mocked_today = date(2026, 4, 6)
        active_task = type("TaskStub", (), {"text": "Active"})()
        future_one = type("TaskStub", (), {"text": "Future one"})()
        future_two = type("TaskStub", (), {"text": "Future two"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch(
                "egdo.cli.complete_tasks", return_value=[active_task, future_one, future_two]
            ) as complete_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["done", "1", "3", "4"])

        self.assertEqual(exit_code, 0)
        complete_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, [1, 3, 4])

    def test_main_unmove_command_prints_destination(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo")},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        unmoved_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "Buy oat milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.unmove_tasks", return_value=[unmoved_task]) as unmove_tasks_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["unmove", "1"])

        self.assertEqual(exit_code, 0)
        unmove_tasks_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, [1])
        self.assertIn("✓ Unmoved “Buy oat milk” → 2026-04-06", output.getvalue())

    def test_main_defaults_to_list_when_no_command_is_given(self) -> None:
        with (
            patch("egdo.cli.load_config") as load_config_mock,
            patch("egdo.cli.list_task_refs", return_value=[]),
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            load_config_mock.return_value = type(
                "ConfigStub",
                (),
                {"root": Path("/tmp/notes/egdo")},
            )()

            exit_code = main([])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
