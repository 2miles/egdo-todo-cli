# Egdo Guide

This guide teaches the ideas and everyday workflows behind `egdo`. Read it in order if you
are getting started, or jump to a topic when you want to understand how a feature fits into
the rest of the system. For exact command syntax and options, use the
[command reference](command-reference.md).

## Contents

- [Getting Started](#getting-started)
- [How Egdo Organizes Your Work](#how-egdo-organizes-your-work)
- [Multiple Projects](#multiple-projects)
- [Adding Tasks](#adding-tasks)
- [Completing, Editing, and Deleting](#completing-editing-and-deleting)
- [Nested Tasks](#nested-tasks)
- [Tags](#tags)
- [Priority](#priority)
- [Moving Tasks Between Dates](#moving-tasks-between-dates)
- [Notes](#notes)
- [Interactive Commands](#interactive-commands)
- [How Rollover Works](#how-rollover-works)
- [The Markdown Files](#the-markdown-files)
- [Using Egdo with Obsidian](#using-egdo-with-obsidian)
- [Files, Configuration, and Recovery](#files-configuration-and-recovery)
- [Getting Help](#getting-help)

## Getting Started

Initialize a journal from the directory where its related notes live:

```bash
cd ~/Notes
egdo init Main
```

Add a task, view the list, and complete it using the number shown:

```bash
egdo add "Buy milk"
egdo
egdo done 1
```

That is the core workflow. `egdo init` creates a local project marker and an `egdo/`
archive beside it. Adding the task creates the current monthly Markdown file; completing it
keeps it in that file as history.

Most task-changing commands also open a guided interface when you omit their arguments. For
example, `egdo add` guides you through a new task and `egdo done` lets you choose tasks from
the current list.

## How Egdo Organizes Your Work

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

## Multiple Projects

Each project is an independent journal with its own tasks, notes, numbering, monthly files,
and history. Initialize another one from the directory where it belongs:

```bash
cd ~/Notes/topics/gaming/minecraft
egdo init Minecraft
```

When you run egdo inside that directory or one of its descendants, the nearest local project
marker selects Minecraft automatically. Outside an initialized directory, egdo uses the
global default. You can choose that default interactively with `egdo project`, or change it
directly:

```bash
egdo project use Minecraft
```

Use another project once without changing the default:

```bash
egdo -P Minecraft list
```

When a journal no longer needs to appear in the project registry, unregister it with:

```bash
egdo project remove Demo
```

This removes only the registration—not its local marker or Markdown archive—so the project
can be initialized again later. Egdo refuses to remove the only configured project.

To see every project together:

```bash
egdo list --all-projects
```

The combined view is read-only. Its task IDs remain local to their displayed project, so
select that project before acting on one, for example `egdo -P Minecraft done 2`.

`--all-projects` cannot be combined with `-P/--project`, `--future`, `--completed`, or
`--tag`.

## Adding Tasks

Run `egdo add` by itself for the guided form. It asks for the task text, then lets you choose
a tag, priority, and schedule. No tag, normal priority, and today are the defaults.

```bash
egdo add
```

When you already know what you want, add it directly. A task may have one tag and may be
marked important:

```bash
egdo add "Call the dentist"
egdo add -p important -t work "Send invoice"
```

Use `--done` when something is already finished but still belongs in the history:

```bash
egdo add --done "Called Dad"
```

Egdo creates the current month and day only when there is something to record, so adding the
first task or note never produces empty intervening dates.

## Completing, Editing, and Deleting

The numbers in the list are handles for acting on tasks. Pass one or several to complete them,
or omit the numbers to choose interactively:

```bash
egdo done
egdo done 3
egdo done 1 3 12
```

Completion keeps the task in the archive instead of erasing it. Today’s completed work is
available as a filtered view:

```bash
egdo list --completed
```

Editing changes the full task text while preserving its original creation date:

```bash
egdo edit
egdo edit 2 "Buy oat milk"
```

Use the dedicated `tag` and `priority` commands when you only want to change those properties.
Delete a task only when you do not want it retained as completed history:

```bash
egdo delete
egdo delete 2
```

## Nested Tasks

Use a task’s displayed ID as `--parent` to break work into smaller steps:

```bash
egdo add "Build finance dashboard"
egdo add --parent 1 "Add tests"
egdo add --parent 1a "Test missing values"
```

The resulting IDs express the hierarchy as `1`, `1a`, and `1aa`, while the archive remains
ordinary nested Markdown:

```markdown
- [ ] Build finance dashboard (07-27)
  - [ ] Add tests (07-27)
    - [ ] Test missing values (07-27)
```

Nesting is limited to three total levels and 26 direct children per parent. Completing,
deleting, moving, tagging, or prioritizing a task applies to its entire subtree.
Editing changes only the selected task's wording. Acting directly on a child affects that
child and its descendants, not its parent or siblings. Moving a child without its parent
promotes it to the top level at the destination.

## Tags

Tags describe the area or context of a task. Examples include `work`, `money`, `home`,
`minecraft`, `movies`, and `errands`.

Add a tag with a task, change it later, or filter the list around it:

```bash
egdo add -t work "Send invoice"
egdo tag 3 work
egdo tag 3 --remove
egdo list -t work
```

A task has at most one tag, so setting another replaces the current one. The same operation
can be applied to several task IDs at once. Tags are case-insensitive: `work`, `WORK`, and
`{WORK}` all refer to the same tag.

In Markdown, the tag is stored as a leading brace group such as `{WORK}`. Only the first
leading brace group is treated as a tag; braces elsewhere remain part of the description.

Terminal lists omit the braces and render tags as uppercase, dim cyan labels. Long tags are
shortened only for display; their stored text remains unchanged.

## Priority

Priority is deliberately binary. Important tasks show `●` in the terminal; normal tasks
leave that column empty. Set it while adding a task or change it later:

```bash
egdo add -p important "Renew registration"
egdo priority 3 important
egdo priority 3 normal
```

Important tasks store a leading `!` in Markdown. Returning one to normal removes that marker.
As with tags, you can change several task IDs in one operation.

## Moving Tasks Between Dates

Move a task when you want it attached to a particular date rather than carried forward each
day:

```bash
egdo move
egdo move 2 tomorrow
egdo move 2 friday
egdo move 1 6 7 +3
```

Dates can be written as `today`, `tomorrow`, `+N`, a weekday, or `YYYY-MM-DD`. A weekday
means its next occurrence, and destinations cannot be in the past. If you omit the task IDs,
the destination, or both, egdo asks only for what is missing.

Scheduled tasks appear in the normal list, or by themselves in the future view:

```bash
egdo list --future
```

They use the same IDs in either view and work with the ordinary task commands. Move one back
into today’s active work with:

```bash
egdo move 12 today
```

## Notes

Notes capture context that does not need to behave like a task. Run `egdo note` to write
multiline Markdown in your editor, or provide a short note directly:

```bash
egdo note
egdo note "Need to test villager trading setup"
```

Notes are not tasks: they do not receive indexes, roll forward, or appear in task views.
They remain alongside that day's tasks in the monthly Markdown file. The editor follows
`$VISUAL`, then `$EDITOR`, and falls back to `vi`; saving an empty note cancels it.

## Interactive Commands

Run `project`, `add`, `done`, `edit`, `move`, `delete`, `tag`, or `priority` without the
input it needs to open a guided prompt. Pickers share the same controls: Up/Down or j/k moves,
Space selects where applicable, and Enter continues. Press q or Escape to cancel a picker;
enter `/cancel` to leave a line prompt. The `note` command opens your editor when no text is
supplied.

## How Rollover Works

Rollover keeps unfinished work visible without filling the archive with empty dates. When
you first use egdo on a newer day, incomplete tasks from the most recent earlier day move
into today. Their original creation dates remain attached, so they appear under
**Carried forward** rather than **Today**.

Completed tasks and notes stay on the days where they were recorded. Running egdo repeatedly
on the same day does not duplicate anything.

Scheduled tasks remain on their future dates until those dates arrive or you move them again.

## The Markdown Files

Each project stores its history as one Markdown file per month:

```text
<root>/YEAR/YEAR_MM_mon.md
```

For example:

```text
egdo/2026/2026_07_jul.md
```

Each file contains sections for days with tasks or notes. Dates without content are
omitted rather than represented by empty day headers:

```markdown
## Jul-24 Fri

### Tasks

- [ ] ! {WORK} Send invoice (07-24)
- [x] {HOME} Replace air filter (07-24)

### Notes

Remember to compare the new electricity rate.
```

The checkbox records completion, `!` records priority, and `{WORK}` is the tag. The final
`(MM-DD)` is the task’s original creation date—not its scheduled date.

For a larger working example, copy the repository’s [example notes](../example-notes) and
run `egdo init Demo` inside the copy. The included archive is populated but intentionally
uninitialized, so it can be adopted without changing the repository version.

## Using egdo with Obsidian

Initialize projects inside your Obsidian vault and their `egdo/` archives become ordinary
vault folders. The monthly files can be opened, searched, linked, and synced like your other
Markdown notes.

For quick phone access, bookmark the current month’s file. An Obsidian Base is optional and
can provide a broader searchable view of the entire archive.

Editing from Obsidian is supported. Keep task items in the day's `### Tasks` section and
notes in `### Notes`. Safe manual changes include:

- Editing task wording
- Checking or unchecking a checkbox
- Adding a normal Markdown checklist item
- Adding a leading tag such as `{WORK}`
- Adding a leading `!` to mark a task important
- Editing notes

Keep checklist items under the correct `### Tasks` heading and notes under `### Notes`.
Avoid changing day headers or creation-date suffixes. If you add a plain checklist item,
egdo fills in its creation date from the surrounding day the next time it reads the file.

## Files, Configuration, and Recovery

There are two small pieces of project metadata in addition to the Markdown archive:

- `.egdo.toml` identifies the project from its local directory
- `~/.config/egdo/config.toml` records known projects and the global default

The local marker deliberately stores only identity:

```toml
project = "Minecraft"
```

A typical global config maps those identities to their archive locations:

```toml
default_project = "Main"

[projects]
"Main" = "/Users/you/Notes/egdo"
"Minecraft" = "/Users/you/Notes/topics/gaming/minecraft/egdo"
```

The archive is always the marker’s sibling `egdo/` directory. Moving the initialized
directory therefore moves the marker and archive together. The next command run inside the
moved tree finds the local archive and refreshes its registered location. If a valid marker
still exists at the old location, egdo refuses to choose between the two copies.

Initialization can safely adopt an existing `egdo/` archive and can be repeated for the same
project. It refuses conflicting local markers, project names, and registered roots. Project
names match case-insensitively while preserving their display capitalization.

Configuration changes preserve the previous file as `config.toml.bak`; they never move,
merge, or delete Markdown archives. Back up or sync both the archives and global config when
you want the same projects and default on another computer. The former
`egdo config --root` workflow is obsolete—initialize projects with `egdo init NAME` instead.

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
