# Command Reference

## Overview

Running `egdo` with no command is a shortcut for `egdo list`.

Successful task-changing commands clear and redraw the current list when run in an
interactive terminal, with the confirmation shown above it. Piped or redirected output
is not cleared and receives only the confirmation line(s).

## `egdo init`

Creates the config file at:

```text
~/.config/egdo/config.toml
```

Example:

```bash
egdo init --root /path/to/egdo
```

Arguments:

- `--root` required absolute or user-relative path where `egdo` stores its yearly files

## `egdo add`

Add a task to today’s active list.

```bash
egdo add
egdo add "Call dentist"
egdo add -t chores "Do the dishes"
egdo add -p important -t work "Submit application"
egdo add --parent 6 "Add tests"
egdo add --parent 6a "Test missing values"
egdo add --done -t errands "Call the DMV"
egdo add "{CHORES} Do the dishes"
egdo add --done "Call dad"
```

- uses today by default
- when task text is omitted, opens an interactive form for text, one optional tag, priority, and schedule
- the form uses arrow or Vim navigation; Space selects a tag and Enter confirms a screen
- No tag is explicit and mutually exclusive with a selected tag; pressing n creates a tag
- the form accepts `today`, `tomorrow`, `+N`, weekdays, and `YYYY-MM-DD` schedules
- creates the monthly file and day section if they do not exist
- first performs rollover for unfinished tasks from the most recent earlier day
- `-t` or `--tag` prepends one tag without requiring Markdown tag syntax
- `-p` or `--priority` accepts `important` or `normal`
- preserves one leading tag in the task body and normalizes it to `{UPPERCASE}`
- `--done` creates the task already completed
- `--parent ID` inserts a child beneath a task scheduled for today
- nesting is limited to three total levels: `6`, `6a`, and `6a.a`

## `egdo list`

List active tasks for today.

```bash
egdo
egdo list
egdo list -t chores
```

- running bare `egdo` is the same as `egdo list`
- uses today by default
- first performs rollover for unfinished tasks from the most recent earlier day
- shows incomplete active tasks grouped as `Today` and `Carried forward`; carried tasks are ordered by creation date, newest first
- also shows future tasks grouped by scheduled date, with tomorrow labeled explicitly
- `-t` or `--tag` filters by leading tags such as `{CHORES}` or `{HOME}`
- `--future` shows only tasks scheduled after today and can be combined with `--tag`
- numbering continues across `Today`, `Carried forward`, and future date sections without restarting
- normal `done`, `edit`, `move`, `delete`, `tag`, and `priority` commands automatically route each index to the correct group
- `egdo list --future` is an optional filtered view that preserves the same global indexes

## `egdo finished`

List completed tasks for today.

```bash
egdo finished
egdo finished -t chores
```

- uses today by default
- shows only completed tasks from today
- `-t` or `--tag` filters by leading tags such as `{CHORES}` or `{HOME}`

## `egdo list --future`

List incomplete tasks scheduled after today.

```bash
egdo list --future
egdo list --future -t chores
```

- shows incomplete tasks on dates later than today
- groups tasks by their scheduled day
- preserves the global task numbers from the combined `egdo list` view
- shows each task with its original created date
- this command is view-only; use the normal top-level commands with the displayed indexes

Example output:

```text
Thu, Apr 3rd
────────────────────────────────────────
1. {CHORES} Buy milk (Thu, Apr 3rd)
2. Call dentist (Thu, Apr 3rd)
```

## `egdo priority`

Mark active tasks as important or return them to normal. New tasks default to normal.

```bash
egdo priority 3 important
egdo priority 1 6 7 important
egdo priority 3 normal
```

- accepts one or more numeric indexes shown by `egdo list`
- `important` stores a leading `!` in Markdown
- `normal` removes the priority marker
- renders an uncolored `●` for important tasks and an empty priority column for normal tasks
- the same command works for future tasks using their global indexes

## `egdo done`

Mark one or more numbered active tasks complete in today’s file.

```bash
egdo done
egdo done 1
egdo done 1 3 12
```

- uses today by default
- without IDs, opens a multi-select picker using arrows or j/k, Space, and Enter
- completes by the numeric index shown in `egdo list`
- resolves all indexes before marking anything complete, so later indexes do not shift when completing multiple tasks
- keeps the completed task in that day’s file as part of the archive

## `egdo edit`

Edit a numbered active task in today’s file.

```bash
egdo edit 2 "Buy oat milk"
egdo edit 1 "{CHORES} Pick up detergent"
```

- uses today by default
- edits by the numeric index shown in `egdo list`
- updates only the task text
- preserves the original created date suffix such as `(04-05)`
- can be used to rewrite tags inline if you want to replace the task text completely

## `egdo move`

Move one or more numbered active tasks to a future date.

```bash
egdo move 2 tomorrow
egdo move 1 6 7 tomorrow
egdo move 2 +3
egdo move 2 sunday
egdo move 2 2026-04-10
```

- uses today as the source day
- accepts one or more numeric indexes shown in `egdo list`
- physically relocates the task into the destination day section
- preserves the original created date suffix such as `(04-05)`
- accepts `tomorrow`, `+N`, weekday names, and `YYYY-MM-DD`
- weekday names mean the next occurrence of that weekday, never today
- rejects non-future destinations

## `egdo unmove`

Bring one or more future tasks back to today's active list.

```bash
egdo unmove 12
egdo unmove 10 12 15
```

- accepts the global task indexes shown by `egdo` or `egdo list --future`
- accepts only tasks that are currently scheduled after today
- preserves each task's original creation date

## `egdo delete`

Delete one or more numbered active tasks from today’s file.

```bash
egdo delete 2
egdo delete 1 6 7
```

- uses today by default
- accepts one or more numeric indexes shown in `egdo list`
- removes the task entirely instead of marking it complete

## `egdo tag`

Set, replace, or remove the tag on numbered active tasks in today’s file.

```bash
egdo tag 3 chores
egdo tag 1 6 7 chores
egdo tag 3 6 7 --remove
```

- uses today by default
- reads leading values as task indexes and the final value as one tag
- setting a tag replaces any tag already on every selected task
- `--remove` clears the tag from every selected task
- stores the tag as one leading brace group such as `{CHORES}`
- normalizes tag names case-insensitively

## `egdo note`

Append a note to today’s `### Notes` section.

```bash
egdo note "Need to test villager trading setup"
```

- uses today by default
- creates the monthly file and day section if they do not exist
- appends each new note as a new paragraph in that day’s Notes section

## Behavior Notes

### Nested tasks

- Markdown uses two spaces of indentation per nesting level
- top-level tasks use numeric IDs, children use IDs such as `6a`, and grandchildren use `6a.a`
- `done`, `delete`, `move`, `unmove`, `tag`, and `priority` cascade to descendants
- `edit` changes only the selected task while preserving its descendants
- moving a child without its parent promotes that child to the top level at its destination
- a parent may have at most 26 direct children

### Carry-Forward

When you access a new day with `add`, `list`, `done`, `edit`, `move`, `delete`, or `tag`, `egdo` moves unfinished tasks from the most recent earlier day into the current day.

That means:

- incomplete tasks do not stay stranded in old files
- completed tasks stay where they were finished
- your archive reflects when work was actually done

Rollover is idempotent, so repeating `list` for the same day does not duplicate tasks.

### Tags

- one leading brace group is treated as the task's tag for filtering
- you can create a tag either with `egdo add -t chores "Task"` or by typing `{CHORES} Task` directly in Markdown
- only the first leading brace group is a tag; later brace groups remain ordinary task text
- braces later in the task text are treated as normal text
- terminal lists show the tag without braces as an uppercase, dim cyan label in a fixed-width column; long labels are shortened only for display

### Normalization

You can manually add simple checklist items like:

```markdown
- [ ] Pick up prescription
- [x] Paid invoice
```

On the next read/write command, `egdo` normalizes them into the standard task format and fills in the created date from the day section if needed.
