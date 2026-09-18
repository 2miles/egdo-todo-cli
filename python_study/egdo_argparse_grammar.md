# Egdo `argparse` grammar

This is a tree-shaped reference for the parser defined by `build_parser()` in
`src/egdo/cli.py`.

## Full parser tree

```text
egdo
├── global options
│   ├── -P NAME, --project NAME
│   │   └── dest: selected_project
│   ├── --debug
│   │   └── action: store_true
│   └── --version
│       └── action: version
│
└── COMMAND (required subparser; dest: command)
    │
    ├── init NAME
    │   └── NAME
    │       ├── positional, required
    │       └── dest: name
    │
    ├── project [ACTION]
    │   └── ACTION (optional nested subparser; dest: project_command)
    │       ├── no action
    │       │   └── interactively select the active project
    │       ├── list
    │       ├── use NAME
    │       │   └── NAME
    │       │       ├── positional, required
    │       │       └── dest: name
    │       └── remove NAME [--force]
    │           ├── NAME
    │           │   ├── positional, required
    │           │   └── dest: name
    │           └── --force
    │               └── action: store_true
    │
    ├── add [TEXT] [-t TAG | --tag TAG]
    │       [-p LEVEL | --priority LEVEL] [--done] [--parent ID]
    │   ├── TEXT
    │   │   ├── positional
    │   │   ├── nargs: ?
    │   │   └── dest: text
    │   ├── -t TAG, --tag TAG
    │   │   └── dest: tag
    │   ├── -p LEVEL, --priority LEVEL
    │   │   └── dest: priority
    │   ├── --done
    │   │   ├── action: store_true
    │   │   └── dest: done
    │   └── --parent ID
    │       └── dest: parent
    │
    ├── list [-t TAG | --tag TAG] [--all-projects]
    │        [--future | --completed]
    │   ├── -t TAG, --tag TAG
    │   │   └── dest: tag
    │   ├── --all-projects
    │   │   ├── action: store_true
    │   │   └── dest: all_projects
    │   └── mutually exclusive view
    │       ├── --future
    │       │   ├── action: store_true
    │       │   └── dest: future
    │       └── --completed
    │           ├── action: store_true
    │           └── dest: completed
    │
    ├── search [TEXT] [-t TAG | --tag TAG] [--completed]
    │          [--tasks | --notes] [--all-projects]
    │   ├── TEXT
    │   │   ├── positional
    │   │   ├── nargs: ?
    │   │   └── dest: query
    │   ├── -t TAG, --tag TAG
    │   │   └── dest: tag
    │   ├── --completed
    │   │   ├── action: store_true
    │   │   └── dest: completed
    │   ├── mutually exclusive result kind
    │   │   ├── --tasks
    │   │   │   ├── action: store_true
    │   │   │   └── dest: tasks
    │   │   └── --notes
    │   │       ├── action: store_true
    │   │       └── dest: notes
    │   └── --all-projects
    │       ├── action: store_true
    │       └── dest: all_projects
    │
    ├── done [ID ...]
    │   └── ID
    │       ├── positional
    │       ├── nargs: *
    │       └── dest: indexes
    │
    ├── edit [ID] [TEXT]
    │   ├── ID
    │   │   ├── positional
    │   │   ├── nargs: ?
    │   │   └── dest: index
    │   └── TEXT
    │       ├── positional
    │       ├── nargs: ?
    │       └── dest: text
    │
    ├── move [ID_OR_WHEN ...]
    │   └── ID_OR_WHEN
    │       ├── positional
    │       ├── nargs: *
    │       ├── initial dest: move_values
    │       └── normalized after parsing into:
    │           ├── indexes: list of task IDs
    │           └── when: today, tomorrow, +N, weekday, or YYYY-MM-DD
    │
    ├── delete [ID ...]
    │   └── ID
    │       ├── positional
    │       ├── nargs: *
    │       └── dest: indexes
    │
    ├── tag [ID_OR_TAG ...] [--remove]
    │   ├── ID_OR_TAG
    │   │   ├── positional
    │   │   ├── nargs: *
    │   │   └── dest: values
    │   └── --remove
    │       ├── action: store_true
    │       └── dest: remove
    │
    ├── priority [ID_OR_LEVEL ...]
    │   └── ID_OR_LEVEL
    │       ├── positional
    │       ├── nargs: *
    │       ├── initial dest: priority_values
    │       └── normalized after parsing into:
    │           ├── indexes: list of task IDs
    │           └── level: important, normal, or None
    │
    ├── note [TEXT]
    │   └── TEXT
    │       ├── positional
    │       ├── nargs: ?
    │       └── dest: text
    │
    └── open [MONTH ...]
        └── MONTH
            ├── positional
            ├── nargs: *
            ├── dest: month_values
            └── accepted application-level forms:
                ├── no value: current month
                ├── YYYY-MM
                ├── month name
                └── month name followed by a year
```

## Approximate command forms

Brackets mean optional input. An ellipsis means a value may repeat. A vertical
bar means alternatives.

```text
egdo [-P NAME | --project NAME] [--debug] [--version] COMMAND

egdo init NAME

egdo project
egdo project list
egdo project use NAME
egdo project remove NAME [--force]

egdo add [TEXT] [-t TAG | --tag TAG]
               [-p LEVEL | --priority LEVEL]
               [--done] [--parent ID]

egdo list [-t TAG | --tag TAG] [--all-projects]
          [--future | --completed]

egdo search [TEXT] [-t TAG | --tag TAG] [--completed]
                   [--tasks | --notes] [--all-projects]

egdo done [ID ...]
egdo edit [ID] [TEXT]
egdo move [ID_OR_WHEN ...]
egdo delete [ID ...]
egdo tag [ID_OR_TAG ...] [--remove]
egdo priority [ID_OR_LEVEL ...]
egdo note [TEXT]
egdo open [MONTH ...]
```

## Parsing versus application validation

The parser accepts some deliberately broad token shapes. Handlers perform
additional validation after parsing.

- `move` initially accepts any number of `ID_OR_WHEN` strings. The custom
  `EgdoArgumentParser.parse_args()` method separates IDs from the destination.
- `priority` initially accepts any number of `ID_OR_LEVEL` strings. The custom
  parser treats a final `important` or `normal` token as the level.
- `tag` initially accepts `ID_OR_TAG` strings. The handler separates task IDs
  from the tag and enforces exactly one tag when not removing one.
- `open` accepts zero or more `MONTH` tokens at the parser level. The date
  parser later accepts only zero tokens, one `YYYY-MM` or month-name token, or
  a month name followed by a four-digit year.
- Some combinations are rejected by handlers rather than `argparse`, such as
  `list --all-projects --future` and incompatible search filters.

## Default command behavior

The parser requires a command, but `main()` supplies one before parsing when
the user enters plain `egdo`:

```python
if not argv:
    argv = ["list"]
```

Therefore, the user-facing behavior is:

```text
egdo -> egdo list
```

while the parser itself still has a required `COMMAND` subparser.
