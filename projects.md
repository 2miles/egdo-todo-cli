# Projects (Multiple Roots)

## Implementation Status

The initial scope described below is implemented on the `projects` branch. Project setup
and root changes use the unified `project add` and `project set` interface; the former
single-root `config --root` command has been removed. Linked projects, combined views,
directory detection, and cross-project operations remain deferred.

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

## Proposed CLI

Manage named projects with explicit subcommands:

```bash
egdo project add Main ~/Notes/egdo
egdo project add Minecraft ~/Notes/topics/gaming/minecraft/egdo
egdo project list
egdo project set Minecraft ~/Notes/topics/gaming/minecraft/egdo
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

## Proposed Global Configuration

The global configuration maps display names to storage roots and records the default project:

```toml
default_project = "Main"

[projects]
Main = "/Users/miles/Notes/egdo"
Minecraft = "/Users/miles/Notes/topics/gaming/minecraft/egdo"
```

Existing installations with a single top-level `root` should have a clear, safe migration path to a `Main` project. Migration must not relocate or rewrite the existing archive.

The compatibility reader treats a legacy top-level `root` as `Main`. The next `project add`,
`project set`, or `project use` saves the canonical project format and a backup. New setup
uses `project add`; there is no separate single-root configuration command.

## Initial Scope

The first version should remain deliberately small:

1. Store multiple named roots in the global configuration.
2. Provide a default `Main` project.
3. Add commands to create, list, and select projects.
4. Add `-P/--project` for a one-command override; lowercase `-p` remains task priority.
5. Show the active project at the top of every task display.
6. Keep every project's files and history completely separate.
7. Preserve a narrow read-and-migrate path for existing single-root configs and archives.

This feature is about selecting an independent egdo archive. It does not introduce milestones, dependencies, teams, workflows, or other conventional project-management concepts.

## Ideas to Defer

Do not include these in the initial implementation:

- linked parent and child projects
- nested project hierarchies
- synchronized or shared tasks between projects
- automatic aggregation of all project task lists
- moving tasks between projects
- automatic project detection based on the current directory
- local `.egdo.toml` project declarations

These may be evaluated after using the basic feature. Possible later additions include:

```bash
egdo list --all-projects
```

and directory-based detection, where running `egdo` inside a Minecraft directory automatically selects `Minecraft`. Both ideas require clear precedence and safety rules before implementation.

## Design Principle

Projects should protect egdo's simplicity rather than expand its complexity:

> A project is an independent egdo timeline with a name.

Everything else about tasks, notes, rollover, Markdown storage, and manual editing should continue to work as it does within a single root today.
