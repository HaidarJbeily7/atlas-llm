"""Interactive REPL mode for ATLAS security researchers."""
from __future__ import annotations

import asyncio
import importlib
import shlex
import sys
import time
from datetime import UTC, datetime
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from atlas.config.models import AtlasConfig
from atlas.core.models import Attempt
from atlas.logging.setup import get_logger

logger = get_logger(__name__)

console = Console()

# Banner displayed when the REPL starts
_BANNER = r"""
    _  _____ _      _    ____
   / \|_   _| |    / \  / ___|
  / _ \ | | | |   / _ \ \___ \
 / ___ \| | | |__/ ___ \ ___) |
/_/   \_\_| |____/_/   \_\____/

  Interactive Security Research Console
"""

_HELP_TEXT = """\
| Command | Description |
|---|---|
| `probe <name>` | Run a specific probe and show results |
| `detect <text>` | Run detectors on arbitrary text |
| `generate <prompt>` | Send a prompt to the LLM and show response |
| `list probes` | List available probes |
| `list detectors` | List available detectors |
| `status` | Show current session status |
| `config` | Show current configuration |
| `help` | Show this help message |
| `exit` / `quit` | Exit the REPL |
"""


class AtlasREPL:
    """Interactive REPL for exploring ATLAS probes, detectors, and LLM interactions.

    Provides a command-driven loop that lets security researchers run probes,
    test detectors on arbitrary text, send ad-hoc prompts to the target LLM,
    and inspect session state -- all without leaving the terminal.
    """

    def __init__(self, config: AtlasConfig) -> None:
        self.config = config
        self.started_at = datetime.now(UTC)
        self.command_count = 0
        self.probes_run: list[str] = []
        self.detections_run: int = 0
        self.generations_run: int = 0

        # Lazily initialised -- created on first use so the REPL can start
        # even when provider credentials are not yet set.
        self._generator: Any | None = None
        self._runner: Any | None = None

    # -- lazy helpers -------------------------------------------------------

    def _get_generator(self) -> Any:
        """Lazily create the LiteLLM generator."""
        if self._generator is None:
            from atlas.generators.litellm import LiteLLMGenerator

            self._generator = LiteLLMGenerator.from_config(self.config.provider)
        return self._generator

    def _get_runner(self) -> Any:
        """Lazily create the ScanRunner."""
        if self._runner is None:
            from atlas.engine.runner import ScanRunner

            self._runner = ScanRunner(self.config)
        return self._runner

    # -- main loop ----------------------------------------------------------

    async def run(self) -> None:
        """Start the interactive REPL loop."""
        console.print(Text(_BANNER, style="bold cyan"))
        console.print(
            f"  Model : [cyan]{self.config.provider.model}[/cyan]"
        )
        console.print(
            "  Type [bold]help[/bold] for available commands, "
            "[bold]exit[/bold] to quit.\n"
        )

        while True:
            try:
                raw = console.input("[bold green]atlas>[/bold green] ")
            except (EOFError, KeyboardInterrupt):
                console.print("\nGoodbye.")
                break

            line = raw.strip()
            if not line:
                continue

            try:
                await self._handle_command(line)
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")
                logger.debug("repl_command_error", command=line, error=str(exc))

    # -- command dispatch ---------------------------------------------------

    async def _handle_command(self, cmd: str) -> None:
        """Parse and dispatch a single REPL command."""
        parts = shlex.split(cmd)
        verb = parts[0].lower()
        args = parts[1:]

        self.command_count += 1

        dispatch: dict[str, Any] = {
            "probe": self._cmd_probe,
            "detect": self._cmd_detect,
            "generate": self._cmd_generate,
            "list": self._cmd_list,
            "status": self._cmd_status,
            "config": self._cmd_config,
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
        }

        handler = dispatch.get(verb)
        if handler is None:
            console.print(
                f"[yellow]Unknown command:[/yellow] {verb}. "
                "Type [bold]help[/bold] for available commands."
            )
            return

        await handler(args, cmd)

    # -- individual command handlers ----------------------------------------

    async def _cmd_probe(self, args: list[str], raw: str) -> None:
        """Run a named probe against the configured LLM."""
        if not args:
            console.print("[yellow]Usage:[/yellow] probe <name>")
            return

        probe_name = args[0]

        from atlas.probes import PROBE_MODULES

        if probe_name not in PROBE_MODULES:
            console.print(
                f"[red]Unknown probe:[/red] {probe_name}. "
                "Use [bold]list probes[/bold] to see available probes."
            )
            return

        console.print(
            f"\nRunning probe [cyan]{probe_name}[/cyan] against "
            f"[cyan]{self.config.provider.model}[/cyan] ...\n"
        )

        runner = self._get_runner()
        start = time.time()

        try:
            result = await runner._run_probe(
                probe_name,
                detectors=[
                    _resolve_default_detectors(),
                ],
            )
        except Exception as exc:
            console.print(f"[red]Probe failed:[/red] {exc}")
            return

        elapsed = time.time() - start
        self.probes_run.append(probe_name)

        # -- display results --
        table = Table(
            title=f"Probe Results: {probe_name}",
            show_lines=True,
        )
        table.add_column("#", justify="right", style="dim", width=4)
        table.add_column("Prompt (truncated)", style="white", max_width=60)
        table.add_column("Response (truncated)", max_width=50)
        table.add_column("Passed", justify="center")

        for idx, finding in enumerate(result.findings, 1):
            prompt_short = _truncate(finding.attempt.prompt, 120)
            resp_short = _truncate(finding.attempt.response, 100)
            passed_str = (
                "[green]PASS[/green]" if finding.passed else "[red]FAIL[/red]"
            )
            table.add_row(str(idx), prompt_short, resp_short, passed_str)

        console.print(table)

        rate_color = (
            "green" if result.pass_rate >= 80
            else "yellow" if result.pass_rate >= 60
            else "red"
        )
        console.print(
            f"\nTotal: {result.total_attempts}  "
            f"Passed: [green]{result.passed}[/green]  "
            f"Failed: [red]{result.failed}[/red]  "
            f"Pass rate: [{rate_color}]{result.pass_rate:.1f}%[/{rate_color}]  "
            f"Time: {elapsed:.1f}s\n"
        )

    async def _cmd_detect(self, args: list[str], raw: str) -> None:
        """Run detectors on arbitrary text supplied by the user."""
        # Everything after "detect " is the text to analyse
        if not args:
            console.print("[yellow]Usage:[/yellow] detect <text to analyse>")
            return

        text = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
        if not text:
            console.print("[yellow]Usage:[/yellow] detect <text to analyse>")
            return

        from atlas.detectors.keyword import KeywordDetector
        from atlas.detectors.refusal import RefusalDetector

        attempt = Attempt(probe_name="repl_detect", prompt="", response=text)
        detectors = [KeywordDetector(), RefusalDetector()]

        console.print(
            f"\nAnalysing text with {len(detectors)} detectors ...\n"
        )

        table = Table(title="Detection Results")
        table.add_column("Detector", style="cyan")
        table.add_column("Passed", justify="center")
        table.add_column("Score", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("Evidence", max_width=60)

        for detector in detectors:
            result = await detector.detect(attempt)
            passed_str = (
                "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            )
            table.add_row(
                result.detector_name,
                passed_str,
                f"{result.score:.2f}",
                f"{result.confidence:.2f}",
                _truncate(result.evidence, 100),
            )

        console.print(table)
        console.print()
        self.detections_run += 1

    async def _cmd_generate(self, args: list[str], raw: str) -> None:
        """Send an ad-hoc prompt to the target LLM and display the response."""
        if not args:
            console.print("[yellow]Usage:[/yellow] generate <prompt>")
            return

        prompt = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
        if not prompt:
            console.print("[yellow]Usage:[/yellow] generate <prompt>")
            return

        console.print(
            f"\nSending prompt to [cyan]{self.config.provider.model}[/cyan] ...\n"
        )

        generator = self._get_generator()
        start = time.time()
        response = await generator.generate(prompt)
        elapsed = time.time() - start

        console.print(
            Panel(
                response or "[dim](empty response)[/dim]",
                title="LLM Response",
                subtitle=f"{elapsed:.1f}s",
                border_style="cyan",
            )
        )
        console.print()
        self.generations_run += 1

    async def _cmd_list(self, args: list[str], raw: str) -> None:
        """List available probes or detectors."""
        if not args:
            console.print(
                "[yellow]Usage:[/yellow] list probes | list detectors"
            )
            return

        target = args[0].lower()

        if target == "probes":
            from atlas.probes import PROBE_MODULES

            table = Table(title="Available Probes")
            table.add_column("Name", style="cyan")
            table.add_column("Module", style="dim")

            for name, module in sorted(PROBE_MODULES.items()):
                table.add_row(name, module)

            console.print(table)

        elif target == "detectors":
            from atlas.detectors import DETECTOR_REGISTRY

            table = Table(title="Available Detectors")
            table.add_column("Name", style="cyan")
            table.add_column("Class", style="dim")

            for name, cls_path in sorted(DETECTOR_REGISTRY.items()):
                table.add_row(name, cls_path)

            console.print(table)

        else:
            console.print(
                f"[yellow]Unknown list target:[/yellow] {target}. "
                "Use [bold]list probes[/bold] or [bold]list detectors[/bold]."
            )

        console.print()

    async def _cmd_status(self, args: list[str], raw: str) -> None:
        """Display current session status."""
        now = datetime.now(UTC)
        uptime = now - self.started_at
        uptime_str = str(uptime).split(".")[0]  # drop microseconds

        table = Table(title="Session Status", show_header=False)
        table.add_column("Key", style="bold")
        table.add_column("Value")

        table.add_row("Model", self.config.provider.model)
        table.add_row("Session started", self.started_at.isoformat(timespec="seconds"))
        table.add_row("Uptime", uptime_str)
        table.add_row("Commands executed", str(self.command_count))
        table.add_row("Probes run", str(len(self.probes_run)))
        if self.probes_run:
            table.add_row("  Probes list", ", ".join(self.probes_run))
        table.add_row("Detections run", str(self.detections_run))
        table.add_row("Generations run", str(self.generations_run))

        console.print(table)
        console.print()

    async def _cmd_config(self, args: list[str], raw: str) -> None:
        """Show the current ATLAS configuration (secrets masked)."""
        from atlas.logging.setup import _mask_secrets

        data = self.config.model_dump(mode="json")
        masked = _mask_secrets(data)

        # Format as a readable table grouped by section
        for section, values in masked.items():
            if isinstance(values, dict):
                table = Table(title=f"Config: {section}", show_header=False)
                table.add_column("Key", style="bold")
                table.add_column("Value")
                for k, v in values.items():
                    table.add_row(k, str(v))
                console.print(table)
            else:
                console.print(f"[bold]{section}:[/bold] {values}")

        console.print()

    async def _cmd_help(self, args: list[str], raw: str) -> None:
        """Show the help table."""
        console.print()
        console.print(Markdown(_HELP_TEXT))
        console.print()

    async def _cmd_exit(self, args: list[str], raw: str) -> None:
        """Exit the REPL."""
        console.print("Goodbye.")
        raise SystemExit(0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, length: int = 80) -> str:
    """Truncate text to *length* characters, appending an ellipsis if needed."""
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


def _resolve_default_detectors() -> Any:
    """Return the default keyword detector for interactive probe runs."""
    from atlas.detectors.keyword import KeywordDetector

    return KeywordDetector()


# ---------------------------------------------------------------------------
# Typer CLI entry-point
# ---------------------------------------------------------------------------

def interactive_command(
    model: str = typer.Option(
        None, "--model", "-m",
        help="LLM model to interact with (e.g., openai/gpt-4o)",
    ),
    config_file: str = typer.Option(
        None, "--config", "-c",
        help="Path to atlas config YAML file",
    ),
) -> None:
    """Start an interactive REPL session for security research."""
    from pathlib import Path

    from atlas.config.loader import load_config

    cfg_path = Path(config_file) if config_file else None
    config = load_config(cfg_path)

    if model:
        config.provider.model = model

    repl = AtlasREPL(config)

    try:
        asyncio.run(repl.run())
    except (KeyboardInterrupt, SystemExit):
        pass
