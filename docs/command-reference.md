# Command Reference

## Commands

| Command | Purpose | Interactive |
| --- | --- | --- |
| [`egdo init NAME`](#egdo-init) | Initialize a journal | No |
| [`egdo project`](#egdo-project) | Choose or manage projects | Yes |
| [`egdo add`](#egdo-add) | Add a task | Yes |
| [`egdo`](#egdo-list) / [`egdo list`](#egdo-list) | Show tasks and filtered views | No |
| [`egdo done`](#egdo-done) | Complete tasks | Yes |
| [`egdo edit`](#egdo-edit) | Edit a task | Yes |
| [`egdo move`](#egdo-move) | Reschedule tasks | Yes |
| [`egdo delete`](#egdo-delete) | Delete tasks | Yes |
| [`egdo tag`](#egdo-tag) | Set or remove tags | Yes |
| [`egdo priority`](#egdo-priority) | Set task priority | Yes |
| [`egdo note`](#egdo-note) | Add a note | Yes |

Interactive commands open a guided prompt when required input is omitted.

## `egdo init`

Initialize a named journal in the current directory:

```bash
cd ~/Notes
egdo init Main
```

This creates a `.egdo.toml` project marker and a sibling `egdo/` archive, then registers the
project. The first initialized project becomes the default; initializing additional projects
does not change it.

Running the command again for the same project is safe. Commands run from the initialized
directory or its descendants automatically use that project. Monthly files are created only
after adding a task or note.

## `egdo project`

List projects or choose the global default:

```bash
egdo project
egdo project list
egdo project use Minecraft
egdo project remove Demo
```

- `egdo project` opens the default-project picker
- `egdo project list` shows every project and marks the default with `*`
- `egdo project use NAME` changes the default directly
- `egdo project remove NAME` unregisters a project without deleting its files

Removal asks for confirmation in a terminal; use `--force` for non-interactive use. The only
configured project cannot be removed. Removing the default makes the first remaining project
the new default.

For normal commands, egdo selects a project in this order: an explicit `-P/--project`, the
nearest `.egdo.toml` found from the current directory upward, then the global default.

Use `-P/--project` for a one-time selection without changing the default:

```bash
egdo -P Minecraft list
```

Create new projects with `egdo init NAME`.

## `egdo add`

Add a task to today’s active list.

```bash
egdo add
egdo add "Call dentist"
egdo add -p important -t work "Submit application"
egdo add --parent 6 "Add tests"
egdo add --done "Call dad"
```

Without task text, `egdo add` opens an interactive form for the description, tag, priority,
and schedule. Supplying text adds the task directly to today.

- `-t/--tag TAG` assigns a tag
- `-p/--priority LEVEL` sets `important` or `normal`
- `--parent ID` creates a subtask beneath an active task
- `--done` records the new task as already completed

## `egdo list`

Show active and scheduled tasks for the current project.

```bash
egdo
egdo list
egdo list -t chores
```

Running `egdo` with no command is the same as `egdo list`. Task IDs remain consistent across
the normal and filtered list views.

- `-t/--tag TAG` filters by tag
- `--future` shows only scheduled tasks
- `--completed` shows only tasks completed today

`--future` and `--completed` cannot be combined; either can be combined with `--tag`.

## `egdo list --completed`

Show tasks completed today, optionally filtered by tag:

```bash
egdo list --completed
egdo list --completed -t chores
```

## `egdo list --future`

Show future tasks grouped by scheduled date, optionally filtered by tag:

```bash
egdo list --future
egdo list --future -t chores
```

The displayed IDs are the same IDs used by the normal task commands.

## `egdo list --all-projects`

Show tasks from every configured project:

```bash
egdo list --all-projects
```

This view is grouped by project and strictly read-only. IDs remain local to each project;
select a project before changing one of its tasks, for example `egdo -P Minecraft done 2`.
It cannot be combined with `-P/--project` or another list filter.

## `egdo done`

Complete one or more tasks:

```bash
egdo done
egdo done 1
egdo done 1 3 12
```

Without IDs, `egdo done` opens an interactive multi-select picker. Otherwise, it completes
the supplied active or future task IDs directly.

## `egdo edit`

Choose and edit a task, or supply its ID and replacement text:

```bash
egdo edit
egdo edit 2
egdo edit 2 "Buy oat milk"
```

With no ID, `egdo edit` opens a task picker. With an ID but no replacement text, it prompts
only for the new text. Editing replaces the complete task text, including any tag or priority.

## `egdo move`

Move tasks to today or a future date:

```bash
egdo move
egdo move tomorrow
egdo move 2 tomorrow
egdo move 7 today
egdo move 1 6 7 tomorrow
```

Missing task IDs or a destination are collected interactively without discarding supplied
values. Dates accept `today`, `tomorrow`, `+N`, a weekday, or `YYYY-MM-DD`; destinations
cannot be in the past.

## `egdo delete`

Delete one or more tasks:

```bash
egdo delete
egdo delete 2
egdo delete 1 6 7
```

Without IDs, `egdo delete` opens a multi-select picker and asks for confirmation. Deletion
removes tasks from the archive rather than recording them as completed.

## `egdo tag`

Set, replace, or remove task tags:

```bash
egdo tag
egdo tag 3
egdo tag 3 chores
egdo tag 1 6 7 chores
egdo tag 3 6 7 --remove
```

Missing task IDs or a tag are collected interactively. Setting a tag replaces the existing
tag; `--remove` clears it.

## `egdo priority`

Mark tasks as important or return them to normal:

```bash
egdo priority
egdo priority 3 important
egdo priority 1 6 7 important
egdo priority 3 normal
```

Missing task IDs or a priority are collected interactively. The available levels are
`important` and `normal`.

## `egdo note`

Add a note for today:

```bash
egdo note
egdo note "Need to test villager trading setup"
```

Without text, `egdo note` opens `$VISUAL`, then `$EDITOR`, falling back to `vi`. Multiline
Markdown is preserved, and saving an empty buffer cancels without writing.
