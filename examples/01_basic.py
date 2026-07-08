"""01 — The one-liner: bench(func, *args) prints a report, returns the value."""

from bench import bench


def fib(n: int) -> int:
    """Deliberately naive recursive Fibonacci — great benchmarking fodder."""
    return n if n < 2 else fib(n - 1) + fib(n - 2)


if __name__ == "__main__":
    answer = bench(fib, 20)
    print(f"\nbench() handed back the real answer: fib(20) = {answer}")

    # Dial precision up or down without touching your function:
    bench(fib, 20, mode="fast")  # 1 combined run
    bench(fib, 20, repeat=50, warmup=3)  # explicit control
