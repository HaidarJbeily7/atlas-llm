"""Main ATLAS CLI application."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from atlas import __version__

console = Console()

app = typer.Typer(
    name="atlas",
    help="ATLAS - Automated Testing for LLM Assurance & Security",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"atlas {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output"),
    log_level: Optional[str] = typer.Option(
        None, "--log-level", "-l", envvar="ATLAS_LOG_LEVEL",
        help="Log level (DEBUG, INFO, WARNING, ERROR)",
    ),
    log_format: Optional[str] = typer.Option(
        None, "--log-format", envvar="ATLAS_LOG_FORMAT",
        help="Log format (console, json)",
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", envvar="ATLAS_CONFIG",
        help="Path to config file",
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", callback=version_callback, is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """ATLAS - Automated Testing for LLM Assurance & Security."""
    from atlas.logging.setup import setup_logging

    # Determine effective log level
    if verbose:
        effective_level = "DEBUG"
    elif quiet:
        effective_level = "ERROR"
    else:
        effective_level = log_level or "INFO"

    setup_logging(level=effective_level, format_type=log_format or "console")

    # Store in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["config_file"] = config_file
    ctx.obj["log_level"] = effective_level


# Register subcommands
from atlas.cli.scan import scan_app
from atlas.cli.report import report_app
from atlas.cli.config import config_app
from atlas.cli.history import history_app

app.add_typer(scan_app, name="scan", help="Run security scans")
app.add_typer(report_app, name="report", help="Generate reports")
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(history_app, name="history", help="View and manage scan history")

# Register interactive REPL command
from atlas.cli.repl import interactive_command

app.command("interactive", help="Start an interactive REPL session")(interactive_command)
