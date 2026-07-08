"""06 — run() for silent results, exports (json/csv/md), matplotlib plots."""

from pathlib import Path

from bench import compare, export_result, run

OUT = Path("bench_output")


def workload(n: int) -> int:
    return sum(i * i for i in range(n))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)

    result = run(workload, args=(50_000,))  # never prints, never raises
    for suffix in (".json", ".csv", ".md"):
        path = export_result(result, OUT / f"workload{suffix}")
        print("wrote", path)

    cmp_result = compare(
        ("sum-genexpr", lambda n: sum(i * i for i in range(n))),
        ("sum-map", lambda n: sum(map(lambda i: i * i, range(n)))),
        args=(50_000,),
        quiet=True,
    )
    export_result(cmp_result, OUT / "comparison.json")

    try:
        from bench import plot_comparison, plot_memory, plot_runtime

        print("plot:", plot_runtime(result, path=OUT / "runtime.png"))
        print("plot:", plot_memory(result, path=OUT / "memory.png"))
        print("plot:", plot_comparison(cmp_result, path=OUT / "comparison.png"))
    except Exception as exc:  # GraphError without matplotlib
        print(f"(skipping plots: {exc})")
