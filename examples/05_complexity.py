"""05 — estimate_complexity(): is it really O(n log n)?"""

import random

from bench import estimate_complexity


def my_sort(xs: list[int]) -> list[int]:
    return sorted(xs)


def slow_pairs(xs: list[int]) -> int:
    hits = 0
    for a in xs:  # O(n^2) on purpose
        for b in xs:
            hits += a < b
    return hits


if __name__ == "__main__":
    rng = random.Random(42)

    estimate_complexity(
        my_sort,
        sizes=[1_000, 2_000, 4_000, 8_000, 16_000],
        args_for=lambda n: ([rng.randrange(n) for _ in range(n)],),
    )

    estimate_complexity(
        slow_pairs,
        sizes=[100, 200, 400, 800],
        args_for=lambda n: (list(range(n)),),
    )
