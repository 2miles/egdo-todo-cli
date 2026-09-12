# Egdo Publish Roadmap

This document combines the publication roadmap with the historical product-cleanup review. It captures the work needed to move `egdo` from a working personal tool to something ready to share publicly on GitHub and potentially package for wider use later.

> The product-review sections preserve the problems and proposals that drove the cleanup, so examples of the old interface are intentional. For current behavior, use `README.md`, `docs/guide.md`, and `docs/command-reference.md`.

The guiding recommendation is to make egdo feel like a calm, opinionated daily task journal—not a miniature Taskwarrior. The biggest gains should come from subtraction, consistency, and trustworthiness rather than more task-management features.

## Goal

Make `egdo` solid enough that someone outside this repo can:

- understand what it does quickly
- install it without friction
- use it without hitting avoidable parser or UX problems
- trust the Markdown workflow and file model

## Product Hardening

### Markdown safeguards and diagnostics

- Improve errors for malformed or partially malformed daily task sections.
- Make parser failures identify the file, line, and likely problem rather than raising generic exceptions.
- Decide how tolerant `egdo` should be of partially malformed task blocks.
- Keep the parser permissive enough for manual editing without making behavior ambiguous.
- Make writes atomic so an interruption cannot corrupt a month file.
- Verify that the documented storage invariant consistently describes the actual monthly format.

Useful errors should include:

- what failed
- where it failed
- how to correct it
- no traceback unless `--debug` is supplied

For example:

```text
egdo: cannot parse ~/Notes/egdo/2026/2026_08_aug.md:42
Nested task must follow a parent task.

Run `egdo doctor` to check the rest of the archive.
```

### A useful doctor command

Because the files are manually editable, a diagnostic command fits the product well:

```bash
egdo doctor
```

It could check:

- configuration exists
- root directory is writable
- month files parse successfully
- task dates and nesting are valid
- no malformed task sections exist

Initially it should only report problems. A future `egdo doctor --fix` could normalize safe cases after showing a preview.

### CLI UX and command language

- Review `--help` output for every command.
- Add clearer help text and examples where the CLI is too terse.
- Decide whether common mistakes such as `egdo --add` deserve a friendlier error path.
- Make success and failure messages consistent.
- Add `--version`.
- Add `--no-color` and respect the `NO_COLOR` environment variable.
- Send machine-readable errors to stderr and use reliable exit codes.
- Choose one spelling and casing convention everywhere for terms such as “Markdown,” “ID,” “todo,” dates, quotation marks, and arrows.
- Avoid clearing the entire terminal after every mutation unless users opt into it; an inline refresh may be less disruptive.
- If clearing remains, add `--quiet` and possibly `--no-refresh`.

### A future command

- a future read-only `egdo completed DATE` command

### Destructive-operation safety

A concise recovery path is preferable to confirmation prompts on every deletion:

```text
egdo delete 4

# Deleted “Cancel old subscription”
# Undo: egdo restore
```

An undo mechanism would be valuable, but atomic backup files or Git integration may be enough initially. Avoid making the CLI tedious with confirmation prompts for every deletion.

### Edge cases

- Review rollover behavior around sparse files and unusual manual edits.
- Verify behavior when files contain unexpected content inside daily sections.
- Verify behavior when tasks are manually checked or unchecked after creation.

## Focused Feature Additions

These additions reinforce the product’s existing model rather than expanding away from it.

### Direct file opening

Manual editing is one of egdo’s differentiators, so make it effortless:

```bash
egdo open
egdo open today
egdo open 2026-08-12
```

Use `$EDITOR` and open the relevant monthly file at the relevant day if practical.

### Modest search

Search is the highest-priority missing user feature because it makes the archive substantially more valuable:

```bash
egdo search dentist
egdo search --tag work
egdo search --completed application
```

A simple text, tag, and date search is enough. Egdo does not need a query language.

## Features to Defer

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

Recurrence looks obvious, but it introduces identity, duplication, completion, editing, and history semantics. It can easily double the complexity of the storage model.

## Test Expansion

- Add CI across supported Python versions.
- Fix the repo-local environment and test-installation instructions.
- Test installation from a built wheel in a completely clean environment.
- Add tests for malformed or partially malformed Markdown in daily sections.
- Add tests for unusual manual edits and recovery behavior.
- Add tests for files with preserved preamble content and unusual Notes sections.
- Add tests for month and year boundaries if they are not already covered well enough.
- Add tests focused on user-facing error messages where failures are intentional.

## GitHub Readiness

### README presentation

The top of the README should be much shorter and make the value obvious within the first few paragraphs. Add a short “why this exists” pitch and consider this opening:

> egdo is a terminal task list that keeps your work in ordinary Markdown.
>
> Unfinished tasks roll into today. Completed tasks remain in the day they were finished, turning your todo list into a searchable work journal.

Then present:

1. A short animated demo or polished terminal screenshot.
2. Installation.
3. A five-command, copy-paste-friendly quick start.
4. Example Markdown output.
5. “Why egdo instead of Taskwarrior or todo.txt?”
6. Links to the full guide and command reference.

Also:

- Make the manual-editing workflow clear.
- Make the `.venv` workflow clear and consistent throughout.
- Avoid introducing nearly every command before the reader experiences the basic loop.

### Project metadata

- Choose and add a license.
- State supported Python versions clearly in the README and packaging metadata.
- Confirm the versioning approach for early releases such as `0.1.x`.
- Add a simple changelog or release-notes file.

### Repository hygiene

- Review `.gitignore` for anything else that should be excluded.
- Make sure the repository layout is clean and understandable to a new visitor.
- Decide whether planning documents should remain in the root or move into `docs/` later.

## Packaging Path

### Installation documentation transition

The README currently documents an editable installation from a local clone:

```bash
python3 -m venv ~/.venvs/tools
~/.venvs/tools/bin/pip install -e /path/to/egdo-todo-cli
```

This is appropriate while egdo is primarily a development checkout, but it assumes the user
already has the repository and understands how to replace the example path. The `-e` flag
also means Python runs the package from that working tree, which is useful for development
rather than a normal end-user installation.

Before presenting egdo as a generally installable tool, choose and test one primary public
installation path. Likely stages are:

```bash
# Install directly from GitHub
pipx install git+https://github.com/USER/egdo-todo-cli.git

# Install from PyPI after publication
pipx install egdo
```

`pipx` is a natural default for a Python CLI because it provides an isolated environment
while exposing the `egdo` executable globally. Confirm the final repository URL and PyPI
package name before publishing either command.

Once a public installation path is ready:

- Replace the editable-install instructions in the README with the shortest supported command.
- Keep source-checkout and editable-install instructions in contributor or development docs.
- Test the documented command on a clean machine or isolated environment.
- Verify that `egdo --help`, `egdo init Main`, upgrades, and uninstalling all work as described.
- State the supported Python versions and how users should upgrade.

### GitHub first

- Publish the repository once the README, license, and basic docs are ready.
- Include a short project description and usage example in the repository metadata.
- Treat the first public state as a clean `0.1.x` release candidate.

### PyPI later

- Check whether the package name `egdo` is available.
- Verify installation in a clean virtual environment, including from a built wheel.
- Build a source distribution and wheel.
- Confirm the package metadata is complete before uploading.
- Publish to PyPI only after the installation and help experience feels stable.

## Recommended Release Sequence

1. Redesign the default list and simplify priority presentation.
2. Reconcile command names and remove `unmove`.
3. Standardize interactive picker visuals.
4. Improve parser errors and add `egdo doctor`.
5. Add atomic writes, CI, a license, `--version`, and `--no-color`.
6. Expand tests around malformed Markdown, manual edits, and rollover edge cases.
7. Test installation from a wheel in a clean environment.
8. Rewrite the README around one screenshot and the daily workflow.
9. Clean up packaging metadata and document supported Python versions.
10. Publish to GitHub as a `0.1.x` release candidate.
11. Use it for several weeks before choosing between search and recurrence.
12. Evaluate PyPI publication after one more installation pass.

If only three things are done, prioritize simplifying the list display, adding professional diagnostics, and radically tightening the README. Those changes will make egdo feel more mature than another ten commands would.
