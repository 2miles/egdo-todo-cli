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
- tags use leading brace groups such as `{CHORES}` or `{HOME}`
- tag colors stay stable in the terminal once assigned

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
egdo add "Buy milk"
egdo add -t chores -t home "Do the dishes"
egdo add -p high -t work "Submit application"
egdo add --done -t car -t errands "Call the DMV"
egdo
egdo list -t chores
egdo finished
egdo future
egdo future done 1
egdo done 1
egdo done 1 3 12
egdo edit 2 "Buy oat milk"
egdo move 1 6 7 tomorrow
egdo future unmove 1
egdo delete 1 6 7
egdo tag 1 6 7 chores home
egdo tag 3 6 7 --remove work
egdo priority 1 6 7 high
egdo priority 3 critical
egdo note "Need to test villager trading setup"
egdo color --tag chores
egdo color --tag chores home --style blue
```

Running `egdo` with no command is the same as `egdo list`.

`egdo list` groups tasks as `Today`, `Old`, and `Future` using one continuous set of indexes. Normal commands such as `done`, `delete`, `move`, `tag`, `priority`, and `edit` automatically operate on the selected task regardless of its group.

`egdo future` remains available as an optional filtered view, but it preserves the same global indexes shown by the main list.

You can create tags either from the CLI with repeated `-t` or `--tag` flags or by typing leading brace tags directly in the markdown, such as `{CHORES} {HOME} Do the dishes`.

Priorities use `!P1!` through `!P4!` in Markdown. Add one with `-p` or `--priority`, using `1`/`critical`, `2`/`high`, `3`/`normal`, or `4`/`low`. Use `egdo priority INDEX LEVEL` to change an existing task, or use `none` as the level to clear it.

In terminal lists, egdo renders priority as a three-slot meter: `!!!` for P1, `.!!` for P2, `..!` for P3, and `...` for P4. Dots are gray placeholders and exclamation marks carry the priority color. Tasks without an explicit priority display as low priority (`...`) without changing their stored Markdown.

For the full command reference, see [docs/command-reference.md](/Users/miles/Code/Github/egdo-todo-cli/docs/command-reference.md).

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

- [ ] !P2! {CHORES} Buy milk (04-05)

### Notes

Need to test villager trading setup.
```

The trailing `(MM-DD)` is the date the task first entered the system.

## Manual Editing

Manual editing is a normal part of the workflow.

You can safely:

- change task text in a day’s `### Tasks` section
- add simple checklist items in a `### Tasks` section
- create tags by typing leading brace groups such as `{CHORES}` or `{HOME}`
- add or change priority by typing a leading marker such as `!P1!`
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

Tag colors are stored in the same file:

```toml
[tag_colors]
chores = "blue"
important = "bold red"
```

Priority styles use a separate table:

```toml
[priority_styles]
p1 = "bold white on red"
p2 = "bold orange1"
p3 = "yellow"
p4 = "grey50"
```

P1–P3 style their exclamation marks. P4 styles all gray placeholder dots, including dots shown in higher-priority meters.

If you prefer not to edit that by hand, use:

```bash
egdo color --tag chores
egdo color --priority high --style "bold orange1"
```

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
