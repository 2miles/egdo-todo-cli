# Example Notes

This directory is a populated, uninitialized Egdo journal for use as a demo or playground.
It contains completed history from August 2026 and active work centered on September 11,
2026. Together, the two monthly files demonstrate tasks, notes, tags, priorities, nesting,
carry-forward dates, and future scheduling.

Copy the directory somewhere outside the repository, enter the copied directory, and adopt
the existing archive as a new project:

```bash
cp -R example-notes ~/Notes/egdo-demo
cd ~/Notes/egdo-demo
egdo init Demo
egdo
```

The repository copy intentionally has no `.egdo.toml`, so initializing your copy does not
modify the example or assume a particular project name. If you use it after the sample dates,
Egdo will carry its unfinished work into the current day as it would in a real journal.

Useful commands to try include:

```bash
egdo
egdo list --completed
egdo list --future
egdo done
egdo project list
```

When you are finished, unregister the temporary project before deleting your copied
directory:

```bash
egdo project remove Demo
```

The command removes only the registry entry. You can then delete the copied directory
without leaving a stale project behind.
