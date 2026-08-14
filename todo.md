- use it for a bit and see which commands you actually reach for
- look for awkward naming or overlapping behavior
- simplify anything that feels clever but not natural

- keep help text and docs synchronized as behavior changes
- real-world usage pass to remove friction rather than add scope

- functionally: pretty good
- UX: starting to need polish

- periodically review `--help` output and README examples against actual behavior

## Architecture

The current module split is:

- src/egdo/cli.py
  Argument parsing, dependency wiring, and the process entrypoint.
- src/egdo/handlers.py
  Command execution and terminal-facing workflows.
- src/egdo/render.py
  List headers, task rows, separators, wrapping, and styling.
- src/egdo/dates.py
  Date parsing and display formatting.

- src/egdo/store.py
  High-level task operations, rollover, movement, and global indexing.
- src/egdo/markdown_store.py
  File parsing/rendering, FileState, DayState, path resolution, and persistence.

The major boundaries have been extracted. Only split `store.py` further if new behavior
makes another boundary clearly useful.

## New Features to Add

- search
- recurring tasks,
- “review carried forward” flow
