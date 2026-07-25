# The Complete egdo Guide

This is the practical handbook for using `egdo`: what to type, how its task list behaves,
how priorities and colors work, and how to use the same files from Obsidian.

For a compact description of every argument, see the
[command reference](command-reference.md).

## The Everyday Cheat Sheet

```bash
# See everything
egdo

# Add tasks
egdo add "Buy milk"
egdo add -t errands "Buy milk"
egdo add -p high -t work "Submit application"

# Act on the numbers shown by `egdo`
egdo done 3
egdo edit 3 "Buy oat milk"
egdo delete 3
egdo move 3 tomorrow

# Do the same thing to several tasks
egdo done 1 6 7
egdo delete 1 6 7
egdo move 1 6 7 friday
egdo priority 1 6 7 high

# Manage tags
egdo tag 3 chores home
egdo tag 3 6 7 --remove work

# See completed or scheduled work
egdo finished
egdo list --future
```

Running `egdo` by itself is the same as running `egdo list`.

## The Basic Mental Model

`egdo` shows one numbered list containing three groups:

- **Today** — tasks created today
- **Old** — unfinished tasks carried forward from an earlier day
- **Future** — tasks scheduled after today

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

Add a plain task:

```bash
egdo add "Call the dentist"
```

Add one or more tags by repeating `-t`:

```bash
egdo add -t health "Call the dentist"
egdo add -t home -t chores "Clean the kitchen"
```

Add a priority with `-p`:

```bash
egdo add -p critical "Renew registration today"
egdo add -p high -t work "Submit application"
```

You can combine priority, tags, and task text in any order accepted by the command:

```bash
egdo add -p high -t work -t money "Send invoice"
```

Add something that is already finished when you want it recorded in the archive:

```bash
egdo add --done "Called Dad"
```

You may also type egdo's Markdown prefixes yourself:

```bash
egdo add "!P2! {WORK} {MONEY} Send invoice"
```

Using `-p` and `-t` is usually easier and avoids formatting mistakes.

## Completing, Editing, and Deleting

Complete one task or several tasks at once:

```bash
egdo done 3
egdo done 1 3 12
```

Completed tasks remain in the Markdown archive. They can be viewed with:

```bash
egdo finished
egdo finished -t work
```

Edit one task's full text:

```bash
egdo edit 2 "Buy oat milk"
```

`edit` replaces the task text, so include any priority or tags you want to retain when
rewriting them inline. For changing only tags or priority, use the dedicated commands.

Delete tasks when you do not want them recorded as completed:

```bash
egdo delete 2
egdo delete 1 6 7
```

## Tags

Tags describe the area or context of a task. Examples include `work`, `money`, `home`,
`minecraft`, `movies`, and `errands`.

Add tags to existing tasks:

```bash
egdo tag 3 work
egdo tag 3 chores home
egdo tag 1 6 7 work
```

When adding tags, the leading numbers are task indexes and the remaining words are tags.

Remove one or more tags:

```bash
egdo tag 3 --remove work
egdo tag 3 6 7 --remove work
egdo tag 3 6 7 --remove work money
```

Filter a view by tag:

```bash
egdo list -t work
egdo finished -t work
```

Tags are case-insensitive. `work`, `WORK`, and `{WORK}` all refer to the same tag. In the
Markdown files they are stored as leading brace groups such as `{WORK} {MONEY}`.

## Priorities

Priority 1 is the most urgent; priority 4 is the least urgent.

| Level | Name | Terminal meter | Meaning |
| --- | --- | --- | --- |
| P1 | `critical` | `!!!` | Needs immediate attention |
| P2 | `high` | `.!!` | Important |
| P3 | `normal` | `..!` | Normal priority |
| P4 | `low` | `...` | Low priority |

Set the priority of one or more existing tasks:

```bash
egdo priority 3 critical
egdo priority 1 6 7 high
egdo priority 4 low
```

Names and numbers are interchangeable:

```bash
egdo priority 3 1
egdo priority 3 critical
```

Clear an explicit priority with any of these values:

```bash
egdo priority 3 none
egdo priority 3 clear
egdo priority 3 off
```

A task without an explicit priority still displays as low (`...`). This is only a visual
default; egdo does not add `!P4!` to its Markdown unless you explicitly assign P4.

The dots in `.!!`, `..!`, and `...` are gray placeholders. In Markdown, explicit
priorities are stored as `!P1!` through `!P4!`.

## Scheduling Future Tasks

Move one or more tasks out of today's active list:

```bash
egdo move 2 tomorrow
egdo move 1 6 7 +3
egdo move 2 friday
egdo move 2 2026-08-15
```

Accepted date forms are:

- `tomorrow`
- `+N`, such as `+3` for three days from today
- a weekday name or abbreviation, such as `friday` or `fri`
- an ISO date in `YYYY-MM-DD` form

A weekday always means its next occurrence, not today. Destinations must be in the future.

See only scheduled tasks:

```bash
egdo list --future
```

Bring future tasks back to today:

```bash
egdo unmove 12
egdo unmove 10 12 15
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

## Tag and Priority Colors

Open the visual color picker for a tag:

```bash
egdo color --tag work
```

Inside the picker:

- use Up/Down or `k`/`j` to move
- press Enter to save
- press `q` or Escape to cancel

Open the same picker for a priority:

```bash
egdo color --priority high
```

If you already know a Rich style, skip the picker:

```bash
egdo color --tag work --style blue
egdo color --tag urgent --style "bold white on red"
egdo color --priority critical --style "bold white on red"
```

Apply the same style to several tags or priorities:

```bash
egdo color --tag work career job --style blue
egdo color --priority high critical --style "bold red"
```

Copy an existing tag's exact style without knowing its color name:

```bash
egdo color --tag career --copy-from work
egdo color --tag career job consulting --copy-from work
```

`--style` and `--copy-from` cannot be used together. The source for `--copy-from` must
already have a saved tag color.

Rich supports named colors plus modifiers such as `bold`, foreground/background pairs,
and other styles. Browse the full list at:

<https://rich.readthedocs.io/en/stable/appendix/colors.html>

## A Practical Color System

Priority color works best for urgency, while tag color works best for category. This
keeps a red work tag from accidentally making every work task look critical.

One possible tag scheme is:

- work and career: blues
- money and bills: greens or golds
- home and chores: warm neutrals
- health: cyan or teal
- fun, games, and movies: purples or pinks
- errands: orange or tan

Treat this as a starting point. A smaller, consistent palette is usually easier to scan
than giving every tag a dramatically different color.

## How Rollover Works

When you first use egdo on a newer day, unfinished tasks from earlier days move into the
new day. Their original creation dates are preserved, which is why they appear under
**Old** and still show an earlier date.

Completed tasks stay on the day where they were completed. Notes also stay on their
original days. Repeatedly running `egdo` does not duplicate rolled-over tasks.

Future tasks are different: they remain attached to their scheduled dates until that date
arrives, you move them again, or you unmove them.

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

- [ ] !P2! {WORK} Send invoice (07-24)
- [x] {HOME} Replace air filter (07-24)

### Notes

Remember to compare the new electricity rate.
```

The final `(MM-DD)` records when a task was originally created. It is not the task's
scheduled date.

## Using egdo with Obsidian

Point `egdo init --root` at an `egdo` directory inside your Obsidian vault. The monthly
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
- adding leading tags such as `{WORK}`
- adding a leading priority such as `!P2!`
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

[tag_colors]
work = "blue"
money = "green_yellow"

[priority_styles]
p1 = "bold white on red"
p2 = "bold orange1"
p3 = "yellow"
p4 = "grey50"
```

Your Markdown vault contains the important task and note history. The config contains the
root location and terminal color preferences. Back up or sync both if you want identical
colors after setting up egdo on another computer.

## “How Do I…?” Index

| I want to… | Command |
| --- | --- |
| see my tasks | `egdo` |
| add a task | `egdo add "Task"` |
| add a tagged task | `egdo add -t work "Task"` |
| add priority and a tag together | `egdo add -p high -t work "Task"` |
| complete several tasks | `egdo done 1 6 7` |
| delete several tasks | `egdo delete 1 6 7` |
| reschedule several tasks | `egdo move 1 6 7 tomorrow` |
| add one tag to several tasks | `egdo tag 1 6 7 work` |
| remove a tag from several tasks | `egdo tag 1 6 7 --remove work` |
| set several priorities | `egdo priority 1 6 7 high` |
| clear a priority | `egdo priority 3 none` |
| see completed tasks | `egdo finished` |
| see only future tasks | `egdo list --future` |
| bring a future task back | `egdo unmove 12` |
| choose a tag color visually | `egdo color --tag work` |
| copy another tag's color | `egdo color --tag career --copy-from work` |
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
egdo color --help
```

When this guide and the program disagree, `egdo COMMAND --help` reflects the installed
version you are actually running.
