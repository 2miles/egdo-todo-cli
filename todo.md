- use it for a bit and see which commands you actually reach for
- look for awkward naming or overlapping behavior
- simplify anything that feels clever but not natural

- help text / docs cleanup
- command naming cleanup
- better output formatting
- real-world usage pass to remove friction rather than add scope

- functionally: pretty good
- UX: starting to need polish

- making --help output excellent
- tightening README examples

## Split

A logical split for cli.py would be:

- src/egdo/cli.py
  Keep only main() and maybe build_parser(), or even just a thin entrypoint.
- src/egdo/commands.py
  Command execution functions like run_list, run_future, run_move, etc.
- src/egdo/render.py
  \_render_list_header, \_render_task_line, \_render_separator, wrapping/styling helpers.
- src/egdo/dates.py
  \_parse_future_date, weekday parsing, maybe display-date formatting too.
- src/egdo/colors.py or src/egdo/tag_colors.py
  tag style assignment, validation, interactive picker.

That gives you cleaner boundaries.

For store.py, a good split would be:

- src/egdo/store.py
  High-level public operations only: add_task, list_tasks, move_task, complete_future_task, etc.
- src/egdo/markdown_store.py or src/egdo/files.py
  file parsing/rendering, FileState, DayState, path resolution, read/write helpers.
- src/egdo/task_ops.py
  shared task movement / lookup helpers if they keep growing.

If you want the least disruptive first step, I would do this order:

1. Extract render/UI helpers from cli.py
2. Extract date parsing from cli.py
3. Extract parser-building or command handlers from cli.py
4. Later split parsing/rendering internals out of store.py

## New Features to Add

- Sub tasks
- search
- recurring tasks,
- “review carried forward” flow
