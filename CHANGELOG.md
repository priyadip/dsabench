# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/priyadip/dsabench/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/priyadip/dsabench/releases/tag/v0.1.0
