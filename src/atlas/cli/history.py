"""CLI commands for scan history management."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

history_app = typer.Typer(
    name="history",
    help="View and manage scan history.",
    no_args_is_help=True,
)

console = Console()


def _get_storage(db_path: str | None = None):
    """Lazy-import and instantiate HistoryStorage."""
    from atlas.history.storage import HistoryStorage

    return HistoryStorage(db_path=db_path or ".atlas/history.db")


@history_app.command("list")
def list_scans(
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Filter by model name"
    ),
    limit: int = typer.Option(
        50, "--limit", "-n", help="Maximum number of scans to list"
    ),
    db_path: Optional[str] = typer.Option(
        None, "--db", help="Path to history database"
    ),
) -> None:
    """List recent scan results."""
    storage = _get_storage(db_path)
    scans = storage.list_scans(model=model, limit=limit)

    if not scans:
        console.print("[yellow]No scan history found.[/yellow]")
        raise typer.Exit()

    table = Table(title="Scan History", show_lines=False)
    table.add_column("Scan ID", style="cyan", no_wrap=True, max_width=12)
    table.add_column("Model", style="green")
    table.add_column("Profile", style="blue")
    table.add_column("Score", justify="right")
    table.add_column("Risk", justify="center")
    table.add_column("Probes", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Timestamp", style="dim")

    for scan in scans:
        score = scan.get("overall_score", 0.0)
        risk = scan.get("risk_level", "")

        # Color-code the score
        if score >= 80:
            score_str = f"[green]{score:.1f}[/green]"
        elif score >= 60:
            score_str = f"[yellow]{score:.1f}[/yellow]"
        else:
            score_str = f"[red]{score:.1f}[/red]"

        # Color-code the risk level
        risk_colors = {
            "critical": "red bold",
            "high": "red",
            "medium": "yellow",
            "low": "green",
            "minimal": "green bold",
        }
        risk_style = risk_colors.get(risk, "white")
        risk_str = f"[{risk_style}]{risk.upper()}[/{risk_style}]" if risk else "-"

        # Truncate scan ID for display
        scan_id_short = scan.get("scan_id", "")[:12]
        timestamp = scan.get("timestamp", "")[:19]  # Trim microseconds

        table.add_row(
            scan_id_short,
            scan.get("model_name", ""),
            scan.get("profile", "-"),
            score_str,
            risk_str,
            str(scan.get("total_probes", 0)),
            str(scan.get("total_findings", 0)),
            timestamp,
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(scans)} scan(s)[/dim]")


@history_app.command("show")
def show_scan(
    scan_id: str = typer.Argument(help="Scan ID (full or prefix)"),
    db_path: Optional[str] = typer.Option(
        None, "--db", help="Path to history database"
    ),
) -> None:
    """Show detailed information for a specific scan."""
    storage = _get_storage(db_path)
    scan = storage.get_scan(scan_id)

    if scan is None:
        # Try prefix match
        all_scans = storage.list_scans(limit=500)
        matches = [s for s in all_scans if s.get("scan_id", "").startswith(scan_id)]
        if len(matches) == 1:
            scan = storage.get_scan(matches[0]["scan_id"])
        elif len(matches) > 1:
            console.print(
                f"[yellow]Multiple scans match prefix '{scan_id}'. "
                f"Please be more specific.[/yellow]"
            )
            for m in matches:
                console.print(f"  {m['scan_id']}")
            raise typer.Exit(code=1)
        else:
            console.print(f"[red]Scan '{scan_id}' not found.[/red]")
            raise typer.Exit(code=1)

    if scan is None:
        console.print(f"[red]Scan '{scan_id}' not found.[/red]")
        raise typer.Exit(code=1)

    # Header
    console.print(f"\n[bold cyan]Scan Details[/bold cyan]")
    console.print(f"  [bold]Scan ID:[/bold]    {scan.get('scan_id', '')}")
    console.print(f"  [bold]Model:[/bold]      {scan.get('model_name', '')}")
    console.print(f"  [bold]Provider:[/bold]   {scan.get('provider', '')}")
    console.print(f"  [bold]Profile:[/bold]    {scan.get('profile', '-')}")
    console.print(f"  [bold]Timestamp:[/bold]  {scan.get('timestamp', '')}")
    console.print(f"  [bold]Duration:[/bold]   {scan.get('duration_ms', 0):.0f}ms")

    # Score
    score = scan.get("overall_score", 0.0)
    risk = scan.get("risk_level", "")
    console.print(f"\n[bold]Security Score:[/bold] {score:.1f}/100")
    console.print(f"[bold]Risk Level:[/bold]     {risk.upper()}")

    # Probe results from full result JSON
    result = scan.get("result")
    if result and "probe_results" in result:
        console.print(f"\n[bold cyan]Probe Results[/bold cyan]")
        probe_table = Table(show_lines=False)
        probe_table.add_column("Probe", style="white")
        probe_table.add_column("Category", style="blue")
        probe_table.add_column("Pass Rate", justify="right")
        probe_table.add_column("Passed", justify="right", style="green")
        probe_table.add_column("Failed", justify="right", style="red")

        for probe_name, probe_data in result["probe_results"].items():
            pass_rate = probe_data.get("pass_rate", 0.0)
            if pass_rate >= 80:
                pr_str = f"[green]{pass_rate:.1f}%[/green]"
            elif pass_rate >= 60:
                pr_str = f"[yellow]{pass_rate:.1f}%[/yellow]"
            else:
                pr_str = f"[red]{pass_rate:.1f}%[/red]"

            probe_table.add_row(
                probe_name,
                probe_data.get("category", "-"),
                pr_str,
                str(probe_data.get("passed", 0)),
                str(probe_data.get("failed", 0)),
            )

        console.print(probe_table)

    # Category scores
    if result and "security_score" in result:
        cat_scores = result["security_score"].get("category_scores", {})
        if cat_scores:
            console.print(f"\n[bold cyan]Category Scores[/bold cyan]")
            cat_table = Table(show_lines=False)
            cat_table.add_column("Category", style="white")
            cat_table.add_column("Score", justify="right")

            for cat_name, cat_score in sorted(
                cat_scores.items(), key=lambda x: x[1]
            ):
                if cat_score >= 80:
                    cs_str = f"[green]{cat_score:.1f}[/green]"
                elif cat_score >= 60:
                    cs_str = f"[yellow]{cat_score:.1f}[/yellow]"
                else:
                    cs_str = f"[red]{cat_score:.1f}[/red]"
                cat_table.add_row(cat_name, cs_str)

            console.print(cat_table)

    # Recommendations
    if result and result.get("recommendations"):
        console.print(f"\n[bold cyan]Recommendations[/bold cyan]")
        for i, rec in enumerate(result["recommendations"], 1):
            console.print(f"  {i}. {rec}")

    console.print()


@history_app.command("trends")
def show_trends(
    model: str = typer.Option(
        ..., "--model", "-m", help="Model name to show trends for"
    ),
    limit: int = typer.Option(
        10, "--limit", "-n", help="Number of data points"
    ),
    db_path: Optional[str] = typer.Option(
        None, "--db", help="Path to history database"
    ),
) -> None:
    """Show score trends over time for a model."""
    storage = _get_storage(db_path)
    trends = storage.get_trends(model=model, limit=limit)

    if not trends:
        console.print(
            f"[yellow]No scan history found for model '{model}'.[/yellow]"
        )
        raise typer.Exit()

    console.print(f"\n[bold cyan]Score Trends: {model}[/bold cyan]\n")

    table = Table(show_lines=False)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Timestamp", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Risk", justify="center")
    table.add_column("Findings", justify="right")
    table.add_column("Trend", justify="center")

    prev_score: float | None = None
    for i, point in enumerate(trends, 1):
        score = point.get("overall_score", 0.0)
        risk = point.get("risk_level", "")

        # Color-code score
        if score >= 80:
            score_str = f"[green]{score:.1f}[/green]"
        elif score >= 60:
            score_str = f"[yellow]{score:.1f}[/yellow]"
        else:
            score_str = f"[red]{score:.1f}[/red]"

        # Risk level
        risk_colors = {
            "critical": "red bold",
            "high": "red",
            "medium": "yellow",
            "low": "green",
            "minimal": "green bold",
        }
        risk_style = risk_colors.get(risk, "white")
        risk_str = f"[{risk_style}]{risk.upper()}[/{risk_style}]" if risk else "-"

        # Trend indicator
        if prev_score is None:
            trend_str = "-"
        elif score > prev_score:
            delta = score - prev_score
            trend_str = f"[green]+{delta:.1f}[/green]"
        elif score < prev_score:
            delta = prev_score - score
            trend_str = f"[red]-{delta:.1f}[/red]"
        else:
            trend_str = "[dim]=[/dim]"

        timestamp = point.get("timestamp", "")[:19]

        table.add_row(
            str(i),
            timestamp,
            score_str,
            risk_str,
            str(point.get("total_findings", 0)),
            trend_str,
        )
        prev_score = score

    console.print(table)

    # Summary
    if len(trends) >= 2:
        first_score = trends[0].get("overall_score", 0.0)
        last_score = trends[-1].get("overall_score", 0.0)
        total_change = last_score - first_score
        if total_change > 0:
            console.print(
                f"\n[green]Overall improvement: +{total_change:.1f} points[/green]"
            )
        elif total_change < 0:
            console.print(
                f"\n[red]Overall decline: {total_change:.1f} points[/red]"
            )
        else:
            console.print(f"\n[dim]No overall change[/dim]")

    console.print()


@history_app.command("delete")
def delete_scan(
    scan_id: str = typer.Argument(help="Scan ID to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation prompt"
    ),
    db_path: Optional[str] = typer.Option(
        None, "--db", help="Path to history database"
    ),
) -> None:
    """Delete a scan from history."""
    storage = _get_storage(db_path)

    # Check it exists first
    scan = storage.get_scan(scan_id)
    if scan is None:
        console.print(f"[red]Scan '{scan_id}' not found.[/red]")
        raise typer.Exit(code=1)

    if not force:
        console.print(
            f"[yellow]About to delete scan {scan_id} "
            f"(model: {scan.get('model_name', 'unknown')}, "
            f"score: {scan.get('overall_score', 0):.1f})[/yellow]"
        )
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    deleted = storage.delete_scan(scan_id)
    if deleted:
        console.print(f"[green]Scan {scan_id} deleted successfully.[/green]")
    else:
        console.print(f"[red]Failed to delete scan {scan_id}.[/red]")
        raise typer.Exit(code=1)
