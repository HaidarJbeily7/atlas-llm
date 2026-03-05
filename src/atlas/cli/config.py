"""Configuration management commands for ATLAS CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.syntax import Syntax

console = Console()

config_app = typer.Typer(no_args_is_help=True)


@config_app.command("init")
def config_init(
    output: Path = typer.Option(Path("atlas.yaml"), "--output", "-o", help="Output config file path"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Create a default ATLAS configuration file."""
    if output.exists() and not force:
        console.print(f"[yellow]Config file already exists: {output}. Use --force to overwrite.[/yellow]")
        raise typer.Exit(1)

    default_config = '''# ATLAS Configuration
# See https://github.com/atlas-llm/atlas for documentation

provider:
  model: openai/gpt-4o           # LiteLLM model string
  api_key: ${OPENAI_API_KEY}      # Environment variable interpolation
  timeout: 30
  max_retries: 3
  temperature: 0.0

scan:
  concurrency: 10
  timeout: 600
  probe_timeout: 120
  continue_on_error: false
  checkpoint_enabled: true

output:
  directory: ./results
  format: json
  include_timestamps: true
  include_evidence: true

compliance:
  eu_ai_act: true
  owasp_llm: true
  risk_threshold: 0.7

logging:
  level: INFO
  format: console
'''

    with open(output, "w") as f:
        f.write(default_config)

    console.print(f"[green]Config file created: {output}[/green]")


@config_app.command("show")
def config_show(
    ctx: typer.Context = typer.Option(None, hidden=True),
) -> None:
    """Show current effective configuration."""
    from atlas.config.loader import load_config

    config_file = None
    if ctx and ctx.obj:
        config_file = ctx.obj.get("config_file")

    try:
        config = load_config(config_file)
        import json
        config_json = json.dumps(config.model_dump(), indent=2, default=str)
        syntax = Syntax(config_json, "json", theme="monokai")
        console.print(syntax)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)


@config_app.command("validate")
def config_validate(
    config_path: Path = typer.Argument(Path("atlas.yaml"), help="Config file to validate"),
) -> None:
    """Validate a configuration file."""
    from atlas.config.loader import load_config

    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        raise typer.Exit(1)

    try:
        config = load_config(config_path)
        console.print(f"[green]Configuration is valid![/green]")
        console.print(f"  Model: {config.provider.model}")
        console.print(f"  Profiles: {len(config.profiles)}")
        console.print(f"  Probes: {len(config.probes)}")
    except Exception as e:
        console.print(f"[red]Invalid configuration: {e}[/red]")
        raise typer.Exit(1)
