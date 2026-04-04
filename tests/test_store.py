from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from egdo.store import (
    SECTION_END,
    SECTION_START,
    add_task,
    complete_task,
    ensure_state,
    file_path,
    list_tasks,
)


class StoreTests(unittest.TestCase):
    def test_add_task_creates_daily_file(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 3)

            add_task(notes_dir, target_date, "Buy milk")

            path = file_path(notes_dir, target_date)
            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertIn("Buy milk", content)
            self.assertIn(SECTION_START, content)
            self.assertIn(SECTION_END, content)

    def test_add_preserves_existing_manual_notes(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 3)
            path = file_path(notes_dir, target_date)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Daily Note\n\nFreeform notes.\n", encoding="utf-8")

            add_task(notes_dir, target_date, "Buy milk")

            content = path.read_text(encoding="utf-8")
            self.assertIn("# Daily Note", content)
            self.assertIn("Freeform notes.", content)
            self.assertIn("Buy milk", content)

    def test_list_rolls_forward_unfinished_tasks(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 3), "Buy milk")

            tasks = list_tasks(notes_dir, date(2026, 4, 4))

            self.assertEqual([task.text for task in tasks], ["Buy milk"])
            previous_state = ensure_state(file_path(notes_dir, date(2026, 4, 3)))
            self.assertEqual(previous_state.tasks, [])

    def test_rollover_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 3), "Buy milk")

            first = list_tasks(notes_dir, date(2026, 4, 4))
            second = list_tasks(notes_dir, date(2026, 4, 4))

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)

    def test_done_marks_task_complete_in_current_file(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 3), "Buy milk")
            list_tasks(notes_dir, date(2026, 4, 4))

            task = complete_task(notes_dir, date(2026, 4, 4), 1)

            self.assertEqual(task.completed, date(2026, 4, 4))
            content = file_path(notes_dir, date(2026, 4, 4)).read_text(encoding="utf-8")
            self.assertIn("- [x] Buy milk", content)
            self.assertIn("completed: 2026-04-04", content)

    def test_done_uses_current_day_active_index(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 3), "Buy milk")
            add_task(notes_dir, date(2026, 4, 4), "Ship box")

            complete_task(notes_dir, date(2026, 4, 4), 2)

            state = ensure_state(file_path(notes_dir, date(2026, 4, 4)))
            completed = {task.text: task.completed for task in state.tasks}
            self.assertIsNone(completed["Buy milk"])
            self.assertEqual(completed["Ship box"], date(2026, 4, 4))

    def test_manual_edit_inside_section_remains_parseable(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            add_task(notes_dir, date(2026, 4, 3), "Buy milk")
            path = file_path(notes_dir, date(2026, 4, 3))
            content = path.read_text(encoding="utf-8").replace("Buy milk", "Buy oat milk")
            path.write_text(content, encoding="utf-8")

            tasks = list_tasks(notes_dir, date(2026, 4, 3))

            self.assertEqual([task.text for task in tasks], ["Buy oat milk"])

    def test_manual_task_without_metadata_is_normalized_on_list(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 3)
            path = file_path(notes_dir, target_date)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "# Daily Note",
                        "",
                        "## Egdo",
                        "<!-- EGDO:START -->",
                        "",
                        "- [ ] Manual task",
                        "",
                        "<!-- EGDO:END -->",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            tasks = list_tasks(notes_dir, target_date)

            self.assertEqual([task.text for task in tasks], ["Manual task"])
            content = path.read_text(encoding="utf-8")
            self.assertIn("created: 2026-04-03", content)
            self.assertIn("origin: 2026-04-03", content)
            self.assertIn("completed:", content)

    def test_manual_completed_task_without_completed_date_is_normalized(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 3)
            path = file_path(notes_dir, target_date)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "## Egdo",
                        "<!-- EGDO:START -->",
                        "",
                        "- [x] Finished manually",
                        "",
                        "<!-- EGDO:END -->",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            tasks = list_tasks(notes_dir, target_date)

            self.assertEqual(tasks, [])
            state = ensure_state(path)
            self.assertEqual(len(state.tasks), 1)
            self.assertEqual(state.tasks[0].completed, target_date)
            self.assertEqual(state.tasks[0].created, target_date)
            self.assertEqual(state.tasks[0].origin, target_date)

    def test_managed_heading_is_not_duplicated_on_rewrite(self) -> None:
        with TemporaryDirectory() as tmp:
            notes_dir = Path(tmp)
            target_date = date(2026, 4, 3)
            path = file_path(notes_dir, target_date)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "# Daily Note",
                        "",
                        "## Egdo",
                        "<!-- EGDO:START -->",
                        "",
                        "- [ ] Manual task",
                        "",
                        "<!-- EGDO:END -->",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            list_tasks(notes_dir, target_date)
            complete_task(notes_dir, target_date, 1)

            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("## Egdo"), 1)


if __name__ == "__main__":
    unittest.main()
