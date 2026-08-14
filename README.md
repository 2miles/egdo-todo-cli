# egdo

`egdo` is a Markdown-backed command-line task manager. It keeps daily tasks and notes in ordinary monthly files that remain readable and editable without the app.

## Why egdo?

Many task managers treat their database as the source of truth. With `egdo`, your Markdown files are the source of truth:

- unfinished tasks roll forward automatically
- completed tasks remain in a daily archive
- notes live alongside tasks
- files can be viewed and edited in any text editor
- optional tags keep tasks organized without complicating the file format

Each month is stored in a single Markdown file, with one section per day. The result is a lightweight task list that preserves a useful history of your work.

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

Configure `egdo`:

```bash
egdo config --root ~/Notes/egdo
```

This writes `~/.config/egdo/config.toml`. The `--root` value tells `egdo` which directory
contains—or will contain—your task archive. Use the real location where you want your
monthly Markdown files stored.

Running the command again changes where `egdo` looks for tasks. It does not move or delete
the task files at the previous root, so an incorrect root can make your list appear empty.
When updating an existing config, `egdo` preserves its other contents and saves the
previous version as `~/.config/egdo/config.toml.bak`.

Example:

```text
root: /Users/you/Notes/egdo
```

That stores files under:

```text
/Users/you/Notes/egdo/2026/2026_04_apr.md
```

## Basic Usage

View your tasks:

```bash
egdo
```

Add and complete tasks:

```bash
egdo add "Buy milk"
egdo done 1
```

Schedule a task for another day:

```bash
egdo move 2 tomorrow
egdo move 5 today
```

Organize tasks with tags and priority:

```bash
egdo add -t chores "Do the dishes"
egdo add -p important -t work "Submit application"
```

Running `egdo` without a command displays today’s tasks, carried-forward work, and
scheduled tasks in one numbered list. Use those numbers with commands such as `done`,
`edit`, `move`, `delete`, `tag`, and `priority`.

For interactive task creation, run `egdo add` without text. To choose tasks from an
interactive completion list, run `egdo done` without IDs.

Additional views:

```bash
egdo list --future
egdo list --completed
egdo list -t chores
```

Tasks are stored in ordinary Markdown files. They may have one optional tag, one binary
priority, and up to two levels of subtasks.

See the [complete guide](docs/guide.md) for workflows and the
[command reference](docs/command-reference.md) for every option.

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
root = "/Users/you/Notes/egdo"
```

Set or change this value with:

```bash
egdo config --root ~/Notes/egdo
```

The command creates the config when it does not exist. When it already exists, the command
changes only its top-level `root` setting, preserves all other content, and copies the
previous version to `config.toml.bak`.

Changing the root does not relocate, modify, or delete existing task files. It only changes
where subsequent commands look for them. To return to the previous location, run
`egdo config --root PREVIOUS_LOCATION` or restore `config.toml.bak`.

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

Licensed under the [MIT License](LICENSE).
