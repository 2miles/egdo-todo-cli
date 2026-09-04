# egdo

`egdo` is a terminal workflow that carries unfinished tasks forward while preserving
completed work as a plain-Markdown journal.

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

Install egdo, open the directory where your notes live, and initialize your first journal:

```bash
cd ~/Notes
egdo init Main
egdo add "My first task"
egdo
```

Initialization creates a small `.egdo.toml` marker and an `egdo/` archive directory. Year
and month files appear only when you add a task or note:

```text
~/Notes/
├── .egdo.toml
└── egdo/
    └── 2026/
        └── 2026_09_sep.md
```

Run egdo anywhere below `~/Notes` and it recognizes `Main` automatically.
The marker stores only the project identity. Its archive is always the sibling `egdo/`
directory, so moving the initialized directory keeps local use working and refreshes its
global registry location automatically.

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

Initialize another journal from the directory containing its related notes:

```bash
cd ~/Notes/topics/gaming/minecraft
egdo init Minecraft
egdo add "Update server plugins"
```

Inside that directory tree, egdo selects `Minecraft`; elsewhere beneath `~/Notes`, it
selects `Main`. Every list displays its active project. The global `-P/--project` option
always provides an explicit one-command override:

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

## Projects and Configuration

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

The preferred setup is local initialization:

```bash
cd ~/Notes
egdo init Main
```

Egdo selects projects in this order: explicit `-P/--project`, the nearest `.egdo.toml`
found by walking upward, then the global default. Project commands show the registry or
change its global fallback:

```bash
egdo project list
egdo project use Main
```

Project changes preserve unrelated config content and copy the previous version to
`config.toml.bak`.

Initializing or selecting a project does not relocate, modify, combine, or delete another
project's task files. Each root keeps its own tasks, notes, monthly files, numbering, and
completed-task history. To restore previous configuration, use `config.toml.bak`.

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
