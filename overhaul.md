The biggest gains now will come from subtraction and consistency, not more task-management features.

My strongest recommendation: make egdo feel like a calm, opinionated daily task journal—not a miniature Taskwarrior.

## Highest-priority polish

### 1. Simplify the default list

The current rendering has several competing signals:

- date header
- two separator lines
- section headers
- priority punctuation
- colored brace tags
- creation dates on every row
- another special divider before future tasks

That creates visual noise. In particular, the double separator in src/egdo/handlers.py:260 looks accidental.

I would aim for something like:

Thursday, August 13

TODAY
1 ● Submit application WORK
2 · Buy milk HOME

CARRIED FORWARD
3 ○ Call the dentist Aug 10
4 · Clean garage Aug 06

UPCOMING
Tomorrow
5 ○ Prepare meeting notes WORK

    Monday, Aug 17
    6  ·  Order replacement filter              HOME

Changes embodied there:

- One header, no full-width rule required.
- Rename Old to Carried forward; it communicates why the task is there.
- Rename Future to Upcoming.
- Show creation dates only when they convey useful age.
- Move tags to a consistent visual column when the terminal is wide enough.
- Use a restrained priority symbol instead of !!!, .!!, ..!, and ....
- Use color to reinforce meaning, never as the only way to understand it.

The punctuation meter is clever, but it requires explanation. Professional interfaces generally make their important states immediately
legible.

### 2. Reduce customization exposed as commands

The entire egdo color feature is disproportionally large for the product’s core purpose. It includes:

- tag color selection
- priority style selection
- copying styles
- interactive palettes
- Rich style names
- automatic assignment
- configuration persistence

That is considerable conceptual surface area for cosmetic configuration.

I would consider:

- Give priorities one excellent built-in palette.
- Automatically assign restrained tag colors.
- Keep manual color configuration in TOML for power users.
- Either remove egdo color or leave it undocumented until the core release is solid.

Similarly, tag_levels is useful for your particular taxonomy, but it should feel like an advanced configuration option—not a headline
feature.

### 3. Make command language consistent

A few commands describe the same concepts differently:

- done performs completion.
- finished displays completed tasks.
- move only moves into the future.
- unmove moves something back to today.

I would prefer one vocabulary:

egdo done 3
egdo completed
egdo move 3 tomorrow
egdo move 7 today

That would let you remove unmove entirely.

Potential streamlined command set:

add
list
done
edit
move
delete
tag
note
completed
config

You could also support aliases without promoting them:

- ls → list
- rm → delete
- finish → done

Avoid adding abbreviations for every command, however; discoverability matters more than shaving two characters.

## Things I would add

### Essential product-quality work

Before search, recurrence, reminders, or synchronization:

- Add a license.
- Add CI across supported Python versions.
- Fix the repo-local environment and test installation instructions.
- Test installation from a built wheel in a completely clean environment.
- Add --version.
- Add --no-color and respect the NO_COLOR environment variable.
- Ensure machine-readable errors go to stderr with reliable exit codes.
- Make writes atomic so an interruption cannot corrupt a month file.
- Detect malformed Markdown and explain the file and line involved.
- Reconcile the daily-file description in AGENT.md with the actual monthly format.
- Add a short animated demo or polished terminal screenshot to the README.
- Choose one spelling and casing convention everywhere: “Markdown,” “ID,” “todo,” dates, quotation marks, and arrows.

Those are the features that make a CLI feel trustworthy.

### A useful doctor command

Because the files are manually editable, a diagnostic command fits the product extremely well:

egdo doctor

It could check:

- configuration exists
- root directory is writable
- month files parse successfully
- task dates and nesting are valid
- no malformed task sections exist

Initially, it should only report problems. A future egdo doctor --fix could normalize safe cases after showing a preview.

### A direct file-opening command

Manual editing is one of the product’s differentiators, so make it effortless:

egdo open
egdo open today
egdo open 2026-08-12

Use $EDITOR and open the relevant monthly file at the relevant day if practical. This reinforces the product thesis instead of expanding
away from it.

### Search, but keep it modest

Search is the one missing user feature I would prioritize:

egdo search dentist
egdo search --tag work
egdo search --completed application

Your archive becomes substantially more valuable when it can answer “When did I do that?”

A simple text/tag/date search is enough. You do not need a query language.

## Things I would not add yet

Avoid these until real usage demonstrates a repeated need:

- recurring tasks
- reminders and notifications
- dependencies
- task durations
- cloud synchronization
- project management
- calendar integrations
- arbitrary custom fields
- a full-screen TUI
- plugin architecture
- natural-language parsing beyond a small documented date grammar

Recurrence looks obvious, but it introduces identity, duplication, completion, editing, and history semantics. It can easily double the
complexity of the storage model.

## Interaction improvements

The interactive forms are promising, but they should behave as one coherent system.

Currently, different pickers use variations of:

- [x]
- (x)
- >
- Space in some screens
- Enter in others
- n only in the tag picker

Standardize the visual grammar:

Add task Esc cancel

Description Submit application

Priority
○ Low
○ Normal
● High
○ Critical

Tags
◉ WORK
○ PERSONAL
○ ERRANDS + Create tag

Schedule
● Today
○ Tomorrow
○ Friday, Aug 14

Other refinements:

- Always display an explicit cancel hint.
- Use the same selected/focused symbols everywhere.
- Show a final compact preview before saving only when the operation is complex.
- Preserve supplied CLI values when opening the form.
- Avoid clearing the entire terminal after every mutation unless users opt into it; an inline refresh can be less disruptive.
- If clearing remains, add --quiet and possibly --no-refresh.

## Error presentation

Right now, top-level errors are printed as unstyled exception text. Give errors a consistent form:

egdo: cannot parse ~/Notes/egdo/2026/2026_08_aug.md:42
Nested task must follow a parent task.

Run `egdo doctor` to check the rest of the archive.

Useful errors should include:

- what failed
- where it failed
- how to correct it
- no traceback unless --debug is supplied

Destructive commands should also be slightly safer:

egdo delete 4

# Deleted “Cancel old subscription”

# Undo: egdo restore

An undo mechanism would be valuable, but atomic backup files or Git integration may be enough initially. I would not add confirmation
prompts to every deletion; that makes a CLI tedious.

## README presentation

The README should become much shorter at the top.

Suggested opening:

> egdo is a terminal task list that keeps your work in ordinary Markdown.
>
> Unfinished tasks roll into today. Completed tasks remain in the day they were finished, turning your todo list into a searchable work
> journal.

Then show:

1. One screenshot.
2. Installation.
3. Five-command quick start.
4. Example Markdown output.
5. “Why egdo instead of Taskwarrior or todo.txt?”
6. Links to the full guide and command reference.

The current README introduces nearly every command before the reader has experienced the basic loop.

## My recommended release sequence

1. Redesign the default list and simplify priority presentation.
2. Reconcile command names and remove unmove.
3. Standardize interactive picker visuals.
4. Improve parser errors and add egdo doctor.
5. Add atomic writes, CI, license, --version, and --no-color.
6. Test installation from a wheel.
7. Rewrite the README around one screenshot and the daily workflow.
8. Release 0.1.0.
9. Use it for several weeks before choosing between search and recurrence.

If you only do three things, I’d choose: simplify the list display, add professional diagnostics, and radically tighten the README. Those
will make it feel more mature than another ten commands would.
