"""03 — auto(): benchmark every user-defined function you call, hands-free."""

import json

from bench import auto, stop_auto


def parse(payload: str) -> dict:
    return json.loads(payload)  # stdlib internals are NOT captured


def transform(data: dict) -> dict:
    return {k: v * 2 for k, v in data.items()}


def pipeline() -> dict:
    return transform(parse('{"a": 1, "b": 2}'))


if __name__ == "__main__":
    auto()  # live line per top-level user call

    for _ in range(3):
        pipeline()

    stop_auto()  # ranked summary table

    # Only care about some functions? Use fnmatch patterns:
    auto(live=False, include=["trans*"])
    pipeline()
    report = stop_auto()
    print("captured:", [r.name for r in report.records])
