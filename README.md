# egdo

`egdo` is a Markdown-backed command-line task manager. It keeps daily tasks and notes in ordinary monthly files that remain readable and editable without the app.

## Why egdo?

Many task managers treat their database as the source of truth. With `egdo`, your Markdown files are the source of truth:

- unfinished tasks roll forward automatically
- completed tasks remain in a daily archive
- notes live alongside tasks
- files can be viewed and edited in any text editor
- optional tags keep tasks organized without complicating the file format

Each month is stored in a single Markdown file, with sections only for days containing
tasks or notes. Empty dates are omitted. The result is a lightweight task list that
preserves a useful history of your work.

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

Create the default `Main` project:

```bash
egdo project add Main ~/Notes/egdo
```

This writes `~/.config/egdo/config.toml`. The `ROOT` argument tells `egdo` which directory
contains—or will contain—the `Main` task archive. Use the real location where you want
your monthly Markdown files stored.

Use `egdo project set Main NEW_ROOT` to change its location later. This does not move or
delete task files at the previous root, so an incorrect root can make `Main` appear empty.
When updating an existing config, `egdo` preserves its other contents and saves the
previous version as `~/.config/egdo/config.toml.bak`.

Example configuration:

```toml
default_project = "Main"

[projects]
"Main" = "/Users/you/Notes/egdo"
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

Keep an independent task history for another area with a named project:

```bash
egdo project add Minecraft ~/Notes/topics/gaming/minecraft/egdo
egdo project use Minecraft
egdo --project Main list
```

Every list displays its active project. `project use` changes the default, while the
global `-P/--project` option selects a project for one command without changing it:

```bash
egdo -P Minecraft add "Update server plugins"
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

Example:

```toml
default_project = "Main"

[projects]
"Main" = "/Users/you/Notes/egdo"
"Minecraft" = "/Users/you/Notes/topics/gaming/minecraft/egdo"
```

Create the first project with:

```bash
egdo project add Main ~/Notes/egdo
```

Add more projects or change a configured root with:

```bash
egdo project add Minecraft ~/Notes/topics/gaming/minecraft/egdo
egdo project set Minecraft ~/Notes/topics/games/minecraft/egdo
```

Project changes preserve unrelated config content and copy the previous version to
`config.toml.bak`. A legacy config containing only `root = "..."` is read once as the
`Main` project and migrated to the project format when any project setting is saved.

Changing or selecting a project does not relocate, modify, combine, or delete task files.
Each root keeps its own tasks, notes, monthly files, numbering, and completed-task history.
To restore previous configuration, use `config.toml.bak`.

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
