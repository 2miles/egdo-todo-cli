# Command Reference

## Overview

Running `egdo` with no command is a shortcut for `egdo list`.

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
egdo add "Call dentist"
egdo add -t chores -t home "Do the dishes"
egdo add -p high -t work "Submit application"
egdo add --done -t car -t errands "Call the DMV"
egdo add "{CHORES} Do the dishes"
egdo add "{PERSONAL} {CHORES} {HOME} Do the dishes"
egdo add --done "Call dad"
```

- uses today by default
- creates the monthly file and day section if they do not exist
- first performs rollover for unfinished tasks from the most recent earlier day
- `-t` or `--tag` can be repeated to prepend tags without typing tag syntax yourself
- `-p` or `--priority` accepts `1`/`critical`, `2`/`high`, `3`/`normal`, or `4`/`low`
- preserves any leading tag groups in the task body and normalizes touched tags to `{UPPERCASE}`
- `--done` creates the task already completed

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
- shows incomplete active tasks grouped as `Today` and `Old`
- also shows future tasks grouped by scheduled date, with tomorrow labeled explicitly
- `-t` or `--tag` filters by leading tags such as `{CHORES}` or `{HOME}`
- numbering continues across `Today`, `Old`, and `Future` without restarting
- normal `done`, `edit`, `move`, `delete`, `tag`, and `priority` commands automatically route each index to the correct group
- `egdo future` is an optional filtered view that preserves the same global indexes

## `egdo finished`

List completed tasks for today.

```bash
egdo finished
egdo finished -t chores
```

- uses today by default
- shows only completed tasks from today
- `-t` or `--tag` filters by leading tags such as `{CHORES}` or `{HOME}`

## `egdo future`

List incomplete tasks scheduled after today.

```bash
egdo future
egdo future -t chores
egdo future done 1
egdo future done 1 3 7
egdo future delete 2
egdo future edit 1 "Buy oat milk"
egdo future move 2 sunday
egdo future move 1 3 7 sunday
egdo future tag 1 chores
egdo future priority 1 high
egdo future unmove 1
```

- shows incomplete tasks on dates later than today
- groups tasks by their scheduled day
- preserves the global task numbers from the combined `egdo list` view
- shows each task with its original created date
- `-t` or `--tag` filters by leading tags such as `{CHORES}` or `{HOME}`
- `future done`, `delete`, `move`, `tag`, `priority`, and `unmove` accept multiple indexes from the numbering shown by `egdo future`; `edit` remains single-task
- `future unmove` removes a task from its future day and puts it back on today’s active list
- `future move` accepts the same date forms as `egdo move`: `tomorrow`, `+N`, weekday names, and `YYYY-MM-DD`

Example output:

```text
Thu, Apr 3rd
────────────────────────────────────────
1. {CHORES} Buy milk (Thu, Apr 3rd)
2. Call dentist (Thu, Apr 3rd)
```

## `egdo priority`

Set or clear the priority of an active task.

```bash
egdo priority 3 critical
egdo priority 1 6 7 high
egdo priority 3 none
```

- accepts one or more numeric indexes shown by `egdo list`
- accepts `1`/`critical`, `2`/`high`, `3`/`normal`, and `4`/`low`
- stores the priority as a leading plain-Markdown marker such as `!P1!`
- renders priority as a three-slot meter: `!!!` (P1), `.!!` (P2), `..!` (P3), and `...` (P4), with gray dots as placeholders
- displays tasks without an explicit priority as low (`...`) without adding a marker to Markdown
- `none`, `clear`, or `off` removes the marker
- use `egdo future priority INDEX LEVEL` for a future task

## `egdo done`

Mark one or more numbered active tasks complete in today’s file.

```bash
egdo done 1
egdo done 1 3 12
```

- uses today by default
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

Add one or more tags to one or more numbered active tasks in today’s file.

```bash
egdo tag 3 chores
egdo tag 3 chores home
egdo tag 1 6 7 chores home
egdo tag 3 6 7 --remove work
```

- uses today by default
- reads leading numbers as task indexes and applies the remaining tags to all of them
- `--remove TAG...` removes one or more tags from every selected task
- stores tags as leading brace groups such as `{CHORES} {HOME}`
- ignores duplicate tags and normalizes tag names case-insensitively

## `egdo note`

Append a note to today’s `### Notes` section.

```bash
egdo note "Need to test villager trading setup"
```

- uses today by default
- creates the monthly file and day section if they do not exist
- appends each new note as a new paragraph in that day’s Notes section

## `egdo color`

Set the terminal color for a tag or priority level.

```bash
egdo color --tag chores
egdo color --tag chores --style green_yellow
egdo color --tag chores home --style green_yellow
egdo color --priority high --style "bold orange1"
egdo color --priority high critical --style "bold red"
```

- requires either `--tag TAG...` or `--priority LEVEL...`
- applies one `--style` value to every supplied tag or priority level
- normalizes tag names to lowercase
- opens an interactive up/down picker by default so you can see the available colors before saving
- supports `j` and `k` in addition to the arrow keys
- saves the selected Rich style in `[tag_colors]` in the config file
- `--style` skips the picker and writes the provided Rich style directly
- priority levels accept the same numeric and named values as `egdo priority`
- priority styles are saved as `p1` through `p4` in `[priority_styles]`
- P1–P3 control the filled exclamation slots; P4 controls every placeholder dot

Available Rich colors: https://rich.readthedocs.io/en/stable/appendix/colors.html

If `[priority_styles]` is absent, egdo uses its built-in defaults.

## Behavior Notes

### Carry-Forward

When you access a new day with `add`, `list`, `done`, `edit`, `move`, `delete`, or `tag`, `egdo` moves unfinished tasks from the most recent earlier day into the current day.

That means:

- incomplete tasks do not stay stranded in old files
- completed tasks stay where they were finished
- your archive reflects when work was actually done

Rollover is idempotent, so repeating `list` for the same day does not duplicate tasks.

### Tags

- leading brace groups are treated as tags for filtering
- you can create tags either with `egdo add -t chores -t home "Task"` or by typing `{CHORES} {HOME} Task` directly in the markdown
- `{PERSONAL} {CHORES} {HOME} Do the dishes` has tags `personal`, `chores`, and `home`
- braces later in the task text are treated as normal text
- tag colors are assigned once and stored in config so they stay stable across lists

### Normalization

You can manually add simple checklist items like:

```markdown
- [ ] Pick up prescription
- [x] Paid invoice
```

On the next read/write command, `egdo` normalizes them into the standard task format and fills in the created date from the day section if needed.
