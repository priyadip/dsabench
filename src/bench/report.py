"""Rich-powered terminal reports.

All console output produced by the package flows through this module so the
formatting stays consistent: a rounded panel for single benchmarks, a ranked
table for comparisons, and a fit table for complexity estimates.
"""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import Config
from .types import BenchmarkResult, ComparisonResult, ComplexityResult, SpaceComplexityResult
from .utils import format_bytes, format_time_ns

__all__ = [
    "get_console",
    "print_report",
    "print_comparison",
    "print_complexity",
    "print_space_complexity",
]


def get_console(config: Config) -> Console:
    """Return a :class:`rich.console.Console` honouring the color setting.

    Args:
        config: Active configuration.

    Returns:
        A console with syntax highlighting disabled (reprs stay verbatim).
    """
    return Console(no_color=not config.color, highlight=False)


def _grid() -> Table:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", no_wrap=True, min_width=18)
    grid.add_column()
    return grid


def _section(grid: Table, title: str, style: str = "bold cyan") -> None:
    grid.add_row(Text(title, style=style), Text(""))


def render_report(result: BenchmarkResult, config: Config) -> Panel:
    """Build the Rich panel for a single :class:`BenchmarkResult`.

    Args:
        result: The benchmark result to render.
        config: Active configuration (precision, argument display).

    Returns:
        A :class:`rich.panel.Panel` ready to print.
    """
    p = config.precision
    grid = _grid()

    grid.add_row("Function", Text(result.name, style="bold magenta"))
    if config.show_args and result.args_repr:
        grid.add_row("Arguments", Text(result.args_repr))
    warm = f" (+{result.warmup} warmup)" if result.warmup else ""
    runs = "run" if result.repeat == 1 else "runs"
    grid.add_row("Mode", Text(f"{result.mode.value} · {result.repeat} {runs}{warm}"))
    grid.add_row("Return", Text(result.return_repr))

    if result.timing is not None:
        t = result.timing
        _section(grid, "Time")
        grid.add_row("  Fastest", Text(format_time_ns(t.fastest_ns, p), style="green"))
        grid.add_row("  Average", Text(format_time_ns(t.average_ns, p), style="bold"))
        grid.add_row("  Median", Text(format_time_ns(t.median_ns, p)))
        grid.add_row("  Slowest", Text(format_time_ns(t.slowest_ns, p), style="yellow"))
        grid.add_row("  Std Dev", Text(format_time_ns(t.stdev_ns, p)))
        grid.add_row("  95th pct", Text(format_time_ns(t.p95_ns, p)))

    if result.memory is not None:
        m = result.memory
        _section(grid, "Memory")
        grid.add_row("  Peak", Text(format_bytes(m.peak_bytes), style="bold"))
        grid.add_row("  Current", Text(format_bytes(m.current_bytes)))
        grid.add_row("  Delta", Text(format_bytes(m.delta_bytes)))
        if m.process_rss_bytes is not None:
            grid.add_row("  Process RSS", Text(format_bytes(m.process_rss_bytes)))

    if result.cpu is not None:
        c = result.cpu
        _section(grid, "CPU")
        grid.add_row("  CPU time", Text(format_time_ns(c.average_cpu_ns, p)))
        grid.add_row("  CPU %", Text(f"{c.cpu_percent:.1f}%"))

    if result.calls is not None:
        k = result.calls
        _section(grid, "Calls")
        grid.add_row("  Function calls", Text(f"{k.function_calls:,}"))
        grid.add_row("  Recursive calls", Text(f"{k.recursive_calls:,}"))
        grid.add_row("  Max recursion depth", Text(f"{k.max_recursion_depth:,}"))
        grid.add_row("  GC collections", Text(f"{k.gc_collections:,}"))

    if result.exception is not None:
        _section(grid, "Exception", style="bold red")
        grid.add_row("  Type", Text(result.exception.type_name, style="red"))
        grid.add_row("  Message", Text(result.exception.message, style="red"))

    return Panel(
        grid,
        box=box.ROUNDED,
        border_style="cyan",
        title="Benchmark Report",
        title_align="left",
        subtitle=result.timestamp,
        subtitle_align="right",
        expand=False,
        padding=(1, 2),
    )


def print_report(
    result: BenchmarkResult,
    config: Config,
    console: Console | None = None,
) -> None:
    """Print the panel for *result* to *console* (or a fresh one).

    Args:
        result: The benchmark result to print.
        config: Active configuration.
        console: Optional console to reuse.
    """
    (console or get_console(config)).print(render_report(result, config))


def print_comparison(
    comparison: ComparisonResult,
    config: Config,
    console: Console | None = None,
) -> None:
    """Print the ranked comparison table.

    Args:
        comparison: Result of :func:`bench.compare`.
        config: Active configuration.
        console: Optional console to reuse.
    """
    p = config.precision
    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        title="Comparison" + (f" — args {comparison.args_repr}" if comparison.args_repr else ""),
        title_justify="left",
    )
    table.add_column("Rank", justify="right")
    table.add_column("Name", style="bold")
    table.add_column("Average", justify="right")
    table.add_column("Fastest", justify="right")
    table.add_column("Std Dev", justify="right")
    table.add_column("Peak Mem", justify="right")
    table.add_column("Relative", justify="right", no_wrap=True)

    for entry in comparison.entries:
        res = entry.result
        if res.exception is not None:
            table.add_row(
                str(entry.rank),
                Text(entry.name, style="red"),
                Text("error", style="red"),
                "—",
                "—",
                "—",
                Text(res.exception.type_name, style="red"),
            )
            continue
        t = res.timing
        style = "green" if entry.rank == 1 else ""
        relative = "baseline" if entry.rank == 1 else f"{entry.relative:.2f}× slower"
        table.add_row(
            str(entry.rank),
            Text(entry.name, style=style or "bold"),
            Text(format_time_ns(t.average_ns if t else None, p), style=style),
            format_time_ns(t.fastest_ns if t else None, p),
            format_time_ns(t.stdev_ns if t else None, p),
            format_bytes(res.peak_memory_bytes),
            Text(relative, style=style),
        )

    out = console or get_console(config)
    out.print(table)
    if comparison.outputs_match is True:
        out.print(Text("✓ all outputs match", style="green"))
    elif comparison.outputs_match is False:
        out.print(Text("⚠ outputs differ between candidates", style="yellow"))


def print_complexity(
    estimate: ComplexityResult,
    config: Config,
    console: Console | None = None,
) -> None:
    """Print the measured sizes and the complexity fit ranking.

    Args:
        estimate: Result of :func:`bench.estimate_complexity`.
        config: Active configuration.
        console: Optional console to reuse.
    """
    p = config.precision
    out = console or get_console(config)

    measured = Table(
        box=box.ROUNDED,
        border_style="cyan",
        title=f"Complexity — {estimate.name}",
        title_justify="left",
    )
    measured.add_column("n", justify="right")
    measured.add_column("Time", justify="right")
    for size, t_ns in zip(estimate.sizes, estimate.times_ns, strict=True):
        measured.add_row(f"{size:,}", format_time_ns(t_ns, p))
    out.print(measured)

    if estimate.fits:
        best = estimate.best
        out.print(
            Text("Estimated complexity: ", style="bold")
            + Text(best.label, style="bold green")
            + Text(f"  (R² = {best.r_squared:.4f})")
        )
        fits = Table(box=box.SIMPLE_HEAD, border_style="cyan")
        fits.add_column("Model")
        fits.add_column("R²", justify="right")
        for fit in estimate.fits:
            style = "green" if fit.label == best.label else ""
            fits.add_row(Text(fit.label, style=style), Text(f"{fit.r_squared:.4f}", style=style))
        out.print(fits)


def print_space_complexity(
    estimate: SpaceComplexityResult,
    config: Config,
    console: Console | None = None,
) -> None:
    """Print the measured sizes and the space-complexity fit ranking.

    Args:
        estimate: Result of :func:`bench.estimate_space_complexity`.
        config: Active configuration.
        console: Optional console to reuse.
    """
    out = console or get_console(config)

    measured = Table(
        box=box.ROUNDED,
        border_style="cyan",
        title=f"Space Complexity — {estimate.name}",
        title_justify="left",
    )
    measured.add_column("n", justify="right")
    measured.add_column("Peak Memory", justify="right")
    for size, peak in zip(estimate.sizes, estimate.peak_bytes, strict=True):
        measured.add_row(f"{size:,}", format_bytes(peak))
    out.print(measured)

    if estimate.fits:
        best = estimate.best
        out.print(
            Text("Estimated space complexity: ", style="bold")
            + Text(best.label, style="bold green")
            + Text(f"  (R² = {best.r_squared:.4f})")
        )
        fits = Table(box=box.SIMPLE_HEAD, border_style="cyan")
        fits.add_column("Model")
        fits.add_column("R²", justify="right")
        for fit in estimate.fits:
            style = "green" if fit.label == best.label else ""
            fits.add_row(Text(fit.label, style=style), Text(f"{fit.r_squared:.4f}", style=style))
        out.print(fits)
