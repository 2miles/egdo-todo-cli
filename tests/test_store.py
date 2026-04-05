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
    complete_task,
    create_task,
    delete_task,
    ensure_state,
    file_path,
    list_tasks,
    tag_task,
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
            self.assertIn("# 2026_04_apr", content)
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

    def test_tag_adds_one_or_more_tags_to_task(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)
            add_task(notes_dir, target_date, "Do the dishes")

            task = tag_task(notes_dir, target_date, 1, ["chores", "home"])

            self.assertEqual(task.text, "[chores][home] Do the dishes")
            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("- [ ] [chores][home] Do the dishes (04-05)", content)

    def test_add_note_creates_notes_section_and_appends_paragraphs(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 5)

            add_note(notes_dir, target_date, "First note.")
            add_note(notes_dir, target_date, "Second note.")

            content = file_path(notes_dir, target_date).read_text(encoding="utf-8")
            self.assertIn("### Notes", content)
            self.assertIn("First note.\n\nSecond note.", content)

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
            self.assertEqual(state.days[target_date].notes, ["", "Need to remember cat meds."])

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
