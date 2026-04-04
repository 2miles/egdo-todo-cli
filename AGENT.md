# AGENT.md

## Purpose

`egdo` is a small Python CLI for markdown-backed daily todos in a notes directory. Keep changes aligned with that core model: plain files, manual editability, deterministic behavior.

## Working Rules

- Use the repo-local virtual environment in `.venv`.
- Prefer standard library solutions unless a third-party dependency clearly improves the product.
- Keep the CLI small and explicit. Avoid feature creep.
- Preserve manual editing as a first-class workflow.

## Core Invariants

- `egdo` only owns the managed section between `<!-- EGDO:START -->` and `<!-- EGDO:END -->`.
- Content outside the managed section must be preserved exactly.
- Daily files live at `<notes-root>/<todos-root>/YYYY/MM/YYYY-MM-DD.md`.
- Unfinished tasks roll forward on first access to a new day.
- Completed tasks stay in the file where they were completed.
- Manual checklist items inside the managed section are valid input and should normalize cleanly.

## Code Map

- `src/egdo/cli.py`: command-line interface and command dispatch
- `src/egdo/config.py`: config load/write
- `src/egdo/store.py`: markdown parsing, normalization, rollover, persistence
- `tests/test_store.py`: storage and rollover behavior tests

## Change Guidance

- Prefer deterministic section rewrites over fragile in-place text editing.
- Add tests for behavior changes, especially parser, rollover, and manual-edit cases.
- If changing the markdown contract, update `README.md` and `egdo_v1_plan.md`.
- If changing publish-facing expectations, update `publish_roadmap.md` when relevant.

## Verification

Run these before finishing:

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests
python3 -m compileall src tests
```
