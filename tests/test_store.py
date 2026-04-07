from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.store import (
    add_note,
    add_task,
    complete_future_task,
    complete_task,
    create_task,
    delete_future_task,
    delete_task,
    edit_future_task,
    edit_task,
    ensure_state,
    file_path,
    list_future_tasks,
    list_tasks,
    move_future_task,
    move_task,
    tag_future_task,
    tag_task,
    unmove_task,
)


class StoreTests(unittest.TestCase):
    def test_add_task_creates_month_file_and_day_section(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)

            add_task(notes_dir, target_date, "Buy milk")

            path = file_path(notes_dir, target_date)
            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Apr-05 Sun", content)
            self.assertIn("### Tasks", content)
            self.assertIn("- [ ] Buy milk (04-05)", content)

    def test_create_task_can_start_completed(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)

            task = create_task(notes_dir, target_date, "Call dad", done=True)

            self.assertTrue(task.done)
            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [x] Call dad (04-05)", content)

    def test_month_file_path_uses_year_and_month(self) -> None:
        notes_dir = Path("/tmp/notes")
        self.assertEqual(file_path(notes_dir, date(2026, 4, 5)), notes_dir / "2026" / "2026_04_apr.md")

    def test_list_rolls_forward_unfinished_tasks_across_days(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 4), "[chores] Buy milk")

            tasks = list_tasks(notes_dir, date(2026, 4, 5))

            self.assertEqual([task.text for task in tasks], ["[chores] Buy milk"])
            state = ensure_state(file_path(notes_dir, date(2026, 4, 5)))
            content = file_path(notes_dir, date(2026, 4, 5)).read_text(encoding="utf-8")
            self.assertIn("## Apr-05 Sun", content)
            self.assertIn("- [ ] [chores] Buy milk (04-04)", content)
            self.assertNotIn(date(2026, 4, 4), state.days)

    def test_rollover_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 4), "Buy milk")

            first = list_tasks(notes_dir, date(2026, 4, 5))
            second = list_tasks(notes_dir, date(2026, 4, 5))

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)

    def test_render_includes_blank_day_headers_between_populated_days(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 4), "Buy milk")
            complete_task(notes_dir, date(2026, 4, 4), 1)
            add_task(notes_dir, date(2026, 4, 6), "Ship box")

            content = file_path(notes_dir, date(2026, 4, 6)).read_text(encoding="utf-8")

            self.assertIn("## Apr-04 Sat", content)
            self.assertIn("## Apr-05 Sun", content)
            self.assertIn("## Apr-06 Mon", content)

    def test_blank_day_header_has_no_tasks_section(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 4), "Buy milk")
            complete_task(notes_dir, date(2026, 4, 4), 1)
            add_task(notes_dir, date(2026, 4, 6), "Ship box")

            content = file_path(notes_dir, date(2026, 4, 6)).read_text(encoding="utf-8")

            self.assertIn("## Apr-05 Sun\n\n## Apr-06 Mon", content)

    def test_list_filters_by_leading_tag(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "[personal][chores][home] Do the dishes")
            add_task(notes_dir, target_date, "[work] Fix parser bug")
            add_task(notes_dir, target_date, "Plain task")

            tasks = list_tasks(notes_dir, target_date, tag="chores")

            self.assertEqual([task.text for task in tasks], ["[personal][chores][home] Do the dishes"])

    def test_done_marks_task_complete_in_month_file(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "[chores] Buy milk")

            task = complete_task(notes_dir, target_date, 1)

            self.assertTrue(task.done)
            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [x] [chores] Buy milk (04-05)", content)

    def test_delete_removes_task_from_current_day(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "Buy milk")
            add_task(notes_dir, target_date, "Ship box")

            task = delete_task(notes_dir, target_date, 1)

            self.assertEqual(task.text, "Buy milk")
            tasks = list_tasks(notes_dir, target_date)
            self.assertEqual([remaining.text for remaining in tasks], ["Ship box"])

    def test_edit_updates_active_task_text_and_preserves_created_date(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "Buy milk")

            task = edit_task(notes_dir, target_date, 1, "[chores] Buy oat milk")

            self.assertEqual(task.text, "[chores] Buy oat milk")
            self.assertEqual(task.created, target_date)
            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [ ] [chores] Buy oat milk (04-05)", content)

    def test_edit_indexes_only_active_tasks(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "Done task")
            add_task(notes_dir, target_date, "Active task")
            complete_task(notes_dir, target_date, 1)

            task = edit_task(notes_dir, target_date, 1, "Renamed active task")

            self.assertEqual(task.text, "Renamed active task")
            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [x] Done task (04-05)", content)
            self.assertIn("- [ ] Renamed active task (04-05)", content)

    def test_tag_adds_one_or_more_tags_to_task(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "Do the dishes")

            task = tag_task(notes_dir, target_date, 1, ["chores", "home"])

            self.assertEqual(task.text, "{CHORES} {HOME} Do the dishes")
            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [ ] {CHORES} {HOME} Do the dishes (04-05)", content)

    def test_move_moves_active_task_to_future_day_and_preserves_created_date(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            source_date = date(2026, 4, 6)
            destination_date = date(2026, 4, 10)
            add_task(notes_dir, source_date, "Keep archive anchor")
            complete_task(notes_dir, source_date, 1)
            add_task(notes_dir, source_date, "Buy milk")

            task = move_task(notes_dir, source_date, 1, destination_date)

            self.assertEqual(task.text, "Buy milk")
            self.assertEqual(task.created, source_date)
            self.assertEqual(list_tasks(notes_dir, source_date), [])
            moved_tasks = list_tasks(notes_dir, destination_date)
            self.assertEqual([moved.text for moved in moved_tasks], ["Buy milk"])
            content = file_path(notes_dir, destination_date).read_text(encoding="utf-8")
            self.assertIn("## Apr-07 Tue", content)
            self.assertIn("## Apr-10 Fri", content)
            self.assertIn("- [ ] Buy milk (04-06)", content)

    def test_move_creates_new_month_file_when_destination_crosses_month_boundary(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            source_date = date(2026, 4, 30)
            destination_date = date(2026, 5, 2)
            add_task(notes_dir, source_date, "Ship box")

            move_task(notes_dir, source_date, 1, destination_date)

            self.assertFalse(file_path(notes_dir, source_date).exists())
            destination_path = file_path(notes_dir, destination_date)
            self.assertTrue(destination_path.exists())
            content = destination_path.read_text(encoding="utf-8")
            self.assertIn("## May-02 Sat", content)
            self.assertIn("- [ ] Ship box (04-30)", content)

    def test_list_future_tasks_returns_incomplete_tasks_after_today(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            path = file_path(notes_dir, date(2026, 4, 6))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "## Apr-06 Mon",
                        "",
                        "### Tasks",
                        "",
                        "- [ ] Today task (04-06)",
                        "",
                        "## Apr-08 Wed",
                        "",
                        "### Tasks",
                        "",
                        "- [ ] [chores] Future one (04-08)",
                        "",
                        "## Apr-10 Fri",
                        "",
                        "### Tasks",
                        "",
                        "- [x] Future two (04-10)",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            future_tasks = list_future_tasks(notes_dir, date(2026, 4, 6))

            self.assertEqual(
                [(scheduled, task.text) for scheduled, task in future_tasks],
                [
                    (date(2026, 4, 8), "[chores] Future one"),
                ],
            )

    def test_list_future_tasks_filters_by_tag(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            path = file_path(notes_dir, date(2026, 4, 8))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "## Apr-08 Wed",
                        "",
                        "### Tasks",
                        "",
                        "- [ ] [chores] Future one (04-08)",
                        "",
                        "## Apr-09 Thu",
                        "",
                        "### Tasks",
                        "",
                        "- [ ] [work] Future two (04-09)",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            future_tasks = list_future_tasks(notes_dir, date(2026, 4, 6), tag="chores")

            self.assertEqual(
                [(scheduled, task.text) for scheduled, task in future_tasks],
                [(date(2026, 4, 8), "[chores] Future one")],
            )

    def test_unmove_moves_future_task_back_to_today_by_future_index(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 6)
            add_task(notes_dir, today, "Current task")
            move_task(notes_dir, today, 1, date(2026, 4, 10))

            task = unmove_task(notes_dir, today, 1)

            self.assertEqual(task.text, "Current task")
            self.assertEqual(task.created, today)
            today_tasks = list_tasks(notes_dir, today)
            self.assertEqual([current.text for current in today_tasks], ["Current task"])
            self.assertEqual(list_future_tasks(notes_dir, today), [])

    def test_unmove_can_pull_task_back_from_later_month(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 30)
            add_task(notes_dir, today, "Ship box")
            move_task(notes_dir, today, 1, date(2026, 5, 2))

            task = unmove_task(notes_dir, today, 1)

            self.assertEqual(task.text, "Ship box")
            self.assertTrue(file_path(notes_dir, today).exists())
            self.assertFalse(file_path(notes_dir, date(2026, 5, 2)).exists())
            content = file_path(notes_dir, today).read_text(encoding="utf-8")
            self.assertIn("- [ ] Ship box (04-30)", content)

    def test_complete_future_task_marks_scheduled_task_done(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 6)
            add_task(notes_dir, today, "Buy milk")
            move_task(notes_dir, today, 1, date(2026, 4, 10))

            task = complete_future_task(notes_dir, today, 1)

            self.assertTrue(task.done)
            self.assertEqual(list_future_tasks(notes_dir, today), [])

    def test_delete_future_task_removes_scheduled_task(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 6)
            add_task(notes_dir, today, "Buy milk")
            move_task(notes_dir, today, 1, date(2026, 4, 10))

            task = delete_future_task(notes_dir, today, 1)

            self.assertEqual(task.text, "Buy milk")
            self.assertEqual(list_future_tasks(notes_dir, today), [])

    def test_edit_future_task_updates_text_in_place(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 6)
            add_task(notes_dir, today, "Buy milk")
            move_task(notes_dir, today, 1, date(2026, 4, 10))

            task = edit_future_task(notes_dir, today, 1, "{CHORES} Buy oat milk")

            self.assertEqual(task.text, "{CHORES} Buy oat milk")
            future_tasks = list_future_tasks(notes_dir, today)
            self.assertEqual(future_tasks[0][1].text, "{CHORES} Buy oat milk")

    def test_move_future_task_retimes_future_task(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 6)
            add_task(notes_dir, today, "Buy milk")
            move_task(notes_dir, today, 1, date(2026, 4, 10))

            task = move_future_task(notes_dir, today, 1, date(2026, 4, 12))

            self.assertEqual(task.text, "Buy milk")
            future_tasks = list_future_tasks(notes_dir, today)
            self.assertEqual(
                [(scheduled, item.text) for scheduled, item in future_tasks],
                [(date(2026, 4, 12), "Buy milk")],
            )

    def test_tag_future_task_adds_tags_in_place(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            today = date(2026, 4, 6)
            add_task(notes_dir, today, "Buy milk")
            move_task(notes_dir, today, 1, date(2026, 4, 10))

            task = tag_future_task(notes_dir, today, 1, ["chores", "home"])

            self.assertEqual(task.text, "{CHORES} {HOME} Buy milk")
            future_tasks = list_future_tasks(notes_dir, today)
            self.assertEqual(future_tasks[0][1].text, "{CHORES} {HOME} Buy milk")

    def test_add_note_creates_notes_section_and_appends_paragraphs(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)

            add_note(notes_dir, target_date, "First note.")
            add_note(notes_dir, target_date, "Second note.")

            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("### Notes", content)
            self.assertIn("First note.\n\nSecond note.", content)

    def test_add_note_does_not_accumulate_extra_blank_line_after_notes_heading_on_rewrite(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)

            add_task(notes_dir, target_date, "Buy milk")
            add_note(notes_dir, target_date, "First note.")
            list_tasks(notes_dir, target_date)

            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [ ] Buy milk (04-05)\n\n### Notes\n\nFirst note.", content)
            self.assertNotIn("### Notes\n\n\nFirst note.", content)

    def test_manual_month_file_is_parseable(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            path = file_path(notes_dir, target_date)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "## Apr-05 Sun",
                        "",
                        "### Tasks",
                        "",
                        "- [ ] [chores] Buy milk (04-04)",
                        "- [x] Ship box (04-05)",
                        "",
                        "### Notes",
                        "",
                        "Need to remember cat meds.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            tasks = list_tasks(notes_dir, target_date)
            state = ensure_state(path)

            self.assertEqual([task.text for task in tasks], ["[chores] Buy milk"])
            self.assertEqual(state.days[target_date].notes, ["Need to remember cat meds."])

    def test_rollover_across_month_boundary_keeps_original_created_date(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 30), "Buy milk")

            tasks = list_tasks(notes_dir, date(2026, 5, 1))

            self.assertEqual([task.text for task in tasks], ["Buy milk"])
            content = file_path(notes_dir, date(2026, 5, 1)).read_text(encoding="utf-8")
            self.assertIn("- [ ] Buy milk (04-30)", content)


if __name__ == "__main__":
    unittest.main()
