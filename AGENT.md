# AGENT.md

## Purpose

`egdo` is a small Python CLI for Markdown-backed daily tasks in a notes directory. Keep changes aligned with that core model: plain files, manual editability, deterministic behavior.

## Working Rules

- Use the repo-local virtual environment in `.venv`.
- Prefer standard library solutions unless a third-party dependency clearly improves the product.
- Keep the CLI small and explicit. Avoid feature creep.
- Preserve manual editing as a first-class workflow.

## Core Invariants

- Monthly files live at `<notes-root>/YYYY/YYYY_MM_mon.md`.
- `egdo init NAME` creates `.egdo.toml` containing only the project identity; its archive is always the sibling `egdo/` directory.
- Project selection precedence is explicit `-P`, nearest local marker, then global default.
- `egdo list --all-projects` computes project snapshots without writing rollover state.
- Daily sections use `## Mon-DD Day`, with `### Tasks` and optional `### Notes` sections.
- Content before the first managed daily section must be preserved.
- Month files contain only populated daily sections; do not generate headers for empty dates.
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
- If changing publish-facing expectations, update `docs/publish-roadmap.md` when relevant.

## Verification

See `docs/build-vs-install.md` for the complete development and release workflows.

Bootstrap the ignored repository-local environment when needed:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e '.[dev]'
```

Run these before finishing:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall src tests
```
