# Egdo Publish Roadmap

This document captures the work needed to move `egdo` from a working personal tool to something ready to share publicly on GitHub and potentially package for wider use later.

## Goal

Make `egdo` solid enough that someone outside this repo can:

- understand what it does quickly
- install it without friction
- use it without hitting avoidable parser or UX problems
- trust the markdown workflow and file model

## GitHub Readiness

### README polish

- tighten the top of the README so the project value is obvious in the first few paragraphs
- add a short "why this exists" pitch near the top
- make the usage examples more copy-paste friendly
- make sure the manual-editing workflow is clearly explained
- make sure the `.venv` workflow is clear and consistent throughout

### Project metadata

- choose and add a license
- state supported Python versions clearly in the README and packaging metadata
- confirm versioning approach for early releases such as `0.1.x`
- add a simple changelog or release-notes file

### Repository hygiene

- review `.gitignore` for anything else that should be excluded
- make sure the repo layout is clean and understandable to a new visitor
- decide whether planning documents should stay in the root or move into a `docs/` folder later

## Product Hardening

### Markdown safeguards

- improve error messages when the managed section is malformed
- make parser failures point to the likely problem instead of raising generic exceptions
- decide how tolerant `egdo` should be of partially malformed task blocks
- keep the parser permissive enough for manual editing without making behavior ambiguous

### CLI UX

- review `--help` output for each command
- add clearer help text and examples where the current CLI is too terse
- decide whether common mistakes like `egdo --add` deserve a friendlier error path
- make success and failure messages more consistent

### Edge cases

- review rollover behavior around sparse files and unusual manual edits
- verify behavior when files contain unexpected content inside the managed section
- verify behavior when tasks are manually checked or unchecked after creation

## Test Expansion

- add tests for malformed or partially malformed markdown in the managed section
- add tests for unusual manual edits and recovery behavior
- add tests for files with extra notes before and after the managed section
- add tests for month and year boundaries if they are not already covered well enough
- add tests focused on user-facing error messages where failures are intentional

## Packaging Path

### GitHub first

- publish the repo once the README, license, and basic docs are ready
- include a short project description and usage example in the repo metadata
- treat the first public state as a clean `0.1.x` release candidate

### PyPI later

- check whether the package name `egdo` is available
- verify install flow in a clean virtual environment
- build a source distribution and wheel
- confirm the package metadata is complete before uploading
- publish to PyPI only after the install and help experience feels stable

## Suggested Order

1. Polish README and add license.
2. Improve parser error handling and user-facing CLI messages.
3. Expand tests around malformed markdown and manual edits.
4. Clean up packaging metadata and document supported Python versions.
5. Publish to GitHub.
6. Evaluate PyPI publication after one more install pass.
