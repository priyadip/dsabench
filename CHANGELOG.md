# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-09

### Added
- `estimate_complexity()` candidate models extended beyond O(1)…O(n³) with
  `O(log log n)`, `O(2ⁿ)`, `O(3ⁿ)`, `O(eⁿ)`, and `O(n!)` — exponential and
  factorial-time algorithms (e.g. brute-force recursion) now get an
  accurate label instead of being misfit against the largest polynomial.
- `models=` parameter on `estimate_complexity()` to supply a custom
  candidate list, replacing the built-in set entirely.
- `bench.complexity.COMPLEXITY_MODELS` — the built-in candidate list,
  importable and extendable: `models=COMPLEXITY_MODELS + [...]`.
- Model-builder DSL in `bench.complexity`: `const()`, `poly()`,
  `polylog()`, `loglog()`, `exp_base()`, `factorial()`, `raised()`, and
  `compose()` for assembling arbitrary shapes (e.g. `O(n⁴log²n)` via
  `compose(poly(4), polylog(0, 2))`, or a variable exponent via `raised()`)
  without hand-writing raw lambdas.
- Any candidate model that overflows or diverges at the given sizes
  (e.g. `170!` exceeding float range) is now silently excluded from the
  fit instead of crashing; `estimate_complexity()` raises `BenchError`
  only if every candidate model is non-viable at the given sizes.

## [0.1.1] - 2026-07-09

### Changed
- Removed the decorative lightning-bolt (⚡) glyph from report/summary
  titles printed by `bench()`, `compare()`, `estimate_complexity()`, and
  `auto()`. Status glyphs (✓ / ⚠) are unchanged. README examples are
  unaffected.

## [0.1.0] - 2026-07-08

### Added
- `bench(func, *args, **kwargs)` — one-line benchmarking that prints a rich
  report and returns the function's original return value.
- `@benchmark` decorator (bare and parameterised forms) with `last_result`
  and `original` attributes; a shared re-entrancy guard keeps recursive and
  nested decorated calls un-instrumented, so exactly one report is produced
  per outermost call.
- `auto()` / `stop_auto()` — automatic benchmarking of every user-defined
  function call, with live per-call lines, a ranked summary table, and
  fnmatch `include` / `exclude` filters.
- Metrics: wall time (fastest / slowest / average / median / std dev /
  95th percentile), CPU time and CPU %, peak / current / delta memory via
  `tracemalloc`, process RSS, function calls, recursive calls, max recursion
  depth, and GC collections.
- Modes: `fast` (1 run), `default` (10 runs + 1 warmup),
  `accurate` (100 runs + 5 warmups) — plus explicit `repeat=` / `warmup=`.
- `compare()` — ranked head-to-head table with relative slowdowns and
  output-equality checking.
- `estimate_complexity()` — empirical Big-O fitting over
  O(1) … O(n³) with R² scores.
- Exports: JSON, CSV, and Markdown via `export_result()` /
  `configure(export=...)`.
- Optional matplotlib graphs: `plot_runtime()`, `plot_memory()`,
  `plot_comparison()` (install extra: `dsabench[viz]`).
- Support for coroutine functions (`bench_async` inside running loops),
  generator functions (fresh generator returned to the caller), and
  threaded code (CPU % above 100 is reported faithfully).
- Fully typed (`py.typed`), Google-style docstrings, 198-test suite,
  GitHub Actions CI (ruff + black + pytest on Python 3.10–3.13) and
  trusted-publishing release workflow.

[Unreleased]: https://github.com/priyadip/dsabench/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/priyadip/dsabench/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/priyadip/dsabench/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/priyadip/dsabench/releases/tag/v0.1.0
