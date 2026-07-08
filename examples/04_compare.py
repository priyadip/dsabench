"""04 — compare(): three Fibonacci strategies, ranked, outputs verified."""

from bench import compare


def fib_memo(n: int) -> int:
    cache: dict[int, int] = {}

    def go(k: int) -> int:
        if k < 2:
            return k
        if k not in cache:
            cache[k] = go(k - 1) + go(k - 2)
        return cache[k]

    return go(n)


def fib_tab(n: int) -> int:
    if n < 2:
        return n
    table = [0] * (n + 1)
    table[1] = 1
    for i in range(2, n + 1):
        table[i] = table[i - 1] + table[i - 2]
    return table[n]


def fib_space(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


if __name__ == "__main__":
    result = compare(
        ("Memoization", fib_memo),
        ("Tabulation", fib_tab),
        ("Two variables", fib_space),
        args=(30,),
    )
    print(f"\nWinner: {result.winner.name}")
    print(f"Outputs match: {result.outputs_match}")
