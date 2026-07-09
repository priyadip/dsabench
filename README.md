# ⚡ DsaBench

**One-line benchmarking for DSA, competitive programming, and interview prep.**

[![CI](https://github.com/priyadip/dsabench/actions/workflows/ci.yml/badge.svg)](https://github.com/priyadip/dsabench/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dsabench.svg)](https://pypi.org/project/dsabench/)
[![Python](https://img.shields.io/pypi/pyversions/dsabench.svg)](https://pypi.org/project/dsabench/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Typed](https://img.shields.io/badge/typing-py.typed-blue.svg)](https://peps.python.org/pep-0561/)

You wrote two solutions to a problem. Which one is faster? How much memory does
the recursive one eat? How deep does it recurse? Is your "optimised" version
actually O(n log n)?

`dsabench` answers all of that with **one line** — no boilerplate, no
`timeit` incantations, no manual `tracemalloc` bookkeeping:

```python
from bench import bench

answer = bench(solve, arr, target)   # runs it, prints the report below,
print(answer)                        # ...and still hands back the real answer
```

```text
╭─ ⚡ Benchmark Report ──────────────────────────────────╮
│                                                        │
│  Function               solve                          │
│  Arguments              ([3, 1, 2], 4)                 │
│  Mode                   default · 10 runs (+1 warmup)  │
│  Return                 [1, 3]                         │
│  Time                                                  │
│    Fastest              19.293 µs                      │
│    Average              22.169 µs                      │
│    Median               19.457 µs                      │
│    Slowest              46.048 µs                      │
│    Std Dev              8.393 µs                       │
│    95th pct             34.303 µs                      │
│  Memory                                                │
│    Peak                 2.66 KB                        │
│    Current              448 B                          │
│    Delta                448 B                          │
│    Process RSS          24.95 MB                       │
│  CPU                                                   │
│    CPU time             22.680 µs                      │
│    CPU %                102.3%                         │
│  Calls                                                 │
│    Function calls       465                            │
│    Recursive calls      464                            │
│    Max recursion depth  12                             │
│    GC collections       0                              │
│                                                        │
╰────────────────────────────────── 2026-07-08T16:53:33 ─╯
```

## Install

```bash
pip install dsabench            # core (only dependency: rich)
pip install "dsabench[viz]"     # + matplotlib graphs
```

Python 3.10+. Fully typed (`py.typed`), Apache-2.0 licensed.

## Three ways to use it

### 1 · Function call — `bench()`

```python
from bench import bench

def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

value = bench(fib, 20)                      # full report, returns 6765
value = bench(fib, 20, mode="accurate")     # 100 runs + 5 warmups
value = bench(fib, 20, repeat=50, warmup=2) # explicit control
value = bench(fib, 20, quiet=True)          # measure silently
```

`bench()` is transparent: whatever the function returns, you get back —
including for generator functions (you receive a *fresh* generator) and
coroutine functions (awaited for you when no event loop is running).

### 2 · Decorator — `@benchmark`

```python
from bench import benchmark

@benchmark                       # bare form
def solve(nums):
    return sorted(nums)

@benchmark(mode="accurate")      # parameterised form
def solve_fast(nums):
    return sorted(nums)

solve([3, 1, 2])                 # report prints on every call
solve.last_result.average_ms     # latest BenchmarkResult, programmatically
solve.original([3, 1, 2])        # raw, un-instrumented function
```

Recursive and nested decorated functions are handled correctly: inner calls
run the **original** function, so you get exactly one report per outermost
call and true recursion statistics (a `@benchmark`-ed `fib(10)` reports 177
calls at depth 10, not a storm of nested reports).

### 3 · Automatic — `auto()`

```python
from bench import auto, stop_auto

auto()                # from here on, every user-defined function you call
                      # is timed and printed live — stdlib & site-packages
                      # are ignored automatically

run_my_pipeline()

stop_auto()           # prints a ranked summary table (calls, total, avg, min, max)
```

Filter what gets captured with fnmatch patterns:
`auto(include=["solve*"])` or `auto(exclude=["helper_*"])`.

## Compare solutions head-to-head

```python
from bench import compare

result = compare(
    ("Memoization", fib_memo),
    ("Tabulation",  fib_tab),
    ("Matrix power", fib_matrix),
    args=(30,),
)
result.winner.name        # "Matrix power"
```

```text
⚡ Comparison — args (30)
╭──────┬──────────────┬──────────┬──────────┬──────────┬──────────┬──────────────╮
│ Rank │ Name         │  Average │  Fastest │  Std Dev │ Peak Mem │     Relative │
├──────┼──────────────┼──────────┼──────────┼──────────┼──────────┼──────────────┤
│    1 │ Matrix power │ 11.9 µs  │ 10.8 µs  │ 1.1 µs   │  1.2 KB  │     baseline │
│    2 │ Memoization  │ 38.4 µs  │ 35.0 µs  │ 2.9 µs   │  9.8 KB  │ 3.22× slower │
│    3 │ Tabulation   │ 51.7 µs  │ 48.2 µs  │ 3.4 µs   │  2.1 KB  │ 4.34× slower │
╰──────┴──────────────┴──────────┴──────────┴──────────┴──────────┴──────────────╯
✓ all outputs match
```

`compare` also verifies that all candidates return **equal outputs** — the
fastest wrong answer is still wrong.

## Estimate Big-O empirically

```python
from bench import estimate_complexity

estimate_complexity(my_sort, sizes=[1_000, 2_000, 4_000, 8_000, 16_000],
                    args_for=lambda n: (random_list(n),))
```

```text
Estimated complexity: O(n log n)   (R² = 0.998)
```

Fits your measured times against O(1), O(log log n), O(log n), O(n), O(n log n),
O(n²), O(n³), O(2ⁿ), O(3ⁿ), O(eⁿ), and O(n!) by least squares and ranks them by
R². Treat it as a sanity check, not a proof — constant factors and caches are
real.

Need a shape that's not on the list — O(n⁴log²n), a variable exponent, anything?
Compose your own from `bench.complexity`'s builders and pass `models=`:

```python
from bench.complexity import COMPLEXITY_MODELS, polylog

custom = COMPLEXITY_MODELS + [("O(n⁴log²n)", polylog(4, 2))]
estimate_complexity(my_func, sizes=[...], models=custom)
```

## Estimate space complexity empirically

Same fitting machinery, but for **peak memory** instead of time — useful for
answering "is my DP table actually O(n²) in space, or did I accidentally make
it O(n³)?":

```python
from bench import estimate_space_complexity

estimate_space_complexity(build_dp_table, sizes=[50, 100, 200, 400, 800],
                          args_for=lambda n: (n,))
```

```text
Estimated space complexity: O(n²)   (R² = 0.9999)
```

Takes the same `models=` override and builder DSL as `estimate_complexity`.

## Export and plot

```python
from bench import run, export_result, plot_runtime

result = run(fib, args=(25,))                # like bench(), but returns the
                                             # BenchmarkResult and never prints
export_result(result, "fib.json")            # .json / .csv / .md by extension
plot_runtime(result, path="fib.png")         # needs dsabench[viz]
```

Or export everything automatically:

```python
import bench
bench.configure(export="json", export_dir="benchmarks/")
```

## Configuration

```python
import bench
bench.configure(repeat=100, warmup=5, color=True, memory=True,
                cpu=True, export="json")
```

| Option             | Default     | Meaning                                              |
| ------------------ | ----------- | ---------------------------------------------------- |
| `mode`             | `"default"` | `fast` (1 run) / `default` (10+1) / `accurate` (100+5) |
| `repeat`           | mode        | Timed repetitions (overrides mode)                   |
| `warmup`           | mode        | Untimed warmup runs (overrides mode)                 |
| `color`            | `True`      | Colored Rich output                                  |
| `memory`           | `True`      | Track memory via `tracemalloc`                       |
| `cpu`              | `True`      | Track CPU time / CPU %                               |
| `profile`          | `True`      | Track calls / recursion / GC                         |
| `quiet`            | `False`     | Suppress printed reports                             |
| `raise_exceptions` | `True`      | Re-raise exceptions from benchmarked code            |
| `export`           | `None`      | Auto-export every result: `"json"`/`"csv"`/`"md"`    |
| `export_dir`       | `"."`       | Where auto-exports are written                       |
| `precision`        | `3`         | Decimal places in time formatting                    |
| `show_args`        | `True`      | Include the arguments line in reports                |

`reset_config()` restores the defaults; `get_config()` returns the active
configuration.

## How measurement works (and why you can trust it)

- **Warmups first** (never timed) — caches warm, imports settled.
- **Clean timed runs** using `time.perf_counter_ns` (wall) and
  `time.process_time_ns` (CPU). Nothing else happens inside the timed region —
  no memory tracking, no call counting, no allocation by dsabench itself.
- **One separate instrumented pass** afterwards collects memory
  (`tracemalloc`), call counts, recursion depth, and GC activity, so the
  instrumentation overhead never pollutes your timings.

That means the default mode calls your function **12 times**: 1 warmup +
10 timed + 1 instrumented. In `fast` mode it's a single call with everything
combined (numbers are slightly noisier — that's the trade-off).

Other honest details:

- CPU % can exceed 100% for multi-threaded code — `process_time_ns` sums all
  threads. That's signal, not a bug.
- On Windows, `time.process_time_ns` only advances once per system timer tick
  (~15.6 ms via `GetProcessTimes`), so functions faster than that will often
  report `CPU time: 0.000 ns` / `CPU %: 0.0%`. Trust the wall-clock numbers
  for anything sub-millisecond — that's a platform clock limitation, not a
  measurement bug.
- Call counting uses `sys.setprofile`, counts Python-level frames (stdlib
  included, cProfile-style), and excludes dsabench's own machinery. A
  recursion like `fib(10)` reports exactly 177 calls, 176 recursive, depth 10.
- For coroutine functions, call/recursion tracking is disabled (profile hooks
  and event loops don't mix reliably); timing and memory still work.
- `tracemalloc` sees Python allocations. C-extension allocations (NumPy
  buffers, etc.) show up in **Process RSS**, not in peak/delta.

## Jupyter & async

Inside a running event loop (Jupyter, async apps), `bench()` on a coroutine
can't call `asyncio.run` — use the awaitable form:

```python
value = await bench_async(fetch_data, url)
```

The `@benchmark` decorator works on `async def` functions out of the box.

## FAQ

**Why is the import called `bench` when the package is `dsabench`?**
`pip install dsabench`, `from bench import bench` — short at the call site,
unique on PyPI. Heads-up: the Frappe/ERPNext ecosystem ships a CLI tool also
distributed as `bench` on PyPI. Don't install that package into the same
environment as dsabench: both would own the `bench` import name and clash.

**Do warmup runs affect my numbers?** No — they're executed and discarded
before the timing loop.

**Why do I see 12 executions in default mode?** 1 warmup + 10 timed +
1 instrumented pass. Functions with side effects (appending to a list,
writing files) will apply them each time — benchmark pure functions, or pass
fresh inputs.

**Can it benchmark code that raises?** Yes. The exception is captured, shown
in the report, and re-raised by default (`configure(raise_exceptions=False)`
to suppress). `run()` never raises target exceptions; check `result.exception`.

**Is `auto()` production-safe?** It installs a `sys.setprofile` hook, which
slows everything down while active. It's a development and learning tool —
call `stop_auto()` when done.

**Timer resolution?** `perf_counter_ns` has nanosecond *units*; actual
resolution is platform-dependent (typically tens of ns). For micro-functions,
use `mode="accurate"` and read the median.

## Roadmap

- [ ] `bench.timeline()` — flame-graph style per-call timeline for `auto()`
- [ ] Statistical significance testing in `compare()` (Mann–Whitney U)
- [ ] `--bench` pytest plugin for inline regression benchmarks
- [ ] HTML report export
- [ ] Per-line memory attribution (top allocating lines from tracemalloc)

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Run
`ruff check . && black --check . && pytest` before pushing; all three are
enforced by CI on Python 3.10–3.13.

## License

[Apache-2.0](LICENSE) © 2026 Priyadip
