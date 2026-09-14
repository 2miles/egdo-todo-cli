# Architecture

This document is a map of the Egdo codebase for contributors. User-facing behavior belongs
in the [guide](guide.md) and [command reference](command-reference.md).

## Core Model

Markdown files are the source of truth. Python objects are temporary structured state used
while a command runs:

```text
CLI input
   ↓
Project selection and command handling
   ↓
Parse Markdown → read or mutate state → render Markdown
   ↓
Terminal output
```

There is no task database. Each project owns an independent monthly Markdown archive, while
the global configuration only records project names, locations, and the active project.

## Module Responsibilities

- `cli.py` defines the command grammar, wires dependencies, selects projects, and handles
  process-level errors.
- `handlers.py` coordinates user-facing command behavior without owning persistence details.
- `config.py` reads and writes the project registry, manages local markers, and resolves the
  active project.
- `store.py` implements task and note operations such as rollover, creation, completion,
  movement, tagging, and deletion.
- `markdown_store.py` parses monthly files into structured state and renders that state back
  into canonical Markdown.
- `dates.py` interprets scheduling expressions and formats dates for display.
- `interactive.py` owns guided forms and task pickers.
- `terminal_keys.py` provides the low-level keyboard input used by interactive screens.
- `render.py` owns terminal headers, task rows, section separators, and project-list output.

## Data Flow

Most task commands follow the same path:

1. `cli.py` parses arguments and resolves the active project.
2. `handlers.py` collects any missing interactive input and selects an operation.
3. `store.py` loads the relevant archive state and applies the operation.
4. `markdown_store.py` writes the canonical monthly Markdown when state changes.
5. `render.py` builds the terminal presentation.

Read-only operations stop before the write step. In particular, the all-projects view
computes rollover in memory so reviewing every project does not modify every archive.

## Stored State

A monthly file is parsed into a `FileState` containing dated `DayState` values. Each day can
hold `Task` objects and free-form notes. For example:

```markdown
## Jul-12 Sun

### Tasks

- [ ] {ERRANDS} Go to the grocery store (07-12)
- [x] Finish lookup table (07-12)

### Notes

Remember to follow up tomorrow.
```

The parser validates that headings match the file's year and month, checklist syntax,
creation dates, section placement, and nesting. A canonical file contains at most one section
per populated date, with optional `### Tasks` and `### Notes` subsections. The renderer omits
empty dates, preserves preamble and Notes content, and atomically replaces monthly files.

## Important Boundaries

- Task semantics belong in `store.py`, not the CLI or renderer.
- Markdown parsing and canonical serialization belong in `markdown_store.py`.
- Terminal styling must not change stored task text.
- Interactive and direct commands should converge on the same store operations.
- Project selection must not move, merge, or delete another project’s files.
- Tests should exercise observable behavior at the lowest appropriate layer.

## Writing Conventions

- Write “Markdown” with a capital M and use “task” rather than “todo” for Egdo concepts.
- Use “ID” in user-facing text; “index” is reserved for internal implementation details.
- Use `YYYY-MM-DD` for CLI dates, `Mon-DD Day` for stored headings, and readable month names
  in terminal displays.
- Use curly quotation marks around user-provided names and text. Use backticks for commands,
  configuration keys, and literal syntax.
- Use `→` for movement or scheduling in user-facing output and `—` for secondary details.

## Reading the Repository

A useful order for understanding the code is:

1. `cli.py` for the available commands and dependency wiring.
2. `handlers.py` for command workflows.
3. `store.py` for task and note behavior.
4. `markdown_store.py` for the persisted format.
5. `config.py` for project identity, selection, and lifecycle.
6. `interactive.py` and `render.py` for terminal interaction and presentation.

## Versioning and Release Maintenance

Egdo uses semantic versioning with a single version source in `src/egdo/__init__.py`.
Before 1.0, use patch releases such as `0.1.1` for compatible fixes and minor releases such
as `0.2.0` for features or intentional compatibility breaks. Release `1.0.0` only when the
CLI, configuration, and Markdown storage expectations are considered stable.

Maintain an `Unreleased` section in `CHANGELOG.md` as user-facing behavior changes. For a
release:

1. Run the full test suite and clean-install checks.
2. Update `__version__` in `src/egdo/__init__.py`.
3. Rename the changelog's `Unreleased` content to the version and release date, then add a
   new empty `Unreleased` section.
4. Commit the release and tag that commit with the matching `vX.Y.Z` tag.

When changing Python support, update `requires-python` and the classifiers in
`pyproject.toml`, the Installation statement in `README.md`, and the matrix in
`.github/workflows/ci.yml` together. Record dropped or newly supported versions in the
changelog. Do not add a newly released Python version to the documented range until CI passes
on it, and remove an end-of-life version deliberately in a release rather than silently.
