# Python `argparse` reference

`argparse.ArgumentParser` defines the grammar of a command-line program. It
turns a list of string tokens into a validated Python object.

For example, the shell command:

```console
egdo add --tag work --priority important "Submit report"
```

reaches Python approximately as:

```python
[
    "add",
    "--tag",
    "work",
    "--priority",
    "important",
    "Submit report",
]
```

The parser turns those tokens into a namespace resembling:

```python
Namespace(
    command="add",
    tag="work",
    priority="important",
    text="Submit report",
)
```

## Creating a parser

```python
parser = argparse.ArgumentParser(
    prog="egdo",
    description="A rolling Markdown work journal.",
    epilog="Run `egdo COMMAND --help` for command-specific usage.",
)
```

- `prog` is the program name displayed in usage and errors.
- `description` appears before the argument list in help.
- `epilog` appears after the argument list.
- `formatter_class` can customize how help is laid out.

Creating the parser only defines the grammar. Parsing happens later:

```python
args = parser.parse_args(argv)
```

With no explicit `argv`, `parse_args()` reads `sys.argv[1:]`.

## Positional and optional arguments

A positional argument is identified by its position:

```python
add_parser.add_argument("text")
```

```console
egdo add "Buy milk"
```

The value becomes `args.text`.

An optional argument is identified by a flag:

```python
parser.add_argument("-P", "--project")
```

Both of these set `args.project`:

```console
egdo -P Minecraft list
egdo --project Minecraft list
```

"Optional" means the flag may be omitted. If present, it can still require a
value.

## `dest`: the Python attribute

Every argument stores its result under a destination name.

```python
parser.add_argument(
    "-P",
    "--project",
    dest="selected_project",
)
```

The command-line spelling is `--project`, but Python reads:

```python
args.selected_project
```

For long options, hyphens normally become underscores automatically:

```text
--all-projects -> args.all_projects
```

For a positional argument, its declared name is normally its destination:

```python
parser.add_argument("text")  # args.text
```

## `metavar`: the help placeholder

`metavar` only affects help and usage output:

```python
parser.add_argument("--project", metavar="NAME")
```

Help displays:

```text
--project NAME
```

It does not change the Python attribute name.

```text
--project   command-line option
NAME        help placeholder (`metavar`)
project     Python attribute (`dest`)
```

Use `metavar` to tell a reader what kind of value belongs there, such as
`NAME`, `ID`, `TEXT`, `DATE`, or `PATH`.

## Common `add_argument()` settings

### `help`

Describes an argument in generated help:

```python
parser.add_argument(
    "--tag",
    metavar="TAG",
    help="Show only tasks with this leading tag",
)
```

### `type`

Values are strings unless they are converted:

```python
parser.add_argument("--count", type=int)
parser.add_argument("--path", type=Path)
```

If conversion fails, `argparse` reports an error and exits. A custom callable
can also be used as a type.

### `choices`

Restricts a value to a known set:

```python
parser.add_argument(
    "--priority",
    choices=["important", "normal"],
)
```

Invalid choices are rejected automatically and the choices appear in help.

### `default`

Supplies a value when the argument is omitted:

```python
parser.add_argument("--priority", default="normal")
```

The usual implicit default is `None`. Keeping `None` can be useful when the
program must distinguish "not supplied" from an explicit value.

### `required`

Positionals are normally required. Flags are normally optional:

```python
parser.add_argument("--name", required=True)
```

This requires the `--name` flag, although a required flag may sometimes be
clearer as a positional argument.

## Actions

An action controls what happens when an argument is encountered.

The default action stores one value:

```python
parser.add_argument("--tag")  # action="store"
```

Boolean flags commonly use:

```python
parser.add_argument("--debug", action="store_true")
```

The result is `False` when absent and `True` when present. `store_false` does
the reverse.

Repeated flags can build a list:

```python
parser.add_argument("--tag", action="append")
```

```console
program --tag work --tag urgent
```

produces `args.tag == ["work", "urgent"]`.

Occurrences can be counted:

```python
parser.add_argument("-v", action="count", default=0)
```

The built-in version action prints a version and exits:

```python
parser.add_argument(
    "--version",
    action="version",
    version="%(prog)s 1.0.0",
)
```

## `nargs`: how many tokens are consumed

The default is exactly one token:

```python
parser.add_argument("text")
```

`nargs="?"` accepts zero or one token:

```python
parser.add_argument("text", nargs="?")
```

The result is usually `None` when omitted.

`nargs="*"` accepts zero or more and always produces a list:

```python
parser.add_argument("indexes", nargs="*")
```

```text
egdo done       -> []
egdo done 1     -> ["1"]
egdo done 1 3   -> ["1", "3"]
```

`nargs="+"` accepts one or more and produces a list. An integer such as
`nargs=2` requires exactly that many tokens.

`nargs=argparse.REMAINDER` captures all tokens left over. This is mainly useful
for programs that forward arguments to another command.

## Subparsers

Subparsers define commands such as `add`, `list`, and `move`:

```python
commands = parser.add_subparsers(
    dest="command",
    required=True,
)

add_parser = commands.add_parser("add")
list_parser = commands.add_parser("list")
```

When parsing `egdo add "Buy milk"`, the root parser recognizes `add`, selects
the add parser, and lets that parser consume the remaining tokens. With
`dest="command"`, the result contains:

```python
args.command == "add"
```

Arguments belong to the parser on which they are registered:

```python
add_parser.add_argument("text", nargs="?")
list_parser.add_argument("--future", action="store_true")
```

Therefore, `--future` is valid for `list` but not for `add`.

Subparsers can contain their own subparsers. This represents nested commands:

```text
egdo project list
egdo project use NAME
egdo project remove NAME
```

A parse result might contain both:

```python
args.command == "project"
args.project_command == "remove"
```

## Global and command-specific arguments

Arguments registered on the root parser are global. Arguments registered on a
subparser belong only to that command.

```text
root parser
├── --debug
├── --project NAME
└── commands
    ├── add
    │   ├── TEXT
    │   └── --tag TAG
    └── list
        └── --future
```

Global options are most reliably placed before the command:

```console
egdo --debug add "Task"
```

Command options follow their command:

```console
egdo add --tag work "Task"
```

## The `Namespace`

`parse_args()` normally returns `argparse.Namespace`, a simple object whose
attributes are the parsed values:

```python
args.command
args.text
args.tag
args.debug
```

Use `vars(args)` to see the same values as a dictionary.

## Help and errors

`ArgumentParser` generates help from parser descriptions, arguments, choices,
metavars, and subcommands:

```console
egdo --help
egdo add --help
egdo project remove --help
```

Help normally prints and raises `SystemExit(0)`. Invalid syntax prints an error
to standard error and raises `SystemExit(2)`.

This makes a useful division of responsibility:

- `argparse` handles malformed CLI syntax, missing required values, unknown
  options, invalid types, and invalid choices.
- Application code handles errors such as an unknown task ID, missing
  configuration, or a file that cannot be written.

`parser.error("message")` manually reports a parser-style error and raises
`SystemExit(2)`.

`parse_known_args()` returns `(args, unknown)` instead of rejecting unknown
tokens. It is useful when forwarding arguments, but most CLIs should prefer
`parse_args()` so that spelling mistakes are caught.

## Argument groups

A mutually exclusive group rejects incompatible options:

```python
view = parser.add_mutually_exclusive_group()
view.add_argument("--future", action="store_true")
view.add_argument("--completed", action="store_true")
```

A normal argument group only organizes help output:

```python
display = parser.add_argument_group("display options")
display.add_argument("--color")
```

Do not confuse:

- `add_argument_group()`: organizes help.
- `add_mutually_exclusive_group()`: validates incompatible options.
- `add_subparsers()`: defines commands.

## Custom parser classes

A subclass can run normalization after standard parsing:

```python
class CustomParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        # Normalize an ambiguous command shape here.
        return parsed
```

Egdo uses this for `move` and `priority`, whose final positional token can have
a different meaning from preceding tokens. Standard `argparse` captures the
tokens, and the custom parser separates them afterward.

## Function dispatch with `set_defaults()`

A subparser can store a callback:

```python
add_parser.set_defaults(handler=handle_add)
list_parser.set_defaults(handler=handle_list)

args = parser.parse_args()
return args.handler(args)
```

This is an alternative to checking `args.command` in a dispatcher. It can be
useful for a large CLI, but it also hides routing inside parser construction.
An explicit dispatcher is often easier to trace in a small application.

## The shell parses first

`argparse` does not receive the raw command string. The shell splits it first:

```console
egdo add Buy milk
```

becomes three tokens after `egdo`, whereas:

```console
egdo add "Buy milk"
```

contains one text token. Quotes are handled by the shell and generally do not
reach Python.

## A complete small example

```python
import argparse

parser = argparse.ArgumentParser(
    prog="tasks",
    description="Manage tasks.",
)

parser.add_argument(
    "--debug",
    action="store_true",
    help="show detailed errors",
)

commands = parser.add_subparsers(
    dest="command",
    required=True,
)

add_parser = commands.add_parser("add", help="create a task")
add_parser.add_argument("text", metavar="TEXT")
add_parser.add_argument(
    "-p",
    "--priority",
    choices=["normal", "important"],
    default="normal",
)

list_parser = commands.add_parser("list", help="show tasks")
list_parser.add_argument("--completed", action="store_true")

args = parser.parse_args()
```

Given:

```console
tasks --debug add --priority important "Submit report"
```

the result is approximately:

```python
Namespace(
    debug=True,
    command="add",
    text="Submit report",
    priority="important",
)
```

## Mental model

Think of an `ArgumentParser` as a tree-shaped grammar:

```text
program
├── global options
└── command
    ├── first command
    │   └── its arguments
    └── second command
        └── its arguments
```

Parsing walks this tree, validates the input tokens, and returns a flat
`Namespace`. Application code then uses that structured result to perform the
requested work.

The key terms are:

- **Parser:** defines the CLI grammar.
- **Subparser:** defines one command within the grammar.
- **Argument:** defines one accepted input.
- **Positional:** identified by its position.
- **Optional/flag:** identified by `-x` or `--name`.
- **`dest`:** Python attribute name.
- **`metavar`:** placeholder displayed in help.
- **`action`:** behavior when an argument is encountered.
- **`nargs`:** number of tokens consumed.
- **`type`:** conversion applied to a string value.
- **`choices`:** allowed values.
- **`Namespace`:** parsed result.
- **`parse_args()`:** validates input and builds the result.
