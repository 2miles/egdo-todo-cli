# egdo

`egdo` is a markdown-backed CLI todo manager built for people who want their tasks in normal files.

It keeps daily tasks and notes in plain monthly markdown files. You use it from the terminal, but the data stays readable and editable without the app.

## Why

Most CLI todo tools either hide data behind a database or assume the app owns the data. `egdo` takes the opposite approach:

- tasks live in normal markdown files
- you can edit them by hand when needed
- unfinished work rolls forward automatically
- completed work stays where it happened
- your todo list doubles as a long-term archive

In practice:

- each month has one markdown file
- each day is a section inside that file
- notes live alongside tasks for the same day
- a tag uses one leading brace group such as `{CHORES}` or `{HOME}`
- tags appear as subdued uppercase labels in terminal lists

The result is a todo list that stays lightweight without throwing away history.

## Installation

If you want `egdo` available from anywhere on your machine, install it into a small personal tools virtual environment.

```bash
python3 -m venv ~/.venvs/tools
~/.venvs/tools/bin/pip install -e /path/to/egdo-todo-cli
```

Then add it to your shell `PATH`:

```bash
export PATH="$HOME/.venvs/tools/bin:$PATH"
```

Put that line in `~/.zshrc`, then reload your shell:

```bash
source ~/.zshrc
```

If project dependencies change later, run the editable install command again.

## Quick Start

Initialize `egdo`:

```bash
egdo init --root /path/to/egdo
```

- `--root` is the directory where `egdo` stores its yearly files

Example:

```text
root: /Users/you/Notes/egdo
```

That stores files under:

```text
/Users/you/Notes/egdo/2026/2026_04_apr.md
```

Common commands:

```bash
egdo add
egdo add "Buy milk"
egdo add -t chores "Do the dishes"
egdo add -p important -t work "Submit application"
egdo add --parent 1 "Add tests"
egdo add --parent 1a "Test missing values"
egdo add --done -t errands "Call the DMV"
egdo
egdo list -t chores
egdo finished
egdo list --future
egdo done 1
egdo done 1 3 12
egdo edit 2 "Buy oat milk"
egdo move 1 6 7 tomorrow
egdo unmove 1
egdo delete 1 6 7
egdo tag 1 6 7 chores
egdo tag 3 6 7 --remove
egdo priority 1 6 7 important
egdo priority 3 normal
egdo note "Need to test villager trading setup"
```

Running `egdo` with no command is the same as `egdo list`.

Running `egdo add` without task text opens an interactive form for the description,
an existing or new tag, priority, and schedule. The pickers use arrow or Vim navigation,
Space to select a tag, and Enter to continue. Supplying task text keeps the immediate
one-line behavior used by scripts and quick entry.

Running `egdo done` without IDs opens a completion form showing the current global task
IDs. Use arrow keys or j/k to move, Space to select, and Enter to complete; direct
`egdo done ID...` usage remains available.

After a successful task mutation in an interactive terminal, egdo clears the screen,
shows a confirmation at the top, and redraws the current list. This applies to `add`,
`done`, `edit`, `move`, `unmove`, `delete`, `tag`, and `priority`. Redirected and piped
output keeps the compact confirmation-only behavior.

`egdo list` groups tasks as `Today`, `Carried forward`, and scheduled future dates using one continuous set of indexes. Carried-forward tasks are ordered by creation date, newest first, while tasks from the same date retain their existing order. Normal commands such as `done`, `delete`, `move`, `tag`, `priority`, and `edit` automatically operate on the selected task regardless of its group.

`egdo list --future` provides an optional future-only view while preserving the same global indexes shown by the main list.

Each task may have zero or one tag. Create it with `-t`/`--tag` or type one leading brace tag directly in Markdown, such as `{CHORES} Do the dishes`. Only the first leading brace group is treated as a tag; later brace groups are ordinary task text. Running `egdo tag IDS TAG` replaces the selected tasks' existing tag; `egdo tag IDS --remove` clears it.

Tasks may be nested three levels deep. Child IDs use letters (`1a`, `1b`) and grandchildren use dotted letters (`1a.a`). Actions on a parent cascade to its descendants, except `edit`, which changes only the selected task's text.

Priority is binary: a leading `!` in Markdown marks a task as important, while no marker means normal. Use `-p important` when adding a task or `egdo priority ID important`; use `normal` to remove the marker.

Terminal lists show an uncolored `●` for important tasks and leave the priority column empty for normal tasks.

For a practical walkthrough and cheat sheet, see [The Complete egdo Guide](docs/guide.md).
For every command and argument, see the [command reference](docs/command-reference.md).

## Storage Format

Files are stored like this:

```text
<root>/YYYY/YYYY_MM_mon.md
```

Example:

```text
/path/to/your/notes/egdo/2026/2026_04_apr.md
```

Each day is a section in that month file:

```markdown
## Apr-05 Sun

### Tasks

- [ ] ! {CHORES} Buy milk (04-05)

### Notes

Need to test villager trading setup.
```

The trailing `(MM-DD)` is the date the task first entered the system.

## Manual Editing

Manual editing is a normal part of the workflow.

You can safely:

- change task text in a day’s `### Tasks` section
- add simple checklist items in a `### Tasks` section
- create a tag by typing one leading brace group such as `{CHORES}` or `{HOME}`
- mark a task important by typing a leading `!`
- edit or add text in a day’s `### Notes` section
- open and edit the files directly in any text editor

You should avoid:

- changing the `## Apr-05 Sun` day header format
- changing task date suffixes away from `MM-DD`

If a manual task is missing its trailing `(MM-DD)` date, `egdo` fills it in from the day section date the next time it normalizes the file.

## Configuration

The config file lives at:

```text
~/.config/egdo/config.toml
```

Minimal example:

```toml
root = "/path/to/egdo"
```

Terminal lists render the tag as an uppercase, dim cyan label without the Markdown braces.
The tag column has a fixed width; long labels are shortened with an ellipsis for display
without changing the full tag stored in Markdown.

## Development

Run tests:

```bash
python3 -m unittest discover -s tests
```

Compile the source tree:

```bash
python3 -m compileall src
```

## License

Add the license you want to use for the project here.
