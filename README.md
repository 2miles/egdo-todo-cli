# egdo

`egdo` is a markdown-backed CLI todo manager for daily notes.

It stores tasks and notes in plain monthly markdown files inside your notes directory, so you can use it from the terminal, open the same files in a text editor and still edit everything by hand when needed.

## Why

Most CLI todo tools either hide data behind a database or assume the app is the only thing editing it. `egdo` is built around readable markdown files so you can:

- use the CLI from a terminal
- keep your tasks in normal files
- edit them manually when needed
- maintain a durable archive of what you did over time

## How It Works

- each month has one markdown file
- each day is a section inside that file
- unfinished tasks roll forward the first time you access a new day
- completed tasks stay on the day where you completed them
- notes live alongside tasks for the same day

That gives you a working todo list and a historical record at the same time.

## Features

- markdown-backed storage
- automatic carry-forward for unfinished tasks
- daily notes in the same file as tasks
- leading bracket tags such as `[chores]` or `[home]`
- persistent tag colors in the terminal
- human-editable files

## Installation

If you want `egdo` available from anywhere on your machine, use a dedicated personal tools virtual environment.

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

If you change project dependencies later, run the editable install command again.

## Quick Start

Initialize `egdo`:

```bash
egdo init --root /path/to/egdo
```

- `--root` is the directory where `egdo` stores its yearly files

If you use Obsidian, a typical setup might look like:

```text
root: /Users/you/Notes/egdo
```

That would make `egdo` store files under:

```text
/Users/you/Notes/egdo/2026/2026_04_apr.md
```

Common commands:

```bash
egdo add "Buy milk"
egdo add "[chores] Do the dishes"
egdo
egdo list --tag chores
egdo done 1
egdo edit 2 "Buy oat milk"
egdo delete 2
egdo tag 3 chores home
egdo note "Need to test villager trading setup"
egdo color chores
```

Running `egdo` with no command is the same as `egdo list`.

For the full command reference, see [docs/command-reference.md](/Users/miles/Code/Github/egdo-todo-cli/docs/command-reference.md).

## File Layout

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

- [ ] [chores] Buy milk (04-05)

### Notes

Need to test villager trading setup.
```

The trailing `(MM-DD)` is the date the task originally entered the system.

## Manual Editing

Manual editing is expected.

You can safely:

- change task text in a day’s `### Tasks` section
- add simple checklist items in a `### Tasks` section
- edit or add text in a day’s `### Notes` section
- open and edit the files directly in Obsidian

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

If you prefer not to edit that by hand, use:

```bash
egdo color chores
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

## Current Scope

Current commands:

- `init`
- `add`
- `list`
- `done`
- `edit`
- `delete`
- `tag`
- `color`
- `note`

Not included yet:

- archive commands
- priorities
- recurring tasks
- search or reporting

## License

Add the license you want to use for the project here.
