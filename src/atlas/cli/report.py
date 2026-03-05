"""Report commands for ATLAS CLI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()

report_app = typer.Typer(no_args_is_help=True)


@report_app.command("generate")
def generate_report(
    input_path: Path = typer.Option(..., "--input", "-i", help="Path to scan result JSON"),
    output_dir: Path = typer.Option(Path("./results"), "--output", "-o", help="Output directory"),
    format: str = typer.Option("html", "--format", "-f", help="Report format (json, html, markdown)"),
) -> None:
    """Generate a report from scan results."""
    from atlas.core.models import ScanResult

    if not input_path.exists():
        console.print(f"[red]Input file not found: {input_path}[/red]")
        raise typer.Exit(1)

    with open(input_path) as f:
        data = json.load(f)

    result = ScanResult.model_validate(data)
    _generate_report(result, output_dir, format)


def _generate_report(result, output_dir: Path, format: str) -> None:
    """Internal report generation."""
    import asyncio

    output_dir.mkdir(parents=True, exist_ok=True)

    if format == "html":
        from atlas.reports.html_reporter import HTMLReporter
        reporter = HTMLReporter()
        output_path = output_dir / f"report_{result.scan_id[:8]}.html"
        asyncio.run(reporter.generate(result, str(output_path)))
        console.print(f"HTML report: [bold]{output_path}[/bold]")

    elif format == "markdown":
        from atlas.reports.markdown_reporter import MarkdownReporter
        reporter = MarkdownReporter()
        output_path = output_dir / f"report_{result.scan_id[:8]}.md"
        asyncio.run(reporter.generate(result, str(output_path)))
        console.print(f"Markdown report: [bold]{output_path}[/bold]")

    elif format == "json":
        from atlas.reports.json_reporter import JSONReporter
        reporter = JSONReporter()
        output_path = output_dir / f"report_{result.scan_id[:8]}.json"
        asyncio.run(reporter.generate(result, str(output_path)))
        console.print(f"JSON report: [bold]{output_path}[/bold]")

    else:
        console.print(f"[red]Unknown format: {format}. Use json, html, or markdown.[/red]")
        raise typer.Exit(1)


@report_app.command("compare")
def compare_reports(
    inputs: list[Path] = typer.Argument(..., help="Two or more scan result JSON files"),
    output_dir: Path = typer.Option(Path("./results"), "--output", "-o", help="Output directory"),
) -> None:
    """Compare multiple scan results side by side."""
    from rich.table import Table
    from atlas.core.models import ScanResult

    if len(inputs) < 2:
        console.print("[red]At least 2 input files required for comparison.[/red]")
        raise typer.Exit(1)

    results = []
    for path in inputs:
        if not path.exists():
            console.print(f"[red]File not found: {path}[/red]")
            raise typer.Exit(1)
        with open(path) as f:
            results.append(ScanResult.model_validate(json.load(f)))

    # Comparison table
    table = Table(title="Scan Comparison")
    table.add_column("Metric", style="bold")
    for r in results:
        table.add_column(f"{r.model_name}\n({r.scan_id[:8]})", justify="center")

    # Overall score
    scores = [f"{r.security_score.overall_score:.1f}" for r in results]
    table.add_row("Security Score", *scores)

    # Risk level
    levels = [r.security_score.risk_level.value.upper() for r in results]
    table.add_row("Risk Level", *levels)

    # Total findings
    total = [str(len(r.findings)) for r in results]
    table.add_row("Total Findings", *total)

    # Per-probe pass rates
    all_probes = set()
    for r in results:
        all_probes.update(r.probe_results.keys())

    for probe in sorted(all_probes):
        rates = []
        for r in results:
            if probe in r.probe_results:
                rates.append(f"{r.probe_results[probe].pass_rate:.1f}%")
            else:
                rates.append("N/A")
        table.add_row(f"  {probe}", *rates)

    console.print(table)
