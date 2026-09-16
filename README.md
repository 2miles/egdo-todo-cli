# egdo

Egdo is a local-first command-line journal for tasks and notes, stored as readable Markdown
history.

Unfinished work follows you forward. Completed work stays on the day it was finished. Each
project keeps an independent journal beside its related notes, without hiding your data in an
application database.

## Why Egdo?

- **Plain Markdown** — Read and edit the archive with Obsidian, any text editor, or ordinary
  file tools.
- **Useful history** — Completed tasks and notes remain organized by day in monthly files.
- **Rolling work** — Unfinished tasks return automatically instead of becoming stranded on
  an old list.
- **Independent projects** — Initialize a journal wherever its work belongs and let directory
  context select it.
- **Terminal-native** — Use concise commands when you know what you want or guided prompts
  when you do not.

## Installation

Egdo requires Python 3.10 or newer and is tested on Python 3.10 through 3.14.

Egdo currently installs from a local clone. A dedicated tools environment keeps it available
from any directory without mixing it into another Python project:

```bash
python3 -m venv ~/.venvs/tools
~/.venvs/tools/bin/pip install -e /path/to/egdo-todo-cli
```

Add that environment to your shell path:

```bash
export PATH="$HOME/.venvs/tools/bin:$PATH"
```

Put the export in `~/.zshrc` or the corresponding startup file for your shell.

## Quick Start

Initialize a journal in the directory where its related notes live:

```bash
cd ~/Notes
egdo init Main
```

Then add, view, and complete your first task:

```bash
egdo add "Try egdo"
egdo
egdo done 1
```

Completing the task removes it from the active list but preserves it in the monthly Markdown
archive. Run `egdo add` or `egdo done` without further arguments when you prefer a guided
interactive flow.

## What It Looks Like

![Egdo task list showing current, carried-forward, and scheduled work](docs/assets/egdo-list.png)

The displayed numbers are temporary handles for commands such as `done`, `edit`, `move`,
`delete`, `tag`, and `priority`. Tags, priority, nesting, creation dates, and scheduling remain
visible without turning the list into a dashboard.

Commands can also guide you through missing choices. This tag picker appears during
interactive task creation:

![Egdo interactive tag picker](docs/assets/egdo-tag-picker.png)

Behind both views is the Markdown archive. Completed work remains readable alongside notes,
while active tasks use ordinary checklist syntax:

![Completed Egdo tasks and notes from August](docs/assets/egdo-markdown-aug.png)

![Active Egdo tasks and notes from September](docs/assets/egdo-markdown-sep.png)

## Core Ideas

**Markdown is the source of truth.** Each project stores tasks and notes in monthly files
containing only dates with actual content. If manually edited managed sections are ambiguous,
Egdo reports the file and line to fix and leaves the file unchanged.
Run `egdo open`, or for example `egdo open jan 2026`, to open a monthly file directly in
your configured editor.

**Rollover keeps work visible.** Incomplete tasks move into the current day while retaining
their original creation dates; completed tasks and notes stay in history.

**History stays searchable.** Run `egdo search dentist` to search the selected project's
tasks and notes, or add `--all-projects` to search every configured journal without
modifying their files.

**Project selection is explicit.** Running `egdo init NAME` creates a local marker and an
`egdo/` archive. Choose the active project once and Egdo keeps using it until you switch.

**Direct and interactive use coexist.** Enter a complete command such as
`egdo move 2 tomorrow`, or omit what you do not know yet and let Egdo prompt for it.

**The archive belongs with your notes.** Egdo files work naturally inside an Obsidian vault
and remain usable without Egdo.

## Multiple Projects

Initialize another journal from the directory where it belongs:

```bash
cd ~/Notes/topics/gaming/minecraft
egdo init Minecraft
```

Switch to Minecraft with `egdo project`, use `-P Minecraft` for a one-command override, or
review every journal with `egdo list --all-projects`.

## Documentation

- [Guide](docs/guide.md) — Learn Egdo’s workflows, mental model, Markdown format, and project
  behavior.
- [Command reference](docs/command-reference.md) — Look up commands, arguments, and options.
- [Changelog](CHANGELOG.md) — Review user-facing changes by release.

The [example notes](example-notes) directory contains a populated, uninitialized journal you
can copy and adopt with `egdo init Demo` as a demo or playground. When finished, run
`egdo project remove Demo` before deleting the copy; removal unregisters the project but never
deletes its files.

The built-in help always reflects the version installed on your machine:

```bash
egdo --help
egdo add --help
```

## Development

See the [architecture overview](docs/architecture.md) for the codebase structure and the
[build and installation guide](docs/build-vs-install.md) for a comparison of packaging
commands and complete contributor and release workflows.
Create the repository-local environment with any supported Python interpreter; substitute a
specific command such as `python3.14` when needed:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e '.[dev]'
```

Run the standard verification commands from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall src tests
```

Build the source distribution and wheel with:

```bash
.venv/bin/python -m build
```

Build artifacts are written to `dist/` and are not committed.

## License

Licensed under the [MIT License](LICENSE).
