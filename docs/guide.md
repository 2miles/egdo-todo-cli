# The Complete egdo Guide

This is the practical handbook for using `egdo`: what to type, how its task list behaves,
how priorities and tags work, and how to use the same files from Obsidian.

For a compact description of every argument, see the
[command reference](command-reference.md).

## The Everyday Cheat Sheet

```bash
# See everything
egdo

# Add tasks
egdo add "Buy milk"
egdo add -t errands "Buy milk"
egdo add -p important -t work "Submit application"

# Act on the numbers shown by `egdo`
egdo done 3
egdo edit 3 "Buy oat milk"
egdo delete 3
egdo move 3 tomorrow

# Do the same thing to several tasks
egdo done 1 6 7
egdo delete 1 6 7
egdo move 1 6 7 friday
egdo priority 1 6 7 important

# Manage tags
egdo tag 3 chores
egdo tag 3 6 7 --remove

# See completed or scheduled work
egdo list --completed
egdo list --future
```

Running `egdo` by itself is the same as running `egdo list`.

## The Basic Mental Model

`egdo` shows one numbered list containing three groups:

- **Today** — tasks created today
- **Carried forward** — unfinished tasks from an earlier day, ordered newest first
- **Future date sections** — tasks scheduled after today, grouped by their date

The numbers are global. If a future task is number 12, use `12` with the normal commands:

```bash
egdo done 12
egdo edit 12 "New wording"
egdo delete 12
```

`egdo list --future` is only a filtered view. Its task numbers are the same ones shown by `egdo`,
so you do not have to learn a second indexing system.

Indexes can change whenever the list changes. Run `egdo` again before acting on an old
number if you have added, completed, moved, or deleted tasks since you last viewed it.

## Adding Tasks

Open the guided add form:

```bash
egdo add
```

After the task-text prompt, full-screen pickers handle the tag, priority, and scheduling.
Use Up/Down or j/k to move and Enter to confirm. In the tag picker, Space selects the
current tag and n creates a new one. No tag is an explicit default choice. Priority defaults to
normal and scheduling defaults to today. The custom schedule option accepts `tomorrow`,
`+3`, weekday names, and `YYYY-MM-DD` dates. Press q or Escape to cancel a picker.

Add a plain task:

```bash
egdo add "Call the dentist"
```

Add one optional tag with `-t`:

```bash
egdo add -t health "Call the dentist"
egdo add -t chores "Clean the kitchen"
```

Add a priority with `-p`:

```bash
egdo add -p important "Renew registration today"
egdo add -p important -t work "Submit application"
```

You can combine priority, a tag, and task text in any order accepted by the command:

```bash
egdo add -p important -t work "Send invoice"
```

Add something that is already finished when you want it recorded in the archive:

```bash
egdo add --done "Called Dad"
```

You may also type egdo's Markdown prefixes yourself:

```bash
egdo add "! {WORK} Send invoice"
```

Using `-p` and `-t` is usually easier and avoids formatting mistakes.

## Completing, Editing, and Deleting

Complete one task or several tasks at once:

```bash
egdo done
egdo done 3
egdo done 1 3 12
```

With no IDs, `egdo done` opens a multi-select picker containing the global task list.
Use Up/Down or j/k to move, Space to toggle, Enter to complete, and q or Escape to
cancel. Selecting a parent visibly selects its descendants through cascading behavior.

Completed tasks remain in the Markdown archive. They can be viewed with:

```bash
egdo list --completed
egdo list --completed -t work
```

Edit one task's full text:

```bash
egdo edit 2 "Buy oat milk"
```

`edit` replaces the task text, so include any priority or tag you want to retain when
rewriting it inline. For changing only the tag or priority, use the dedicated commands.

Delete tasks when you do not want them recorded as completed:

```bash
egdo delete 2
egdo delete 1 6 7
```

## Nested Tasks

Create children with `--parent`:

```bash
egdo add "Build finance dashboard"
egdo add --parent 1 "Add tests"
egdo add --parent 1a "Test missing values"
```

They are stored as ordinary nested Markdown checkboxes:

```markdown
- [ ] Build finance dashboard (07-27)
  - [ ] Add tests (07-27)
    - [ ] Test missing values (07-27)
```

The terminal IDs describe the hierarchy. The numeric part remains aligned with its
parent, the suffix grows to the right, and the priority markers occupy their own fixed
column:

```text
 1.                   Build finance dashboard
 1a.                  · Add tests
 1a.a.                ·   Test missing values
10.                   Another top-level task
10a.                  · Its child
```

This makes the `1` in `1`, `1a`, and `1a.a` line up vertically. Task text receives two
additional spaces of indentation at each nesting level.

Nesting is limited to three total levels and 26 direct children per parent. Completing,
deleting, moving, tagging, or prioritizing a task applies to its entire subtree.
Editing changes only the selected task's wording. Acting directly on a child affects that
child and its descendants, not its parent or siblings.

## Tags

Tags describe the area or context of a task. Examples include `work`, `money`, `home`,
`minecraft`, `movies`, and `errands`.

Set or replace the tag on existing tasks:

```bash
egdo tag 3 work
egdo tag 1 6 7 work
```

The leading values are task indexes and the final value is the tag. A task may have zero
or one tag, so setting a tag replaces its current one.

Remove the tag:

```bash
egdo tag 3 --remove
egdo tag 3 6 7 --remove
```

Filter a view by tag:

```bash
egdo list -t work
egdo list --completed -t work
```

Tags are case-insensitive. `work`, `WORK`, and `{WORK}` all refer to the same tag. In the
Markdown files it is stored as one leading brace group such as `{WORK}`.
Only the first leading brace group is interpreted as a tag. Any later `{...}` groups are
preserved as ordinary task-description text.

## Priority

Priority is deliberately binary. Important tasks show `●` in the terminal; normal tasks
leave that column empty. The marker uses the terminal's normal foreground color.

Set the priority of one or more existing tasks:

```bash
egdo priority 3 important
egdo priority 1 6 7 important
egdo priority 4 normal
```

Important tasks store a leading `!` in Markdown. Normal tasks store no priority marker.

## Moving Tasks Between Dates

Move one or more tasks to a future date:

```bash
egdo move 2 tomorrow
egdo move 1 6 7 +3
egdo move 2 friday
egdo move 2 2026-08-15
```

Accepted date forms are:

- `tomorrow`
- `today`, when bringing a future task back
- `+N`, such as `+3` for three days from today
- a weekday name or abbreviation, such as `friday` or `fri`
- an ISO date in `YYYY-MM-DD` form

A weekday always means its next occurrence, not today. Destinations cannot be in the past.

See only scheduled tasks:

```bash
egdo list --future
```

Bring future tasks back to today with the same command:

```bash
egdo move 12 today
egdo move 10 12 15 today
```

The ordinary `done`, `edit`, `delete`, `move`, `tag`, and `priority` commands work on
future tasks using their global indexes. `egdo list --future` is view-only; actions are always
top-level commands.

## Notes

Append a paragraph to today's Notes section:

```bash
egdo note "Need to test villager trading setup"
```

Notes are not tasks: they do not receive indexes, roll forward, or appear in task views.
They remain alongside that day's tasks in the monthly Markdown file.

## Terminal Tag Display

Markdown stores tags with braces, such as `{WORK}`. Terminal lists omit the braces and
render every tag as an uppercase, dim cyan label. This keeps tags visually consistent
while priorities retain the stronger urgency signal.

## How Rollover Works

When you first use egdo on a newer day, unfinished tasks from earlier days move into the
new day. Their original creation dates are preserved, which is why they appear under
**Carried forward** and still show an earlier date.

Completed tasks stay on the day where they were completed. Notes also stay on their
original days. Repeatedly running `egdo` does not duplicate rolled-over tasks.

Future tasks are different: they remain attached to their scheduled dates until that date
arrives or you move them again, including back to today.

## The Markdown Files

The configured root uses this layout:

```text
<root>/YEAR/YEAR_MM_mon.md
```

For example:

```text
egdo/2026/2026_07_jul.md
```

Each file contains daily sections:

```markdown
## Jul-24 Fri

### Tasks

- [ ] ! {WORK} Send invoice (07-24)
- [x] {HOME} Replace air filter (07-24)

### Notes

Remember to compare the new electricity rate.
```

The final `(MM-DD)` records when a task was originally created. It is not the task's
scheduled date.

## Using egdo with Obsidian

Point `egdo config --root` at an `egdo` directory inside your Obsidian vault. The monthly
files then remain normal Obsidian notes and sync to the mobile app using whichever sync
method you use for the rest of the vault.

For quick phone access, bookmark the current month's note in Obsidian. At the beginning
of a new month, replace that bookmark with the new monthly note. This opens the actual
task file directly instead of opening an intermediate list.

An Obsidian Base is optional. It is useful as an archive browser for all egdo month files,
but a Base bookmark opens the Base result list first. If the Base currently contains only
one month file, a direct bookmark to that file is faster. A useful long-term setup is:

- direct bookmark: the current month, for daily phone access
- Base: every egdo Markdown file, for browsing and searching history

Editing from Obsidian is supported. Keep task items in the day's `### Tasks` section and
notes in `### Notes`. Safe manual changes include:

- editing task wording
- checking or unchecking a checkbox
- adding a normal Markdown checklist item
- adding a leading tag such as `{WORK}`
- adding a leading `!` to mark a task important
- editing notes

Avoid changing the day header format (`## Jul-24 Fri`) or manually changing the trailing
creation-date suffix. If you add a checklist item without a suffix, egdo fills it from the
day section the next time it normalizes that file.

## Configuration and Backup

The config file is:

```text
~/.config/egdo/config.toml
```

A typical config looks like:

```toml
root = "/Users/you/Notes/egdo"
```

Create or update it with `egdo config --root ~/Notes/egdo`. This changes only the
top-level `root` setting and saves the previous config as `config.toml.bak`. It does not
move or delete task files; changing the root only changes where `egdo` looks for them.

Your Markdown vault contains the important task and note history. The config contains the
root location. Back up or sync both if you
want identical behavior after setting up egdo on another computer.

## “How Do I…?” Index

| I want to… | Command |
| --- | --- |
| see my tasks | `egdo` |
| add a task | `egdo add "Task"` |
| add a tagged task | `egdo add -t work "Task"` |
| add priority and a tag together | `egdo add -p important -t work "Task"` |
| complete several tasks | `egdo done 1 6 7` |
| delete several tasks | `egdo delete 1 6 7` |
| reschedule several tasks | `egdo move 1 6 7 tomorrow` |
| set one tag on several tasks | `egdo tag 1 6 7 work` |
| remove a tag from several tasks | `egdo tag 1 6 7 --remove` |
| mark several tasks important | `egdo priority 1 6 7 important` |
| return a task to normal | `egdo priority 3 normal` |
| see completed tasks | `egdo list --completed` |
| see only future tasks | `egdo list --future` |
| bring a future task back | `egdo move 12 today` |
| add a note | `egdo note "Note text"` |
| see help for one command | `egdo COMMAND --help` |

## Getting Help

Show the short overview:

```bash
egdo --help
```

Show detailed help for a command:

```bash
egdo add --help
egdo move --help
```

When this guide and the program disagree, `egdo COMMAND --help` reflects the installed
version you are actually running.
