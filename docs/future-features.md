# Possible Future Features

These are possibilities rather than release requirements. Reconsider them after real usage
shows a repeated need.

### Modest search

Search is the highest-priority missing user feature because it makes the archive substantially more valuable:
Search could make the archive substantially more valuable:

```bash
egdo search dentist
egdo search --tag work
egdo search --completed application
```

A simple text, tag, and date search is enough. Egdo does not need a query language.

### Completed work by date

A read-only retrospective command could answer “What did I accomplish on this date?” across
projects:

```bash
egdo completed today
egdo completed yesterday
egdo completed 2026-09-04
```

It should group completions by project, omit empty projects, and preserve project-local
history and IDs. Reconsider the command name and exact date grammar before implementation.

The view should:

- Group completed tasks by project beneath one date heading.
- Remain strictly read-only.
- Preserve project-local history and IDs.
- Omit projects with no completions on the requested date.
- Accept a small, documented date grammar consistent with other commands where practical.

The command name and exact date grammar should be reconsidered before implementation rather
than treated as part of the current CLI contract.

### Undo

Consider `egdo undo` if accidental mutations become a recurring problem. It should reverse
the most recent mutation without replacing an entire month file or overwriting unrelated
manual edits. Design and test its recovery record and conflict behavior before adding it.

### Reversible project archiving

Consider an inactive project state if removing and later re-registering projects becomes a
common workflow. Archiving should retain project identity and location without modifying its
Markdown archive. Design the commands and configuration format only after that need is
demonstrated.

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
