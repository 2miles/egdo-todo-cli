# egdo

`egdo` is a Python CLI todo manager that stores tasks and notes in monthly markdown files inside a notes directory.

The model is simple:

- each month has its own markdown file
- each day is a section inside that month file
- unfinished tasks move forward to the next day when you first access it
- completed tasks stay on the day where you completed them
- notes live alongside tasks for the same day
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
- One monthly file per month
- Per-day sections inside each month file
- Automatic carry-forward for unfinished tasks
- Daily notes stored in the same file
- Human-editable files with metadata normalization for manual checklist entries
- Minimal CLI with `add`, `list`, `done`, `delete`, `tag`, `color`, `note`, and `init`

## Installation

If you want `egdo` available from anywhere on your machine, use a dedicated personal tools virtual environment.

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

Initialize `egdo` with your notes path:

```bash
egdo init --notes-root /path/to/your/notes --todos-root egdo
```

Add a task:

```bash
egdo add "Buy milk"
egdo add "[chores] Do the dishes"
egdo add --done "Call dad"
```

List today’s active tasks:

```bash
egdo
egdo list
egdo list --tag chores
```

Mark a task complete:

```bash
egdo done 1
```

Delete a task:

```bash
egdo delete 2
```

Add tags to a task:

```bash
egdo tag 3 chores home
```

Add a note for today:

```bash
egdo note "Need to test villager trading setup"
```

Set a tag color:

```bash
egdo color chores
egdo color chores --style green_yellow
```

## Commands

Running `egdo` with no command is a shortcut for `egdo list`.

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
- `--todos-root` path inside the notes directory where `egdo` stores monthly files, default: `egdo`

### `egdo add`

Adds a task to today’s active list.

```bash
egdo add "Call dentist"
egdo add "[chores] Do the dishes"
egdo add "[personal][chores][home] Do the dishes"
egdo add --done "Call dad"
```

Behavior:

- uses today by default
- creates the monthly file and day section if they do not exist
- first performs rollover for unfinished tasks from the most recent earlier day
- preserves any leading bracket tags as plain text in the task body
- `--done` creates the task already completed

### `egdo list`

Lists active tasks for today.

```bash
egdo
egdo list
egdo list --tag chores
```

Behavior:

- running bare `egdo` is the same as `egdo list`
- uses today by default
- first performs rollover for unfinished tasks from the most recent earlier day
- shows only incomplete tasks
- `--tag` filters by leading bracket tags such as `[chores]` or `[home]`
- numbers tasks so you can complete them with `done`

Example output:

```text
Thu, Apr 3rd
────────────────────────────────────────
1. [chores] Buy milk (Thu, Apr 3rd)
2. Call dentist (Thu, Apr 3rd)
```

### `egdo done`

Marks a numbered active task complete in today’s file.

```bash
egdo done 1
```

Behavior:

- uses today by default
- completes by the numeric index shown in `egdo list`
- keeps the completed task in that day’s file as part of the archive

### `egdo delete`

Removes a numbered active task from today’s file.

```bash
egdo delete 2
```

Behavior:

- uses today by default
- deletes by the numeric index shown in `egdo list`
- removes the task entirely instead of marking it complete

### `egdo tag`

Adds one or more tags to a numbered active task in today’s file.

```bash
egdo tag 3 chores
egdo tag 3 chores home
```

Behavior:

- uses today by default
- updates the task by the numeric index shown in `egdo list`
- stores tags as leading bracket groups such as `[chores][home]`
- ignores duplicate tags and normalizes tag names to lowercase

### `egdo note`

Appends a note to today’s Notes section.

```bash
egdo note "Need to test villager trading setup"
```

Behavior:

- uses today by default
- creates the monthly file and day section if they do not exist
- appends each new note as a new paragraph in that day’s Notes section

### `egdo color`

Sets the terminal color for a tag.

```bash
egdo color chores
egdo color chores --style green_yellow
```

Behavior:

- normalizes the tag name to lowercase
- opens an interactive up/down picker by default so you can see the available colors before saving
- supports `j` and `k` in addition to the arrow keys
- saves the selected Rich style in `[tag_colors]` in the config file
- `--style` skips the picker and writes the provided Rich style directly

## File Layout

`egdo` stores files by year and month:

```text
<notes-root>/<todos-root>/YYYY/YYYY_MM_mon.md
```

Example:

```text
/path/to/your/notes/egdo/2026/2026_04_apr.md
```

## Markdown Format

`egdo` stores each day as a section inside the month file.

Example month file:

```markdown
## Apr-04 Sat

### Tasks

- [x] [minecraft] Add sorter overflow protection (04-04)
- [x] [chores] Do laundry (04-04)

### Notes

Need to test villager trading setup.

## Apr-05 Sun

## Apr-06 Mon

### Tasks

- [ ] [chores] Buy milk (04-04)
- [ ] [home] Fix shelf (04-05)
```

Field meanings:

- trailing `(MM-DD)`: the date the task originally entered the system

Tag convention:

- leading bracket groups are treated as tags for filtering
- `[personal][chores][home] Do the dishes` has tags `personal`, `chores`, and `home`
- brackets later in the task text are treated as normal text
- tag colors are assigned once and stored in config so they stay stable across lists

You can also add a minimal manual item inside the managed section:

```markdown
- [ ] Pick up prescription
```

or:

```markdown
- [x] Paid invoice
```

On first `egdo list`, `egdo add`, or any other command that reads and rewrites that file, `egdo` will normalize the item into the standard one-line task form using the day section date.

## Carry-Forward Behavior

When you access a new day with `add`, `list`, `done`, `delete`, or `tag`, `egdo` looks for the most recent earlier day section and moves any unfinished tasks into the current day.

That means:

- incomplete tasks do not stay stranded in old files
- completed tasks stay where they were finished
- your archive reflects when work was actually done

Rollover is idempotent, so repeating `list` for the same day does not duplicate tasks.

## Manual Editing

Manual editing is expected.

You can safely:

- change task text inside a day’s Tasks section
- add simple checklist items inside a Tasks section
- edit or add text inside a day’s Notes section
- open and edit the files directly in Obsidian

You should avoid:

- changing the `## Apr-05 Sun` day header format
- changing task date suffixes away from `MM-DD`

Notes on normalization:

- if a manual task is missing its trailing `(MM-DD)` date, `egdo` fills it from the day section date
- if a task already has a valid trailing `(MM-DD)` date, `egdo` preserves it unless another command changes task state

## Configuration

The config file is a small TOML file:

```toml
notes_root = "/path/to/your/notes"
todos_root = "egdo"
```

`notes_root` points at your notes directory. `todos_root` is the directory inside that notes directory where `egdo` writes monthly files.

### Tag Colors

Tag colors are stored separately in the same config file and control how leading bracket tags render in the terminal.

Available colors: https://rich.readthedocs.io/en/stable/appendix/colors.html

```toml
[tag_colors]
minecraft = "green"
chores = "blue"
important = "bold red"
```

`tag_colors` stores persistent terminal color assignments for tags discovered while listing tasks.

Style values use Rich style names such as `green`, `blue`, `magenta`, `bright_yellow`, or `bold red`. If a configured tag style is invalid, `egdo list` warns and replaces it with the next palette color.

If you want to pick from the built-in palette visually instead of editing config by hand, run:

```bash
egdo color chores
```

## Development

If you are using the same global tools environment for development, reinstall after dependency or packaging changes:

```bash
~/.venvs/tools/bin/pip install -e /path/to/egdo-todo-cli
```

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Compile the source tree:

```bash
python3 -m compileall src
```

Freeze dependencies if you want to record the current environment state:

```bash
pip freeze > requirements.txt
```

`egdo` currently uses `rich` for terminal styling, so `requirements.txt` stays small but is no longer standard-library-only.

## Current Scope

Version 1 intentionally keeps the surface area small:

- `init`
- `add`
- `list`
- `done`
- `delete`
- `tag`
- `color`
- `note`

Not included yet:

- task editing from the CLI
- archive commands
- priorities
- recurring tasks
- search or reporting

## License

Add the license you want to use for the project here.
