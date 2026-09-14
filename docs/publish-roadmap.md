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

### Archive-wide diagnostics (deferred)

Reconsider a read-only archive-wide validation command only if manual edits, sync conflicts,
or malformed historical files become a recurring problem that normal command errors do not
solve. Do not add repair behavior until real failures demonstrate which fixes are common,
unambiguous, and safe.

### A future command

- a future read-only `egdo completed DATE` command

### Possible future undo

Consider a future `egdo undo` command if accidental mutations become a recurring problem.
It should reverse the most recent mutation without replacing an entire month file or
overwriting unrelated manual edits. Design the recovery record and conflict behavior before
adding the command; do not imply that undo is currently available.

### Edge cases

- Review rollover behavior around sparse files and unusual manual edits.
- Verify behavior when tasks are manually checked or unchecked after creation.

### Modest search

Search is the highest-priority missing user feature because it makes the archive substantially more valuable:

```bash
egdo search dentist
egdo search --tag work
egdo search --completed application
```

A simple text, tag, and date search is enough. Egdo does not need a query language.

### Completed work across projects

A future retrospective command could answer “What did I accomplish on this date?” without
expanding the deliberately focused `list --all-projects` interface:

```bash
egdo completed today
egdo completed yesterday
egdo completed 2026-09-04
```

The view should:

- Group completed tasks by project beneath one date heading.
- Remain strictly read-only.
- Preserve project-local history and IDs.
- Omit projects with no completions on the requested date.
- Accept a small, documented date grammar consistent with other commands where practical.

The command name and exact date grammar should be reconsidered before implementation rather
than treated as part of the current CLI contract.

### Reversible project archiving

Projects may eventually need an inactive state that remains registered and easy to restore:

```bash
egdo project archive Minecraft
egdo project restore Minecraft
egdo project list --archived
egdo project list --all
```

Archiving is distinct from the existing `project remove` command. Removal forgets a registry
entry while leaving its marker and files untouched; archiving would retain the name, root,
and inactive status in the registry.

Expected behavior:

- `project list` shows active projects by default.
- `project list --archived` shows inactive projects and their remembered roots.
- `project list --all` clearly distinguishes both groups.
- Archived projects cannot be selected with `project use` or `-P/--project`.
- `project restore NAME` reactivates the same registration and archive.
- Archive and restore operations never modify task, note, or history files.
- Project names remain reserved while archived.
- The active project cannot be archived until another project is selected.

The global config could keep this lifecycle state outside project roots:

```toml
active_project = "Main"

[projects]
Main = "/Users/miles/Notes/egdo"

[archived_projects]
Minecraft = "/Users/miles/Notes/topics/gaming/minecraft/egdo"
```

After archiving exists, `egdo list --all-projects --include-archived` could become an explicit
read-only option. Archived projects should remain absent from the default combined view.

## Features to Defer

Avoid these until real usage demonstrates a repeated need:

- recurring tasks
- reminders and notifications
- dependencies
- task durations
- cloud synchronization
- heavyweight project management such as milestones, dependencies, teams, and workflows
- linked parent and child projects
- nested project hierarchies
- synchronized or shared tasks between projects
- moving tasks between projects
- calendar integrations
- arbitrary custom fields
- a full-screen TUI
- plugin architecture
- natural-language parsing beyond a small documented date grammar

Recurrence looks obvious, but it introduces identity, duplication, completion, editing, and history semantics. It can easily double the complexity of the storage model.

## Test Expansion

- Fix the repo-local environment and test-installation instructions.
- Test installation from a built wheel in a completely clean environment.
- Add tests for unusual manual edits and recovery behavior.
- Add tests for month and year boundaries if they are not already covered well enough.
- Add tests focused on user-facing error messages where failures are intentional.

## GitHub Readiness

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

The current repo-local environment is sufficient for running egdo and its tests, but it does
not include the tooling needed for a non-isolated wheel build. Treat that as deferred release
tooling rather than a runtime dependency or product defect. During the packaging pass, build
the wheel and source distribution in an isolated environment and document any development
tools required to reproduce those artifacts.

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

1. Expand tests around manual edits, recovery, and rollover edge cases.
2. Test installation from a wheel in a clean environment.
3. Clean up packaging metadata and document supported Python versions.
4. Publish to GitHub as a `0.1.x` release candidate.
5. Use it for several weeks before choosing between search and recurrence.
6. Evaluate PyPI publication after one more installation pass.

If only three things are done next, prioritize clean-install testing, the remaining test
gaps, and the CLI release basics. Those changes reinforce trust in the Markdown archive and
make the existing product safer to distribute.
