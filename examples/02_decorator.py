"""02 — @benchmark: every call reports; recursion stays correct."""

from bench import benchmark


@benchmark
def fib(n: int) -> int:
    # Recursive calls run the ORIGINAL function (shared re-entrancy guard),
    # so you get ONE report per outer call and true recursion metrics.
    return n if n < 2 else fib(n - 1) + fib(n - 2)


@benchmark(mode="accurate", label="sum-of-squares")
def sum_squares(n: int) -> int:
    return sum(i * i for i in range(n))


if __name__ == "__main__":
    fib(15)
    print("last result, programmatically:", fib.last_result.average_ms, "ms avg")

    sum_squares(10_000)

    # Need the raw function (e.g. inside another benchmark)? It's right here:
    assert fib.original(10) == 55
