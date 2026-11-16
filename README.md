# upgrade-guard-helper

Diff default parameters and config constants (**knobs**) between two versions of a dependency, and list the ones whose defaults changed.

A knob, as defined by [fitzyracing1/knobs](https://github.com/fitzyracing1/knobs), is a default parameter or setting that can change silently between versions and change how your system behaves. This helper builds on that definition and on [knoblog-upgrade-guard](https://github.com/fitzyracing1/knoblog-upgrade-guard) / [knobs-watch](https://github.com/fitzyracing1/knobs-watch). It is **rule-based** (Python `ast` plus simple JavaScript regular expressions, no AI). Local trees are compared fully offline. Downloading a PyPI sdist or npm tarball is optional.

Sponsor: [github.com/sponsors/fitzyracing1](https://github.com/sponsors/fitzyracing1).

## Install

```bash
pipx install git+https://github.com/fitzyracing1/upgrade-guard-helper
```

Or from a checkout:

```bash
pip install -e .
```

## Usage

Compare two source trees (the originals are never overwritten):

```bash
upgrade-guard-helper --old path/to/requests-2.28.0 --new path/to/requests-2.31.0
python -m upgrade_guard_helper --old ./old --new ./new
```

Write the report to a new file:

```bash
upgrade-guard-helper --old ./old --new ./new --write knobs.tidy.txt
```

Optionally download two published versions, then compare them (needs network):

```bash
upgrade-guard-helper --package requests --old-version 2.28.0 --new-version 2.31.0
upgrade-guard-helper --ecosystem npm --package ms --old-version 2.1.2 --new-version 2.1.3
```

The process exits `1` when any knob was added, removed, or changed, and `0` when none moved.

## What is extracted

**Python** (`*.py`), via `ast`:

- Function and `__init__` default arguments whose values are literals
- Public class attributes and dataclass-style annotated defaults
- Module-level `UPPER_CASE` constants

**JavaScript / TypeScript** (`*.js`, `*.mjs`, `*.cjs`, `*.ts`), via regular expressions:

- Function and arrow-function default parameters
- `const`/`let` values named like defaults, timeouts, limits, or `UPPER_CASE`
- `defaultConfig` / `options` / `DEFAULTS` object literals, including one level of nesting

Non-literal defaults (`os.getenv(...)`, function calls) are skipped, because they are not a checkable knob value.

## License

MIT. Copyright (c) 2026 Joshua Almeida (fitzyracing1).
