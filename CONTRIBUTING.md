# Contributing to DsaBench

Thanks for taking the time to contribute! This document keeps the process
lightweight and predictable.

## Development setup

```bash
git clone https://github.com/priyadip/dsabench.git
cd dsabench
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running checks locally

Everything CI runs, you can run locally:

```bash
ruff check .          # lint
black --check .       # formatting (run `black .` to fix)
pytest                # 198 tests, ~1 s
pytest --cov=bench    # with coverage
```

Please make sure all four are green before opening a pull request.

## Guidelines

- **Style** — code is formatted with Black (line length 100) and linted with
  Ruff (`E, F, I, UP, B, W`). Public functions carry Google-style docstrings
  and full type hints (the package ships `py.typed`).
- **Tests** — every behaviour change needs a test. Timing-sensitive tests
  should use sleeps of at most a few milliseconds so the suite stays fast.
- **Measurement code** — be careful inside `benchmark.py`, `profiler.py`,
  and `auto.py`: nothing may allocate or run Python-level calls inside the
  timed region. The rule is: warmups → clean timed runs → one separate
  instrumented pass.
- **Commits & PRs** — small, focused PRs review fastest. Reference the issue
  you're fixing, describe *why* as well as *what*, and add a CHANGELOG entry
  under `[Unreleased]`.

## Reporting bugs / requesting features

Use the issue templates. For bugs, a minimal reproducible snippet plus your
Python version and OS shortens the round-trip enormously.

## Release process (maintainers)

1. Update `version` in `pyproject.toml` and `src/bench/__init__.py`.
2. Move `[Unreleased]` entries into a new dated section in `CHANGELOG.md`.
3. Tag `vX.Y.Z`, push, and create a GitHub Release — the `publish.yml`
   workflow builds and uploads to PyPI via trusted publishing.

## Code of Conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).
