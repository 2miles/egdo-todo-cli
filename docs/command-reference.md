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
egdo add "[chores] Do the dishes"
egdo add "[personal][chores][home] Do the dishes"
egdo add --done "Call dad"
```

- uses today by default
- creates the monthly file and day section if they do not exist
- first performs rollover for unfinished tasks from the most recent earlier day
- preserves any leading bracket tags as plain text in the task body
- `--done` creates the task already completed

## `egdo list`

List active tasks for today.

```bash
egdo
egdo list
egdo list --tag chores
```

- running bare `egdo` is the same as `egdo list`
- uses today by default
- first performs rollover for unfinished tasks from the most recent earlier day
- shows only incomplete tasks
- `--tag` filters by leading bracket tags such as `[chores]` or `[home]`
- numbers tasks so you can complete them with `done`, `edit`, `delete`, or `tag`

Example output:

```text
Thu, Apr 3rd
────────────────────────────────────────
1. [chores] Buy milk (Thu, Apr 3rd)
2. Call dentist (Thu, Apr 3rd)
```

## `egdo done`

Mark a numbered active task complete in today’s file.

```bash
egdo done 1
```

- uses today by default
- completes by the numeric index shown in `egdo list`
- keeps the completed task in that day’s file as part of the archive

## `egdo edit`

Edit a numbered active task in today’s file.

```bash
egdo edit 2 "Buy oat milk"
egdo edit 1 "[chores] Pick up detergent"
```

- uses today by default
- edits by the numeric index shown in `egdo list`
- updates only the task text
- preserves the original created date suffix such as `(04-05)`
- can be used to rewrite tags inline if you want to replace the task text completely

## `egdo delete`

Delete a numbered active task from today’s file.

```bash
egdo delete 2
```

- uses today by default
- deletes by the numeric index shown in `egdo list`
- removes the task entirely instead of marking it complete

## `egdo tag`

Add one or more tags to a numbered active task in today’s file.

```bash
egdo tag 3 chores
egdo tag 3 chores home
```

- uses today by default
- updates the task by the numeric index shown in `egdo list`
- stores tags as leading bracket groups such as `[chores][home]`
- ignores duplicate tags and normalizes tag names to lowercase

## `egdo note`

Append a note to today’s `### Notes` section.

```bash
egdo note "Need to test villager trading setup"
```

- uses today by default
- creates the monthly file and day section if they do not exist
- appends each new note as a new paragraph in that day’s Notes section

## `egdo color`

Set the terminal color for a tag.

```bash
egdo color chores
egdo color chores --style green_yellow
```

- normalizes the tag name to lowercase
- opens an interactive up/down picker by default so you can see the available colors before saving
- supports `j` and `k` in addition to the arrow keys
- saves the selected Rich style in `[tag_colors]` in the config file
- `--style` skips the picker and writes the provided Rich style directly

Available Rich colors: https://rich.readthedocs.io/en/stable/appendix/colors.html

## Behavior Notes

### Carry-Forward

When you access a new day with `add`, `list`, `done`, `edit`, `delete`, or `tag`, `egdo` moves unfinished tasks from the most recent earlier day into the current day.

That means:

- incomplete tasks do not stay stranded in old files
- completed tasks stay where they were finished
- your archive reflects when work was actually done

Rollover is idempotent, so repeating `list` for the same day does not duplicate tasks.

### Tags

- leading bracket groups are treated as tags for filtering
- `[personal][chores][home] Do the dishes` has tags `personal`, `chores`, and `home`
- brackets later in the task text are treated as normal text
- tag colors are assigned once and stored in config so they stay stable across lists

### Normalization

You can manually add simple checklist items like:

```markdown
- [ ] Pick up prescription
- [x] Paid invoice
```

On the next read/write command, `egdo` normalizes them into the standard task format and fills in the created date from the day section if needed.
