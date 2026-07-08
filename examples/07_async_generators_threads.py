"""07 — coroutines, generators, and threaded code all just work."""

import asyncio
import threading

from bench import bench, bench_async


async def fetch(x: int) -> int:
    await asyncio.sleep(0.005)
    return x * 2


def squares(n: int):
    for i in range(n):
        yield i * i


def parallel_sum() -> int:
    results: list[int] = []

    def work() -> None:
        results.append(sum(range(200_000)))

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return sum(results)


if __name__ == "__main__":
    # Coroutine outside a loop: bench() awaits it for you.
    print("fetch ->", bench(fetch, 21, repeat=3, warmup=0))

    # Inside a running loop you'd write:  value = await bench_async(fetch, 21)
    print("via loop ->", asyncio.run(bench_async(fetch, 21, repeat=3, warmup=0)))

    # Generator functions: timing consumes it; YOU get a fresh generator back.
    gen = bench(squares, 5, repeat=2, warmup=0)
    print("generator items:", list(gen))

    # Threads: CPU% above 100 is real signal (process_time sums all threads).
    print("parallel sum ->", bench(parallel_sum, repeat=3, warmup=1))
