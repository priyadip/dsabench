"""Whirlwind tour — run `python examples/demo.py` for the full show."""

import bench


def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


def fib_fast(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


if __name__ == "__main__":
    print("=" * 60, "\n1. One-line benchmark\n", "=" * 60, sep="")
    bench.bench(fib, 18)

    print("=" * 60, "\n2. Head-to-head comparison\n", "=" * 60, sep="")
    bench.compare(("Recursive", fib), ("Iterative", fib_fast), args=(18,))

    print("=" * 60, "\n3. Empirical complexity\n", "=" * 60, sep="")
    bench.estimate_complexity(fib_fast, sizes=[1_000, 2_000, 4_000, 8_000])

    print("=" * 60, "\n4. auto() magic\n", "=" * 60, sep="")
    bench.auto()
    fib_fast(50_000)
    fib_fast(100_000)
    bench.stop_auto()
