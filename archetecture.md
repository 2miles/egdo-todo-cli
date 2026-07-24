## 1. Big Picture

At the highest level, cli.py parses the command, handlers.py decides what to do, store.py changes task/note state, and markdown_store.py
reads/writes the actual files.

mental model: most commands become “load markdown into structured state, mutate it, render it back.”

## Example markdown file

```md
## Jul-12 Sun

### Tasks

- [ ] Go to the grocery store (07-12)
- [x] finish lookup table (07-12)

### Notes

Remember to follow up tomorrow.
```

Parsed roughly as:

```python
  FileState(
      days={
          date(2026, 7, 12): DayState(
              tasks=[
                  Task("Go to the grocery store", created=2026-07-12, done=False),
                  Task("finish lookup table", created=2026-07-12, done=True),
              ],
              notes=[
                  "Remember to follow up tomorrow."
              ],
          )
      }
  )
```

## The clean way to read this repo is:

1. Start with cli.py: what commands exist?
2. Then handlers.py: what does each command call?
3. Then store.py: how does the command change state?
4. Then markdown_store.py: how does state become markdown?
5. Then render.py: how display output is formatted.

The core architectural idea is good: the markdown files are the source of truth, and Python objects are temporary parsed state used while
a command runs.
