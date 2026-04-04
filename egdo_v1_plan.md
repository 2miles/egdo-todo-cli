  # Egdo v1 Plan

  ## Summary

  Build egdo as a Python CLI that manages todos in markdown files inside a notes directory, with one daily file per date under a per-month folder
  layout like .../egdo/2026/04/2026-04-03.md.

  The CLI will support add, list, done, and automatic carry-forward. It will preserve a historical archive by keeping completed tasks in the file
  where they were completed, while moving unfinished tasks into the next day’s file on first access for that day.

  ## Implementation Changes

  - Create a small Python package with a console entrypoint egdo, using the standard library argparse for v1 rather than a heavier CLI framework.
  - Store configuration in a home-level TOML file, defaulting to something like ~/.config/egdo/config.toml, with:
      - notes_root
      - todos_root or relative subpath inside the notes directory
      - optional timezone defaulting to local system time
  - Use a dedicated, clearly delimited section inside each markdown file so manual notes can coexist safely. Recommended markers:
      - ## Egdo
      - <!-- EGDO:START -->
      - <!-- EGDO:END -->
  - Represent each task as a markdown checklist item plus metadata lines that remain readable in Obsidian. Example shape:
      - - [ ] Buy milk
      -   - created: 2026-04-03
      -   - completed:
      -   - origin: 2026-04-03
  - Keep origin stable across rollover so archive history is preserved even after a task moves forward. On completion, set completed to the current
    day and leave the task in that day’s file.
  - On first add or list access for a target day, scan backward to the most recent prior egdo file, extract unfinished tasks from the managed
    section, append them into the target day if not already present, and remove them from the prior day’s managed section.
  - list will show active tasks for the selected day as numbered items. done <n> will complete by numeric index from that day’s current active list.
  - Parser behavior should be resilient but bounded:
      - Only mutate content inside the managed section
      - Preserve non-egdo content exactly
      - Accept manual edits to task text and checkbox state
      - Accept minimal manual checklist items inside the managed section and normalize missing metadata from the file date
      - Rebuild the section deterministically on write to avoid fragile in-place editing logic
  - Default date target is “today” in local time, with optional --date YYYY-MM-DD on add, list, and done for backfill or manual correction.

  ## Public Interfaces

  - CLI commands:
      - egdo add "task text" [--date YYYY-MM-DD]
      - egdo list [--date YYYY-MM-DD]
      - egdo done <index> [--date YYYY-MM-DD]
      - egdo init
  - Config file interface:
      - TOML keys for notes path and todo root
  - Markdown contract:
      - One managed section per daily file
      - Checklist items with stable metadata fields created, completed, and origin after normalization
      - Minimal manual checklist items are also valid input inside the managed section

  ## Test Plan

  - Adding a first task creates the correct dated file and managed section.
  - Adding multiple tasks appends cleanly and preserves non-egdo note content.
  - Listing a new day carries forward unfinished tasks from the most recent prior day.
  - Carry-forward removes unfinished tasks from the previous day and does not duplicate tasks if run twice.
  - Completing a task marks it done in the current day’s file and leaves it archived there.
  - Completing by numeric index only affects the intended active item.
  - Manual note content before and after the managed section remains unchanged after CLI operations.
  - Manual edits to task text inside the managed section remain parseable and writable.
  - Manual open checklist items without metadata are normalized on first read/write.
  - Manual completed checklist items without completion metadata are normalized on first read/write.
  - Empty prior days, missing files, and month-boundary rollover work correctly.

  ## Assumptions

  - v1 does not include edit, delete, priority, tags, or search.
  - v1 uses local filesystem only; no sync-specific logic beyond writing Obsidian-friendly markdown.
  - A new import of your old code is not required for this plan unless there are legacy behaviors you want preserved exactly.
  - The implementation should favor simple, deterministic rewrite of the egdo section over incremental text surgery, because that is the main way to
    avoid the fragility you ran into before.
  - When metadata is missing from a manually added task, the file date is the default source of truth.
