# egdo

`egdo` is a Python CLI todo manager that stores tasks in markdown files inside a notes directory.

The model is simple:

- each day has its own markdown file
- unfinished tasks move forward to the next day when you first access it
- completed tasks stay in the file where you completed them
- everything stays readable and editable by hand

That gives you a working todo list and a historical archive at the same time.

## Why

Most CLI todo tools either hide data behind a database or assume the app is the only thing editing it. `egdo` is built around plain markdown files so you can:

- use the CLI from a terminal
- open the same tasks in Obsidian
- manually edit the files when needed
- keep a durable archive of what you did over time

## Features

- Markdown-backed storage
- One daily file per date
- Per-month folder layout
- Automatic carry-forward for unfinished tasks
- Completion timestamps
- Human-editable files with metadata normalization for manual checklist entries
- Minimal CLI with `add`, `list`, `done`, and `init`

## Installation

Clone the repo, create a local virtual environment in `.venv`, activate it, and install the project there:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This creates the `egdo` command inside the virtual environment from the local checkout.

If you want to deactivate the environment later:

```bash
deactivate
```

## Global Install For Personal Use

If you want `egdo` available from anywhere on your machine without activating the repo-local `.venv`, use a dedicated personal tools virtual environment.

Create it once:

```bash
python3 -m venv ~/.venvs/tools
```

Install `egdo` from this repo into that environment:

```bash
~/.venvs/tools/bin/pip install -e /path/to/egdo-todo-cli
```

Then add the tools environment to your shell `PATH`:

```bash
export PATH="$HOME/.venvs/tools/bin:$PATH"
```

Put that line in `~/.zshrc`, then reload your shell:

```bash
source ~/.zshrc
```

When to run the install command again:

- run it again if you add or change project dependencies
- run it again if packaging metadata changes in a way that affects installation
- you usually do not need to run it again for normal source code edits, because editable install points at your working copy

## Quick Start

Make sure your virtual environment is active first:

```bash
source .venv/bin/activate
```

Initialize `egdo` with your notes path:

```bash
egdo init --notes-root /path/to/your/notes --todos-root egdo
```

Add a task:

```bash
egdo add "Buy milk"
```

List today’s active tasks:

```bash
egdo list
```

Mark a task complete:

```bash
egdo done 1
```

You can also target a specific date:

```bash
egdo add "Write release notes" --date 2026-04-03
egdo list --date 2026-04-03
egdo done 2 --date 2026-04-03
```

## Commands

### `egdo init`

Creates the config file at:

```text
~/.config/egdo/config.toml
```

Example:

```bash
egdo init --notes-root /path/to/your/notes --todos-root egdo
```

Arguments:

- `--notes-root` required absolute or user-relative path to your notes directory
- `--todos-root` path inside the notes directory where `egdo` stores daily files, default: `egdo`

### `egdo add`

Adds a task to the selected day.

```bash
egdo add "Call dentist"
egdo add "Fix parser bug" --date 2026-04-03
```

Behavior:

- uses today by default
- creates the daily file if it does not exist
- first performs rollover for unfinished tasks from the most recent earlier day

### `egdo list`

Lists active tasks for the selected day.

```bash
egdo list
egdo list --date 2026-04-03
```

Behavior:

- uses today by default
- first performs rollover for unfinished tasks from the most recent earlier day
- shows only incomplete tasks
- numbers tasks so you can complete them with `done`

Example output:

```text
2026-04-03  /path/to/your/notes/egdo/2026/04/2026-04-03.md
1. Buy milk (created 2026-04-03)
2. Call dentist (created 2026-04-03)
```

### `egdo done`

Marks a numbered active task complete in the selected day’s file.

```bash
egdo done 1
egdo done 2 --date 2026-04-03
```

Behavior:

- uses today by default
- completes by the numeric index shown in `egdo list`
- stamps the task with the completion date
- keeps the completed task in that day’s file as part of the archive

## File Layout

`egdo` stores files by year and month:

```text
<notes-root>/<todos-root>/YYYY/MM/YYYY-MM-DD.md
```

Example:

```text
/path/to/your/notes/egdo/2026/04/2026-04-03.md
```

## Markdown Format

`egdo` only manages a dedicated section inside the file, so you can keep other notes above or below it.

Example daily file:

```markdown
# Daily Note

Meeting notes and other freeform writing.

## Egdo

<!-- EGDO:START -->

- [ ] Buy milk
  - created: 2026-04-03
  - completed:
  - origin: 2026-04-03

- [x] Ship package
  - created: 2026-04-02
  - completed: 2026-04-03
  - origin: 2026-04-02

<!-- EGDO:END -->
```

Field meanings:

- `created`: the date the task was originally created
- `completed`: the date the task was completed, blank until done
- `origin`: the day the task first entered the system; this stays stable across rollover

You can also add a minimal manual item inside the managed section:

```markdown
- [ ] Pick up prescription
```

or:

```markdown
- [x] Paid invoice
```

On first `egdo list`, `egdo add`, or any other command that reads and rewrites that file, `egdo` will normalize the item into the full metadata form using the file date.

## Carry-Forward Behavior

When you access a new day with `add` or `list`, `egdo` looks for the most recent earlier daily file and moves any unfinished tasks into the current day.

That means:

- incomplete tasks do not stay stranded in old files
- completed tasks stay where they were finished
- your archive reflects when work was actually done

Rollover is idempotent, so repeating `list` for the same day does not duplicate tasks.

## Manual Editing

Manual editing is expected.

You can safely:

- change task text in the managed section
- add simple checklist items inside the managed section without metadata
- add notes outside the managed section
- open and edit the files directly in Obsidian

You should avoid:

- deleting the `<!-- EGDO:START -->` or `<!-- EGDO:END -->` markers
- changing date formats away from `YYYY-MM-DD`

Notes on normalization:

- if a manual open task is missing `created` or `origin`, `egdo` fills them from the file date
- if a manual completed task is missing `completed`, `egdo` fills it from the file date
- if a task already has metadata, `egdo` preserves it unless another command changes task state

## Configuration

The config file is a small TOML file:

```toml
notes_root = "/path/to/your/notes"
todos_root = "egdo"
```

`notes_root` points at your notes directory. `todos_root` is the directory inside that notes directory where `egdo` writes daily files.

## Development

Create and activate the project environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Install in editable mode:

```bash
pip install -e .
```

Freeze dependencies if you want to record the current environment state:

```bash
pip freeze > requirements.txt
```

Right now `egdo` has no third-party runtime dependencies, so `requirements.txt` is intentionally minimal.

## Current Scope

Version 1 intentionally keeps the surface area small:

- `init`
- `add`
- `list`
- `done`

Not included yet:

- task editing from the CLI
- delete/archive commands
- priorities or tags
- recurring tasks
- search or reporting

## License

Add the license you want to use for the project here.
