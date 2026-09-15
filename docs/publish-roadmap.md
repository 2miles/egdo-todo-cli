# Egdo Publish Roadmap

This roadmap tracks the work that remains before Egdo's first release and records a small
set of possible later features. Current behavior is documented in the
[README](../README.md), [guide](guide.md), and [command reference](command-reference.md).

## Scope Boundary

Keep Egdo focused on a calm, local, Markdown-backed daily task journal. Add major
capabilities such as recurrence, synchronization, notifications, or extensibility only after
repeated real-world demand.

Treat recurrence as a storage-model change, not a simple convenience feature: it introduces
identity, duplication, completion, editing, and history semantics.

## First GitHub Release

1. Test the exact GitHub installation, upgrade, and uninstall workflow in an isolated
   environment:

   ```bash
   pipx install git+https://github.com/2miles/egdo-todo-cli.git
   ```

2. Replace the README's editable user-installation instructions with the tested GitHub
   command. Keep contributor setup and build instructions in the
   [build and installation guide](build-vs-install.md), and document how users upgrade.
3. Finalize the `0.1.0` changelog and package metadata.
4. Build the final wheel and source distribution, then repeat the clean-install checks from
   the build and installation guide against those exact artifacts.
5. Add a concise GitHub project description, usage example, and relevant repository topics.
6. Tag the release commit as `v0.1.0` and create the first GitHub release.
7. Use the released version and gather feedback before selecting another feature.

## PyPI Later

Consider PyPI only after the GitHub installation and upgrade workflow has been used in
practice:

1. Check whether the package name `egdo` is available.
2. Rebuild and verify the wheel, source distribution, and package metadata.
3. Test the final artifacts in a clean environment.
4. Publish the artifacts and replace the README's GitHub command with:

   ```bash
   pipx install egdo
   ```

5. Test and document the corresponding upgrade and uninstall commands.
