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
from egdo.handlers import build_tag_styles, normalize_tag_name
from egdo.interactive import AddFormResult
from egdo.store import TaskRef
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

        self.assertEqual(output.getvalue(), "Saturday, April 4\n")

    def test_render_separator_uses_requested_width(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(render_separator(12))

        self.assertEqual(output.getvalue(), "────────────\n")

    def test_render_task_line_plain_text(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                3,
                "{MINECRAFT} Add sorter",
                date(2026, 4, 4),
                {"minecraft": "green"},
                wrap_width=60,
            )
        )

        self.assertEqual(output.getvalue(), " 3.    ·  {MINECRAFT} Add sorter                       Apr 4\n")

    def test_render_nested_task_uses_hierarchical_id_and_indentation(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                "6a",
                "Add tests",
                date(2026, 7, 27),
                {},
                wrap_width=60,
                depth=1,
            )
        )

        self.assertEqual(
            output.getvalue(),
            " 6a.   ·    Add tests                                 Jul 27\n",
        )

    def test_render_task_line_displays_priority_before_colored_tags(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                "!P1! {WORK} Submit application",
                date(2026, 4, 4),
                {"work": "blue"},
                wrap_width=60,
            )
        )

        self.assertEqual(
            output.getvalue(),
            " 1.    ●  {WORK} Submit application                    Apr 4\n",
        )

    def test_render_task_line_uses_less_emphasis_for_lower_priorities(self) -> None:
        expected_markers = {1: "●", 2: "◆", 3: "•", 4: "·"}
        for priority, marker in expected_markers.items():
            with self.subTest(priority=priority):
                output = StringIO()
                console = Console(file=output, force_terminal=False, color_system=None)
                console.print(
                    render_task_line(
                        priority,
                        f"!P{priority}! Task",
                        date(2026, 4, 4),
                        {},
                        wrap_width=50,
                    )
                )
                self.assertIn(f"{priority}.    {marker}  Task", output.getvalue())

    def test_priority_marker_uses_default_style(self) -> None:
        styled = style_wrapped_task_line(
            "1. ◆  Task  Apr 4",
            "1. ◆  ",
            "  Apr 4",
            {},
            priority=2,
        )

        marker_span = next(
            span for span in styled.spans if styled.plain[span.start : span.end] == "◆"
        )
        self.assertEqual(marker_span.style, "yellow")

    def test_priority_meter_uses_configured_styles(self) -> None:
        styled = style_wrapped_task_line(
            "1. ◆  Task  Apr 4",
            "1. ◆  ",
            "  Apr 4",
            {},
            priority=2,
            priority_styles={"p2": "bold cyan", "p4": "grey37"},
        )

        marker_span = next(
            span for span in styled.spans if styled.plain[span.start : span.end] == "◆"
        )
        self.assertEqual(marker_span.style, "bold cyan")

    def test_render_task_line_wraps_with_indented_continuation(self) -> None:
        output = StringIO()
        console = Console(file=output, force_terminal=False, color_system=None)
        console.print(
            render_task_line(
                1,
                "{MINECRAFT} Add dripstone farm overflow protection and sorter",
                date(2026, 4, 4),
                {"minecraft": "green"},
                wrap_width=50,
            )
        )

        self.assertEqual(
            output.getvalue(),
            " 1.    ·  {MINECRAFT} Add dripstone farm     Apr 4\n"
            "          overflow protection and sorter\n",
        )

    def test_style_wrapped_task_line_dims_date_when_date_is_only_continuation_content(self) -> None:
        styled = style_wrapped_task_line(
            "   (Sat, Apr 4th)",
            "1. ",
            " (Sat, Apr 4th)",
            {"minecraft": "green"},
        )

        self.assertEqual(styled.plain, "   (Sat, Apr 4th)")
        self.assertEqual(len(styled.spans), 1)
        self.assertEqual(styled.spans[0].style, "dim")
        self.assertEqual(styled.spans[0].start, 3)
        self.assertEqual(styled.spans[0].end, len(styled.plain))

    def test_task_indexes_use_equal_width_right_aligned_white_column(self) -> None:
        single_digit = style_wrapped_task_line(
            " 9. ·  Task  Apr 4",
            " 9. ·  ",
            "  Apr 4",
            {},
            priority=4,
        )
        double_digit = style_wrapped_task_line(
            "10. ·  Task  Apr 4",
            "10. ·  ",
            "  Apr 4",
            {},
            priority=4,
        )

        self.assertEqual(single_digit.plain.index("Task"), double_digit.plain.index("Task"))
        self.assertEqual(single_digit.spans[0].style, "white")
        self.assertEqual(double_digit.spans[0].style, "white")

    def test_style_wrapped_task_line_preserves_spaces_between_tags(self) -> None:
        styled = style_wrapped_task_line(
            "1. {CHORES} {CAR} Wash the car (Mon, Apr 6th)",
            "1. ",
            " (Mon, Apr 6th)",
            {"chores": "yellow", "car": "blue"},
        )

        self.assertEqual(styled.plain, "1. {CHORES} {CAR} Wash the car (Mon, Apr 6th)")

    def test_build_tag_styles_assigns_distinct_colors_until_palette_runs_out(self) -> None:
        styles, updated, warnings = build_tag_styles(
            [
                "{MINECRAFT} Task",
                "{FUN} Task",
                "{IMPORTANT} Task",
            ]
        )

        self.assertTrue(updated)
        self.assertEqual(warnings, [])
        self.assertEqual(len(set(styles.values())), 3)

    def test_build_tag_styles_reuses_existing_assignment_for_repeat_tags(self) -> None:
        styles, _, _ = build_tag_styles(
            [
                "{MINECRAFT} Task",
                "{FUN} Task",
                "{MINECRAFT} Another task",
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
            ["{MINECRAFT} Task", "{FUN} Task"],
            existing_styles={"minecraft": "red"},
        )

        self.assertTrue(updated)
        self.assertEqual(warnings, [])
        self.assertEqual(styles["minecraft"], "red")

    def test_build_tag_styles_reassigns_invalid_config_style(self) -> None:
        styles, updated, warnings = build_tag_styles(
            ["{MINECRAFT} Task"],
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
            exit_code = main(["color", "--tag", "Chores", "--style", "green_yellow"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(config.tag_colors["chores"], "green_yellow")
        save_config_mock.assert_called_once_with(config)
        self.assertIn("Saved tag color: {CHORES} -> green_yellow", output.getvalue())

    def test_main_color_command_copies_style_from_another_tag(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {"work": "bold orange1"}},
        )()
        output = StringIO()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            exit_code = main(
                ["color", "--tag", "Career", "consulting", "--copy-from", "{WORK}"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(config.tag_colors["career"], "bold orange1")
        self.assertEqual(config.tag_colors["consulting"], "bold orange1")
        save_config_mock.assert_called_once_with(config)

    def test_main_color_command_rejects_unknown_copy_source(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            exit_code = main(["color", "--tag", "career", "--copy-from", "work"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Tag `work` has no saved color to copy", stderr.getvalue())

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
            exit_code = main(["color", "--tag", "chores", "--style", "not-a-real-style"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid style: not-a-real-style", stderr.getvalue())

    def test_main_priority_color_command_saves_style_override(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}, "priority_styles": {}},
        )()
        output = StringIO()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            exit_code = main(["color", "--priority", "high", "--style", "bold cyan"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(config.priority_styles["p2"], "bold cyan")
        save_config_mock.assert_called_once_with(config)
        self.assertIn("Saved priority style: P2 -> bold cyan", output.getvalue())

    def test_color_help_includes_rich_color_reference(self) -> None:
        color_parser = next(
            action.choices["color"]
            for action in build_parser()._actions
            if getattr(action, "choices", None) and "color" in action.choices
        )

        self.assertIn(
            "https://rich.readthedocs.io/en/stable/appendix/colors.html",
            color_parser.format_help(),
        )

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
        edit_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, 2, "Buy oat milk", {}
        )
        self.assertIn("✓ Edited “Buy oat milk”", output.getvalue())

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
            Path("/tmp/notes/egdo"), mocked_today, "!P4! {HOUSE} {CHORES} Do the dishes", done=False
        )
        self.assertIn("✓ Added “{HOUSE} {CHORES} Do the dishes”", output.getvalue())

    def test_successful_task_mutation_clears_and_relists_in_a_terminal(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}, "priority_styles": {}},
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
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, {})
        rendered = output.getvalue()
        self.assertIn("\x1b[2J", rendered)
        self.assertLess(rendered.index("✓ Added “Buy milk”"), rendered.index("Today"))
        self.assertIn("1.    ·  Buy milk", rendered)

    def test_main_add_without_text_uses_interactive_form(self) -> None:
        config = type(
            "ConfigStub", (), {"root": Path("/tmp/notes/egdo"), "tag_colors": {"work": "blue"}}
        )()
        output = StringIO()
        mocked_today = date(2026, 7, 27)
        scheduled = date(2026, 7, 28)
        form = AddFormResult("Submit application", ["work"], "high", scheduled)
        created_task = type(
            "TaskStub", (), {"created": mocked_today, "text": "!P2! {WORK} Submit application"}
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
            "!P2! {WORK} Submit application",
            done=False,
            scheduled_date=scheduled,
        )
        self.assertIn("→ 2026-07-28", output.getvalue())

    def test_main_add_command_adds_named_priority_before_tags(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": mocked_today, "text": "!P2! {WORK} Submit application"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=StringIO(), force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "-p", "high", "-t", "work", "Submit application"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"),
            mocked_today,
            "!P2! {WORK} Submit application",
            done=False,
        )

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
            exit_code = main(["add", "--tag", "chores", "{HOUSE} Do the dishes"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "!P4! {HOUSE} {CHORES} Do the dishes", done=False
        )

    def test_main_add_command_can_create_done_task_with_tags(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        created_task = type(
            "TaskStub", (), {"created": date(2026, 4, 6), "text": "{CAR} {ERRANDS} Call the DMV"}
        )()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.create_task", return_value=created_task) as create_task_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["add", "--done", "-t", "car", "-t", "errands", "Call the DMV"])

        self.assertEqual(exit_code, 0)
        create_task_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, "!P4! {CAR} {ERRANDS} Call the DMV", done=True
        )
        self.assertIn("✓ Added done “{CAR} {ERRANDS} Call the DMV”", output.getvalue())

    def test_main_move_command_prints_destination(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
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
        config = type("ConfigStub", (), {"root": Path("/tmp/notes/egdo"), "tag_colors": {}})()
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
        config = type("ConfigStub", (), {"root": Path("/tmp/notes/egdo"), "tag_colors": {}})()
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
            exit_code = main(["tag", "3", "6", "7", "--remove", "work"])

        self.assertEqual(exit_code, 0)
        untag_tasks_mock.assert_called_once_with(
            Path("/tmp/notes/egdo"), mocked_today, [3, 6, 7], ["work"], {}
        )

    def test_main_list_future_flag_renders_only_grouped_future_tasks(self) -> None:
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
                "egdo.cli.list_task_refs",
                return_value=[
                    TaskRef(mocked_today, object()),
                    TaskRef(mocked_today, object()),
                    TaskRef(date(2026, 4, 7), first_task),
                    TaskRef(date(2026, 4, 10), second_task),
                ],
            ) as list_task_refs_mock,
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["list", "--future"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, {})
        save_config_mock.assert_called_once_with(config)
        rendered = output.getvalue()
        self.assertIn("Upcoming", rendered)
        self.assertIn("Tomorrow (Tue, Apr 7th)", rendered)
        self.assertIn("Fri, Apr 10th", rendered)
        self.assertNotIn("Today\n", rendered)
        self.assertNotIn("Carried forward\n", rendered)
        self.assertIn("3.    ·  {CHORES} Buy milk", rendered)
        self.assertNotIn("Apr 5", rendered)
        self.assertIn("4.    ·  Ship box", rendered)
        self.assertNotIn("Apr 4", rendered)

    def test_main_finished_command_renders_completed_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
        )()
        output = StringIO()
        mocked_today = date(2026, 4, 6)
        finished_task = type("TaskStub", (), {"created": date(2026, 4, 5), "text": "{CHORES} Buy milk"})()

        with (
            patch("egdo.cli.load_config", return_value=config),
            patch("egdo.cli.date") as date_mock,
            patch("egdo.cli.list_finished_tasks", return_value=[finished_task]) as list_finished_tasks_mock,
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["finished"])

        self.assertEqual(exit_code, 0)
        list_finished_tasks_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, tag=None)
        save_config_mock.assert_called_once_with(config)
        rendered = output.getvalue()
        self.assertIn("Monday, April 6", rendered)
        self.assertIn("1.    ·  {CHORES} Buy milk", rendered)
        self.assertIn("Apr 5", rendered)

    def test_main_list_groups_today_and_carried_forward_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
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
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["list"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, {})
        save_config_mock.assert_called_once_with(config)
        rendered = output.getvalue()
        self.assertIn("Today", rendered)
        self.assertIn("Carried forward", rendered)
        self.assertNotIn("Old", rendered)
        self.assertIn("1.    ·  {CHORES} Wash the car", rendered)
        self.assertIn("2.    ·  {MINECRAFT} Add sorter", rendered)
        self.assertIn("Apr 5", rendered)

    def test_main_list_includes_grouped_future_tasks(self) -> None:
        config = type(
            "ConfigStub",
            (),
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
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
            patch("egdo.cli.save_config") as save_config_mock,
            patch("egdo.cli.console", Console(file=output, force_terminal=False, color_system=None)),
        ):
            date_mock.today.return_value = mocked_today
            exit_code = main(["list"])

        self.assertEqual(exit_code, 0)
        list_task_refs_mock.assert_called_once_with(Path("/tmp/notes/egdo"), mocked_today, {})
        save_config_mock.assert_called_once_with(config)
        rendered = output.getvalue()
        self.assertIn("Today", rendered)
        self.assertIn("1.    ·  Wash the car", rendered)
        self.assertIn("── Upcoming ─", rendered)
        self.assertIn("Tomorrow (Tue, Apr 7th)", rendered)
        self.assertIn("2.    ·  {CHORES} Buy milk", rendered)
        self.assertIn("Fri, Apr 10th", rendered)
        self.assertIn("3.    ·  Ship box", rendered)

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
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
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
            "ConfigStub", (), {"root": Path("/tmp/notes/egdo"), "tag_colors": {}}
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
        config = type("ConfigStub", (), {"root": Path("/tmp/notes/egdo"), "tag_colors": {}})()
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
            {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
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
                {"root": Path("/tmp/notes/egdo"), "tag_colors": {}},
            )()

            exit_code = main([])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
