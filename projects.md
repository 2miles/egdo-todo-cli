# Projects (Multiple Roots)

## Implementation Status

The initial project scope and Git-style initialization are implemented. The former raw-root
commands (`config --root`, `project add`, and `project set`) have been removed. The command
`egdo init NAME` is the single project-creation path, with directory detection and
global-default fallback. Linked projects, combined views, and cross-project operations
remain deferred.

## Direction

Add lightweight **projects** to egdo. A project is a named storage root with its own independent task history—not a heavyweight project-management system.

The feature should preserve egdo's core model: plain Markdown files, deterministic behavior, manual editability, and a small explicit CLI.

## Why Projects

Some areas of life naturally deserve completely separate todo systems. A Minecraft server, for example, may have server maintenance, build plans, backups, plugins, and related notes that should not add noise to a personal task list.

Projects provide a stronger boundary than tags:

> **Project:** Which world does this task belong to?
>
> **Tag:** What kind of task is it within that world?

For example, the `Minecraft` project could use simple tags such as `{SERVER}`, `{BUILD}`, and `{BACKUP}`. Without projects, those might become compound or nested tags such as `minecraft/server` or `minecraft/build`.

A useful test for deciding between a project and a tag is:

> Would I sometimes want to open egdo and see none of the tasks from this area?

If yes, it probably deserves a project. If it only needs occasional grouping or filtering, use a tag.

## Terminology

- **Project** is the user-facing name, such as `Main` or `Minecraft`.
- **Root** is the filesystem directory containing that project's Markdown archive.
- **Main** is the default project so ordinary egdo usage remains simple.

Project names should be case-insensitive when entered but preserve their display capitalization. For example, `egdo -P minecraft` selects the project displayed as `Minecraft`.

## Independent Project History

Each project owns its complete egdo timeline:

- active and scheduled tasks
- completed-task history
- daily notes
- monthly Markdown files
- tags
- task numbering

Example layout:

```text
~/Notes/egdo/
└── 2026/
    ├── 2026_08_aug.md
    └── 2026_09_sep.md

~/Notes/topics/gaming/minecraft/egdo/
└── 2026/
    ├── 2026_08_aug.md
    └── 2026_09_sep.md
```

When `Minecraft` is active, egdo rolls forward only Minecraft tasks and records completions only in the Minecraft archive. The `Main` archive remains untouched.

The project directory should be independently portable, synchronizable, shareable, and archivable. Task data and history must remain in the project root; the global configuration should only act as an address book.

## Visible Active Project

Every task display should clearly identify the active project. This is both orientation and a safety feature: users should always know which archive they are about to modify.

Example:

```text
Project: Minecraft
Saturday, August 29

1. Update server plugins
2. Finish the spawn area
3. Back up the world
```

Show the project header in:

- `egdo`
- `egdo list`
- future and completed list views
- interactive task-selection screens

Mutation confirmations can also name the project when useful:

```text
Added to Minecraft: Update server plugins
```

## Project CLI

Initialize projects where their related work lives, then list them or change the fallback:

```bash
cd ~/Notes
egdo init Main

cd ~/Notes/topics/gaming/minecraft
egdo init Minecraft

egdo project list
egdo project use Minecraft
```

The selected project becomes the default for ordinary commands:

```bash
egdo add "Update server plugins"
egdo list
```

Allow a temporary project override without changing the default:

```bash
egdo -P Minecraft list
egdo --project Minecraft add "Build the new spawn"
egdo -P Main list
```

Switching projects must never move, combine, modify, or delete files in another project.

## Global Configuration

The global configuration maps display names to storage roots and records the default project:

```toml
default_project = "Main"

[projects]
Main = "/Users/miles/Notes/egdo"
Minecraft = "/Users/miles/Notes/topics/gaming/minecraft/egdo"
```

The registry has one canonical named-project format. New setup uses `egdo init`; there is
no separate raw-root configuration command or pre-release single-root compatibility format.

## Initial Scope

The first version should remain deliberately small:

1. Store multiple named roots in the global configuration.
2. Provide a default `Main` project.
3. Add commands to create, list, and select projects.
4. Add `-P/--project` for a one-command override; lowercase `-p` remains task priority.
5. Show the active project at the top of every task display.
6. Keep every project's files and history completely separate.

This feature is about selecting an independent egdo archive. It does not introduce milestones, dependencies, teams, workflows, or other conventional project-management concepts.

## Git-Style Project Initialization

The Git-like initialization workflow lets users start an egdo project from the
directory where its related notes or work already live:

```bash
cd ~/Notes/topics/gaming/minecraft
egdo init Minecraft
```

This creates or adopts a local `egdo/` archive, registers it globally, and writes a small
local marker that allows egdo to recognize the project later:

```text
minecraft/
├── .egdo.toml
└── egdo/
    └── 2026/
        └── 2026_09_sep.md
```

The marker stores only the project identity:

```toml
project = "Minecraft"
```

The archive is always the sibling `egdo/` directory.

The first monthly file appears only after the first task or note is added. Initialization
does not create fake history or empty day sections.

After initialization, running egdo anywhere inside that directory tree automatically
select the nearest initialized project:

```bash
cd ~/Notes/topics/gaming/minecraft/server
egdo
egdo add "Update server plugins"
```

Project resolution uses this precedence:

1. An explicit `-P/--project` selection.
2. The nearest `.egdo.toml` found by walking upward from the current directory.
3. The globally configured default project.

Initialization behavior:

- `egdo init NAME` uses `<current-directory>/egdo` as the project root.
- It registers the display name and expanded root in the global config.
- It resolves the local root relative to the marker; tasks and history remain in ordinary
  Markdown below `egdo/`.
- It refuses to overwrite a conflicting marker or reuse a case-insensitive name for another
  root.
- If the local `egdo/` archive already exists, initialization adopts it without rewriting
  its files.
- Re-running initialization for the same name and root is safe and idempotent.
- Explicit project selection must always override directory detection.
- `init` is the only project-creation path, keeping raw root bookkeeping out of the normal
  interface.
- Moving the entire initialized directory keeps local use working because the archive is
  always beside `.egdo.toml`; discovery refreshes the global registry automatically.
- If the old location still has a live marker with the same project name, egdo rejects the
  duplicate instead of silently treating a copy as a move.

### First project and nested projects

When no global config exists, the first initialization also establishes the default
project:

```bash
cd ~/Notes
egdo init Main
```

This:

1. Create `~/Notes/.egdo.toml`.
2. Register `Main` with `~/Notes/egdo` as its archive root.
3. Make `Main` the global default project.
4. Defer creating year and month files until the first task or note is added.

Later `egdo init NAME` calls register additional projects without changing the existing
default. A marker applies to its directory and descendants until a nearer marker overrides
it. For example:

```text
~/Notes/                              → Main
~/Notes/personal/                     → Main
~/Notes/topics/gaming/minecraft/      → Minecraft
~/Notes/topics/gaming/minecraft/wiki/ → Minecraft
```

Initializing `Main` at a broad location such as `~/Notes` therefore provides a useful
fallback throughout an Obsidian vault, while nested topic projects can establish more
specific contexts. Outside every initialized directory tree, egdo falls back to the global
default project.

This provides a simpler product explanation:

> Run `egdo init NAME` in any directory to start a rolling Markdown work journal there.

## Future: Read-Only All-Projects View

A combined view should make it possible to review work across every active project without
merging their archives or creating a global task namespace.

Proposed command:

```bash
egdo list --all-projects
```

The output should group tasks by project and retain each project's local IDs:

```text
Project: Main

1. Send invoice
2. Buy groceries

Project: Minecraft

1. Update server plugins
2. Finish the spawn area
```

Expected behavior:

- Include every active configured project and exclude archived projects by default.
- Keep projects visually separated and clearly named.
- Preserve the task IDs from each project's normal list rather than assigning global IDs.
- Apply supported list filters independently within every project, such as `--future`,
  `--completed`, and `--tag`.
- Show an empty project only if doing so provides useful context; otherwise omit it and print
  one combined empty-state message when no project has matching tasks.
- Use a deterministic project order, preferably the order stored in the config.
- Report an unreadable or malformed project with its project name and root rather than
  silently omitting it.

The combined view must be strictly read-only. It should not rewrite month files, perform
persistent rollover, change the default project, or expose its project-local numbers to
mutation commands. To modify a listed task, the user must select its project explicitly:

```bash
egdo -P Minecraft done 2
```

If normal list preparation currently requires persistent rollover, the all-projects view
should compute the equivalent carried-forward presentation without saving it. This avoids a
single overview command unexpectedly modifying every configured archive.

After project archiving exists, a separate explicit option such as
`egdo list --all-projects --include-archived` could be considered. Archived projects should
not be included by the default all-projects view because archiving is intended to remove
them from everyday use.

## Future: Project Archiving

Projects may eventually need a reversible inactive state. Archiving should hide a project
from everyday use without moving, rewriting, or deleting any of its Markdown files.

Proposed commands:

```bash
egdo project archive Minecraft
egdo project restore Minecraft
egdo project list --archived
egdo project list --all
```

Expected behavior:

- `project list` shows active projects only.
- `project list --archived` shows archived projects and their remembered roots.
- `project list --all` shows both groups with a clear status distinction.
- `project archive NAME` moves only the project registration into an archived state.
- An archived project cannot be selected with `project use` or `-P/--project`.
- `project restore NAME` makes the same project active again at its existing root.
- Archive and restore operations never modify the project's task, note, or history files.
- Project names remain reserved while archived, preventing another active project from using
  the same case-insensitive name.

The global config could represent this without placing lifecycle metadata in project roots:

```toml
default_project = "Main"

[projects]
Main = "/Users/miles/Notes/egdo"

[archived_projects]
Minecraft = "/Users/miles/Notes/topics/gaming/minecraft/egdo"
```

Egdo should refuse to archive the default project. The user must first select another
default:

```text
Cannot archive the default project “Minecraft”.
Select another default with `egdo project use NAME` first.
```

Use `restore` rather than “reinstantiate” in the CLI because the project and its files are
never destroyed or recreated. Permanent removal, if it is ever added, should remain a
separate and explicitly destructive operation. Archive and restore should be implemented
before considering project removal.

## Ideas to Defer

Do not include these in the initial implementation:

- linked parent and child projects
- nested project hierarchies
- synchronized or shared tasks between projects
- moving tasks between projects

These may be evaluated after using the basic feature.

## Design Principle

Projects should protect egdo's simplicity rather than expand its complexity:

> A project is an independent egdo timeline with a name.

Everything else about tasks, notes, rollover, Markdown storage, and manual editing should continue to work as it does within a single root today.
