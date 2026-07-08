# Publishing DsaBench — step-by-step

A one-time checklist for taking this folder to GitHub and PyPI.
(The name `dsabench` was verified available on PyPI.)

## 0. Personalise

Replace the `priyadip` placeholder with your GitHub username everywhere:

```bash
# from the project root — macOS users: use  sed -i '' -e ...
grep -rl "priyadip" --include="*.md" --include="*.toml" --include="*.yml" . \
  | xargs sed -i "s/priyadip/your-github-username/g"
```

Optionally add your email in `pyproject.toml` under `[project] authors`.

## 1. Sanity-check locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && black --check . && pytest      # expect: 198 passed
python -m build                                # builds dist/*.whl and *.tar.gz
```

## 2. Push to GitHub

```bash
git init
git add .
git commit -m "dsabench 0.1.0 — one-line benchmarking for DSA"
git branch -M main
# create an empty repo named dsabench on github.com first, then:
git remote add origin git@github.com:your-github-username/dsabench.git
git push -u origin main
```

CI (`.github/workflows/ci.yml`) runs automatically: ruff + black, then the
test suite on Python 3.10–3.13.

## 3. Publish to PyPI — recommended path (trusted publishing, no tokens)

1. Create an account at https://pypi.org and enable 2FA.
2. On PyPI: **Your account → Publishing → Add a new pending publisher**
   - PyPI project name: `dsabench`
   - Owner: `your-github-username` · Repository: `dsabench`
   - Workflow name: `publish.yml` · Environment: `pypi`
3. On GitHub: repo **Settings → Environments → New environment** named `pypi`.
4. Create a release: **Releases → Draft a new release** → tag `v0.1.0` →
   publish. The `publish.yml` workflow builds and uploads automatically.

## 3b. Alternative: manual upload with an API token

```bash
pip install twine
python -m build
twine upload dist/*        # paste a PyPI API token (username: __token__)
```

## 4. (Optional but wise) dry-run on TestPyPI first

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --no-deps dsabench
```

## 5. Releasing future versions

1. Bump `version` in `pyproject.toml` **and** `src/bench/__init__.py`.
2. Move `[Unreleased]` notes into a new section in `CHANGELOG.md`.
3. Commit, tag `vX.Y.Z`, push, create a GitHub Release → auto-publish.
