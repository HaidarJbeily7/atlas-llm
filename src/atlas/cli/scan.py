"""Scan commands for ATLAS CLI."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

scan_app = typer.Typer(no_args_is_help=True)


@scan_app.command("run")
def scan_run(
    model: str = typer.Option(..., "--model", "-m", help="LLM model (e.g., openai/gpt-4o)"),
    profile: str = typer.Option("standard", "--profile", "-p", help="Scan profile (quick, standard, full)"),
    probes: Optional[str] = typer.Option(None, "--probes", help="Comma-separated probe names"),
    detectors: Optional[str] = typer.Option(None, "--detectors", help="Comma-separated detector names"),
    output: Path = typer.Option(Path("./results"), "--output", "-o", help="Output directory"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json, html, markdown)"),
    no_checkpoint: bool = typer.Option(False, "--no-checkpoint", help="Disable checkpoint/resume"),
    ctx: typer.Context = typer.Option(None, hidden=True),
) -> None:
    """Run a security scan against an LLM model."""
    from atlas.config.loader import load_config
    from atlas.engine.runner import ScanRunner

    config_file = None
    if ctx and ctx.obj:
        config_file = ctx.obj.get("config_file")

    config = load_config(config_file)
    config.provider.model = model
    config.output.directory = str(output)

    probe_list = probes.split(",") if probes else None
    detector_list = detectors.split(",") if detectors else None

    console.print(Panel(
        f"[bold]ATLAS Security Scan[/bold]\n"
        f"Model: [cyan]{model}[/cyan]\n"
        f"Profile: [green]{profile}[/green]\n"
        f"Probes: {probe_list or 'from profile'}\n"
        f"Detectors: {detector_list or 'from profile'}",
        title="Scan Configuration",
    ))

    runner = ScanRunner(config)

    try:
        result = asyncio.run(runner.run(
            profile=profile,
            probe_names=probe_list,
            detector_names=detector_list,
            checkpoint_enabled=not no_checkpoint,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan interrupted. Checkpoint saved.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Scan failed: {e}[/red]")
        raise typer.Exit(1)

    # Display summary
    _display_scan_summary(result)

    # Save results
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / f"scan_{result.scan_id[:8]}.json"
    with open(result_path, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    console.print(f"\nResults saved to: [bold]{result_path}[/bold]")

    # Generate report if requested
    if format != "json":
        from atlas.cli.report import _generate_report
        _generate_report(result, output, format)


def _display_scan_summary(result) -> None:
    """Display scan results summary in Rich table."""
    score = result.security_score

    # Score color
    if score.overall_score >= 80:
        score_color = "green"
    elif score.overall_score >= 60:
        score_color = "yellow"
    elif score.overall_score >= 40:
        score_color = "red"
    else:
        score_color = "bold red"

    console.print()
    console.print(Panel(
        f"[{score_color}]{score.overall_score:.1f}/100[/{score_color}]",
        title="Security Score",
        subtitle=f"Risk Level: {score.risk_level.value.upper()}",
    ))

    # Probe results table
    table = Table(title="Probe Results")
    table.add_column("Probe", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Pass Rate", justify="right")

    for name, pr in result.probe_results.items():
        rate_str = f"{pr.pass_rate:.1f}%"
        rate_color = "green" if pr.pass_rate >= 80 else "yellow" if pr.pass_rate >= 60 else "red"
        table.add_row(
            name,
            str(pr.total_attempts),
            str(pr.passed),
            str(pr.failed),
            f"[{rate_color}]{rate_str}[/{rate_color}]",
        )

    console.print(table)

    # Severity summary
    vuln = score.vulnerabilities_by_severity
    if any(v > 0 for v in vuln.values()):
        console.print(
            f"\nVulnerabilities: "
            f"[bold red]{vuln.get('critical', 0)} critical[/bold red], "
            f"[red]{vuln.get('high', 0)} high[/red], "
            f"[yellow]{vuln.get('medium', 0)} medium[/yellow], "
            f"[green]{vuln.get('low', 0)} low[/green]"
        )

    # Duration
    console.print(f"\nScan completed in {result.duration_ms/1000:.1f}s")


@scan_app.command("list-probes")
def list_probes() -> None:
    """List all available security probes."""
    from atlas.probes import PROBE_MODULES

    table = Table(title="Available Probes")
    table.add_column("Name", style="cyan")
    table.add_column("Module", style="dim")

    for name, module in sorted(PROBE_MODULES.items()):
        table.add_row(name, module)

    console.print(table)


@scan_app.command("list-detectors")
def list_detectors() -> None:
    """List all available detectors."""
    from atlas.detectors import DETECTOR_REGISTRY

    table = Table(title="Available Detectors")
    table.add_column("Name", style="cyan")
    table.add_column("Class", style="dim")

    for name, cls_path in sorted(DETECTOR_REGISTRY.items()):
        table.add_row(name, cls_path)

    console.print(table)
