# AGENT.md

## Purpose

`egdo` is a small Python CLI for markdown-backed daily todos in a notes directory. Keep changes aligned with that core model: plain files, manual editability, deterministic behavior.

## Working Rules

- Use the repo-local virtual environment in `.venv`.
- Prefer standard library solutions unless a third-party dependency clearly improves the product.
- Keep the CLI small and explicit. Avoid feature creep.
- Preserve manual editing as a first-class workflow.

## Core Invariants

- Monthly files live at `<notes-root>/YYYY/YYYY_MM_mon.md`.
- Daily sections use `## Mon-DD Day`, with `### Tasks` and optional `### Notes` sections.
- Content before the first managed daily section must be preserved.
- Unfinished tasks roll forward on first access to a new day.
- Completed tasks stay in the file where they were completed.
- Manual checklist items in task sections are valid input and should normalize cleanly.
- A task has zero or one leading brace tag and zero or one leading `!` priority marker.

## Code Map

- `src/egdo/cli.py`: argument parsing, dependency wiring, and process entrypoint
- `src/egdo/handlers.py`: command dispatch and terminal-facing workflows
- `src/egdo/config.py`: config load/write
- `src/egdo/dates.py`: date parsing and display formatting
- `src/egdo/interactive.py`: interactive add and completion forms
- `src/egdo/render.py`: Rich terminal rendering
- `src/egdo/store.py`: task/note operations, rollover, and global indexing
- `src/egdo/markdown_store.py`: Markdown parsing, normalization, and persistence
- `tests/test_store.py`: storage and rollover behavior tests

## Change Guidance

- Prefer deterministic section rewrites over fragile in-place text editing.
- Add tests for behavior changes, especially parser, rollover, and manual-edit cases.
- If changing the Markdown contract, update `README.md`, `docs/guide.md`, and `docs/command-reference.md`.
- If changing publish-facing expectations, update `publish_roadmap.md` when relevant.

## Verification

Run these before finishing:

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests
python3 -m compileall src tests
```
