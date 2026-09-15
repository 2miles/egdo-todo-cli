# Building and Installing Egdo

Python packaging separates environments, installation, and distribution builds. Egdo is
pure Python, so a build creates installable archives rather than a standalone executable.

## Command Comparison

| Command | Result | Use it for |
| --- | --- | --- |
| `python3 -m venv .venv` | Creates an isolated Python environment | Initial contributor setup |
| `python -m pip install -e .` | Links the environment to the working source | Development without build tooling |
| `python -m pip install -e '.[dev]'` | Links the source and installs development extras | Normal Egdo development |
| `python -m pip install .` | Builds and installs a fixed source snapshot | CI and source-install checks |
| `python -m build` | Writes a wheel and source distribution to `dist/` | Preparing release artifacts |
| `python -m pip install dist/egdo-*.whl` | Installs the already-built wheel | Validating what users will receive |
| `python -m pip install dist/egdo-*.tar.gz` | Builds and installs from the source distribution | Validating downstream source builds |
| `pipx install egdo` | Installs a published CLI in its own managed environment | Future end-user installation |

Use `python -m pip` rather than a bare `pip` while developing. This makes it explicit which
Python environment receives the installation.

## Editable Installs

The `-e` option means editable. Instead of copying Egdo's package into `.venv`, the
installation points at `src/` in the repository:

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

Changes to Python files are therefore visible on the next invocation:

```bash
.venv/bin/egdo --help
```

The argument `.[dev]` has two parts:

- `.` installs the project described by the current directory's `pyproject.toml`.
- `[dev]` installs the optional packages under `[project.optional-dependencies].dev`.

Reinstall after changing dependencies, optional extras, entry points, or other packaging
metadata. Ordinary edits under `src/` do not require reinstallation.

## Fixed Source Installs

```bash
python -m pip install .
```

Pip builds the current checkout in a temporary location and installs a fixed copy. Later
source edits are not reflected in that environment. Egdo's CI uses this form because it
checks that a clean checkout can be packaged and installed, but it does not validate a wheel
previously created in `dist/`.

## Distribution Builds

```bash
.venv/bin/python -m build
```

The build runs in isolated temporary environments using the backend requirements declared
in `pyproject.toml`. It creates two files and does not install either one:

```text
dist/
├── egdo-0.1.0-py3-none-any.whl
└── egdo-0.1.0.tar.gz
```

- The wheel is a prepared installation archive. Pip can install it without rebuilding Egdo.
- The source distribution, or sdist, contains the publishable source. Pip builds a wheel from
  it before installation.

The version embedded in both filenames comes from `src/egdo/__init__.py`. Files under
`dist/` are generated artifacts and are ignored by Git.

Avoid `python -m build --no-isolation` for normal release builds. It relies on whatever build
tools happen to be installed locally and can conceal an incomplete `pyproject.toml`.

## Recommended Workflows

### Initial contributor setup

From the repository root, using any supported Python interpreter:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e '.[dev]'
```

Use a versioned interpreter such as `python3.14` in the first command when `python3` does not
refer to the version you intend to use.

### Daily development

Edit the source through the editable installation, then run:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall src tests
.venv/bin/egdo --version
```

There is no reason to rebuild a wheel after every code change.

### Continuous integration

GitHub Actions creates a fresh environment for each supported Python version, runs
`python -m pip install .`, and then runs the test and compilation checks. CI verifies source
installation and interpreter compatibility; it does not publish anything.

### Release preparation

After updating the version and changelog, run the standard checks and build both artifacts:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall src tests
.venv/bin/python -m build
```

Then install the wheel in a newly created environment rather than the editable development
environment:

```bash
python3 -m venv /tmp/egdo-wheel-test
/tmp/egdo-wheel-test/bin/python -m pip install dist/egdo-*.whl
/tmp/egdo-wheel-test/bin/egdo --version
/tmp/egdo-wheel-test/bin/egdo --help
```

This catches missing package files, invalid metadata, broken entry points, and undeclared
runtime dependencies that an editable installation can hide. Repeat with the sdist when
validating source-distribution installation.

### End-user installation

Until a public installation path is chosen, the README's editable installation from a local
clone remains the documented option. After publication, `pipx` is the preferred shape for a
command-line application because it manages a dedicated environment while exposing `egdo`
on the user's `PATH`:

```bash
pipx install egdo
```

Do not advertise that command until the `egdo` package is actually published at the named
package index.
