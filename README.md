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
- tags use leading bracket groups such as `[chores]` or `[home]`
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
egdo
egdo list -t chores
egdo future
egdo future done 1
egdo done 1
egdo edit 2 "Buy oat milk"
egdo move 2 tomorrow
egdo future unmove 1
egdo delete 2
egdo tag 3 chores home
egdo note "Need to test villager trading setup"
egdo color chores
```

Running `egdo` with no command is the same as `egdo list`.

`egdo future unmove INDEX` takes a task from the `egdo future` view and puts it back on today's active list.

You can create tags either from the CLI with repeated `-t` or `--tag` flags or by typing leading bracket tags directly in the markdown, such as `[chores][home] Do the dishes`.

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

- [ ] [chores] Buy milk (04-05)

### Notes

Need to test villager trading setup.
```

The trailing `(MM-DD)` is the date the task first entered the system.

## Manual Editing

Manual editing is a normal part of the workflow.

You can safely:

- change task text in a day’s `### Tasks` section
- add simple checklist items in a `### Tasks` section
- create tags by typing leading bracket groups such as `[chores]` or `[home]`
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

## License

Add the license you want to use for the project here.
