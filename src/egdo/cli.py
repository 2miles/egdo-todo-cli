from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from egdo.config import CONFIG_PATH, load_config, write_config
from egdo.store import add_task, complete_task, file_path, list_tasks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="egdo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create egdo config")
    init_parser.add_argument("--notes-root", required=True)
    init_parser.add_argument("--todos-root", default="egdo")

    add_parser = subparsers.add_parser("add", help="Add a task")
    add_parser.add_argument("text")
    add_parser.add_argument("--date", dest="target_date")

    list_parser = subparsers.add_parser("list", help="List active tasks")
    list_parser.add_argument("--date", dest="target_date")

    done_parser = subparsers.add_parser("done", help="Complete a task")
    done_parser.add_argument("index", type=int)
    done_parser.add_argument("--date", dest="target_date")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            return _run_init(Path(args.notes_root).expanduser(), args.todos_root)

        config = load_config()
        target_date = _parse_target_date(args.target_date)

        if args.command == "add":
            task = add_task(config.notes_dir, target_date, args.text)
            print(f"Added [{task.created.isoformat()}] {task.text}")
            return 0

        if args.command == "list":
            tasks = list_tasks(config.notes_dir, target_date)
            daily_path = file_path(config.notes_dir, target_date)
            print(f"{target_date.isoformat()}  {daily_path}")
            if not tasks:
                print("No active tasks.")
                return 0
            for idx, task in enumerate(tasks, start=1):
                print(f"{idx}. {task.text} (created {task.created.isoformat()})")
            return 0

        if args.command == "done":
            task = complete_task(config.notes_dir, target_date, args.index)
            print(f"Completed [{target_date.isoformat()}] {task.text}")
            return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_init(notes_root: Path, todos_root: str) -> int:
    config_path = write_config(notes_root=notes_root, todos_root=todos_root, path=CONFIG_PATH)
    print(f"Wrote config to {config_path}")
    return 0


def _parse_target_date(value: str | None) -> date:
    if value is None:
        return date.today()
    return date.fromisoformat(value)


if __name__ == "__main__":
    raise SystemExit(main())
