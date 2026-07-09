"""Export benchmark results to JSON, CSV, and Markdown."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from .exceptions import ExportError
from .types import BenchmarkResult, ComparisonResult, ComplexityResult, SpaceComplexityResult

__all__ = ["to_json", "to_csv", "to_markdown", "export_result", "auto_export"]

Exportable = BenchmarkResult | ComparisonResult | ComplexityResult | SpaceComplexityResult

_SUFFIXES = {".json": "json", ".csv": "csv", ".md": "markdown", ".markdown": "markdown"}


def to_json(obj: Exportable) -> str:
    """Serialise *obj* to a pretty-printed JSON string.

    Args:
        obj: A benchmark, comparison, or complexity result.

    Returns:
        UTF-8 friendly JSON text.
    """
    return json.dumps(obj.to_dict(), indent=2, default=str)


def _flatten(prefix: str, value: Any, rows: list[tuple[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, sub in value.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), sub, rows)
    elif isinstance(value, (list, tuple)):
        rows.append((prefix, ";".join(str(v) for v in value)))
    else:
        rows.append((prefix, value))


def to_csv(obj: Exportable) -> str:
    """Serialise *obj* to CSV text.

    Benchmark results become ``metric,value`` rows; comparisons become one
    ranked row per candidate; complexity estimates become ``n,time_ns`` rows.

    Args:
        obj: A benchmark, comparison, or complexity result.

    Returns:
        CSV text (with header row).
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    if isinstance(obj, BenchmarkResult):
        writer.writerow(["metric", "value"])
        rows: list[tuple[str, Any]] = []
        _flatten("", obj.to_dict(), rows)
        for key, value in rows:
            writer.writerow([key, "" if value is None else value])
    elif isinstance(obj, ComparisonResult):
        writer.writerow(
            [
                "rank",
                "name",
                "average_ns",
                "fastest_ns",
                "median_ns",
                "stdev_ns",
                "peak_memory_bytes",
                "relative",
                "error",
            ]
        )
        for entry in obj.entries:
            res = entry.result
            t = res.timing
            writer.writerow(
                [
                    entry.rank,
                    entry.name,
                    t.average_ns if t else "",
                    t.fastest_ns if t else "",
                    t.median_ns if t else "",
                    t.stdev_ns if t else "",
                    res.peak_memory_bytes if res.peak_memory_bytes is not None else "",
                    "" if entry.relative != entry.relative else entry.relative,  # NaN check
                    res.exception.type_name if res.exception else "",
                ]
            )
    elif isinstance(obj, ComplexityResult):
        writer.writerow(["n", "time_ns"])
        for size, t_ns in zip(obj.sizes, obj.times_ns, strict=True):
            writer.writerow([size, t_ns])
    elif isinstance(obj, SpaceComplexityResult):
        writer.writerow(["n", "peak_bytes"])
        for size, peak in zip(obj.sizes, obj.peak_bytes, strict=True):
            writer.writerow([size, peak])
    else:  # pragma: no cover - defensive
        raise ExportError(f"Cannot export object of type {type(obj).__name__}")
    return buffer.getvalue()


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def to_markdown(obj: Exportable) -> str:
    """Serialise *obj* to a Markdown document.

    Args:
        obj: A benchmark, comparison, or complexity result.

    Returns:
        Markdown text with a heading and a table.
    """
    if isinstance(obj, BenchmarkResult):
        rows: list[tuple[str, Any]] = []
        _flatten("", obj.to_dict(), rows)
        body = _md_table(
            ["Metric", "Value"],
            [[key, "—" if value is None else str(value)] for key, value in rows],
        )
        return f"# Benchmark — {obj.name}\n\n{body}\n"
    if isinstance(obj, ComparisonResult):
        rows_c = []
        for entry in obj.entries:
            res = entry.result
            t = res.timing
            rows_c.append(
                [
                    str(entry.rank),
                    entry.name,
                    f"{t.average_ns:.1f}" if t else "—",
                    f"{t.fastest_ns:.1f}" if t else "—",
                    f"{entry.relative:.2f}×" if entry.relative == entry.relative else "—",
                    res.exception.type_name if res.exception else "",
                ]
            )
        body = _md_table(
            ["Rank", "Name", "Average (ns)", "Fastest (ns)", "Relative", "Error"], rows_c
        )
        match = obj.outputs_match
        note = (
            "\n\nAll outputs match."
            if match is True
            else "\n\n**Warning:** outputs differ." if match is False else ""
        )
        return f"# Comparison — args {obj.args_repr}\n\n{body}{note}\n"
    if isinstance(obj, ComplexityResult):
        body = _md_table(
            ["n", "Time (ns)"],
            [[f"{s}", f"{t:.1f}"] for s, t in zip(obj.sizes, obj.times_ns, strict=True)],
        )
        best = obj.best.label if obj.fits else "—"
        return f"# Complexity — {obj.name}\n\nEstimated: **{best}**\n\n{body}\n"
    if isinstance(obj, SpaceComplexityResult):
        body = _md_table(
            ["n", "Peak Memory (bytes)"],
            [[f"{s}", f"{p:.1f}"] for s, p in zip(obj.sizes, obj.peak_bytes, strict=True)],
        )
        best = obj.best.label if obj.fits else "—"
        return f"# Space Complexity — {obj.name}\n\nEstimated: **{best}**\n\n{body}\n"
    raise ExportError(f"Cannot export object of type {type(obj).__name__}")  # pragma: no cover


def export_result(
    obj: Exportable,
    path: str | Path,
    format: str | None = None,  # noqa: A002 - mirrors common API naming
) -> Path:
    """Write *obj* to *path* in the given (or inferred) format.

    Args:
        obj: A benchmark, comparison, or complexity result.
        path: Destination file; parent directories are created.
        format: ``"json"``, ``"csv"``, ``"md"``/``"markdown"``. When omitted
            the format is inferred from the file suffix.

    Returns:
        The resolved :class:`pathlib.Path` written.

    Raises:
        ExportError: On unknown formats/suffixes or write failures.
    """
    target = Path(path)
    fmt = (format or _SUFFIXES.get(target.suffix.lower(), "")).lower()
    if fmt == "md":
        fmt = "markdown"
    if fmt not in {"json", "csv", "markdown"}:
        raise ExportError(
            f"Cannot infer export format for {target.name!r}; "
            "use .json/.csv/.md or pass format=..."
        )
    if fmt == "json":
        text = to_json(obj)
    elif fmt == "csv":
        text = to_csv(obj)
    else:
        text = to_markdown(obj)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Failed to write {target}: {exc}") from exc
    return target


def auto_export(result: Exportable, config: Config) -> Path | None:
    """Export *result* according to ``config.export`` settings.

    Args:
        result: The result to export.
        config: Active configuration (``export`` format and ``export_dir``).

    Returns:
        The path written, or ``None`` when auto-export is disabled.
    """
    if not config.export:
        return None
    fmt = "markdown" if config.export.lower() == "md" else config.export.lower()
    ext = {"json": ".json", "csv": ".csv", "markdown": ".md"}[fmt]
    name = getattr(result, "name", None) or type(result).__name__
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(name))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path(config.export_dir) / f"bench-{safe}-{stamp}{ext}"
    return export_result(result, target, format=fmt)
