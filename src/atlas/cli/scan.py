"""Scan commands for ATLAS CLI."""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()

scan_app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------------------------
# SARIF report generation
# ---------------------------------------------------------------------------

def _generate_sarif_report(result, output_path: Path) -> None:
    """Generate a SARIF 2.1.0 report from scan results."""
    rules = []
    results_list = []

    rule_index_map: dict[str, int] = {}

    for finding in result.findings:
        rule_id = finding.attempt.probe_name
        if rule_id not in rule_index_map:
            rule_index_map[rule_id] = len(rules)
            rules.append({
                "id": rule_id,
                "name": rule_id,
                "shortDescription": {"text": f"Security probe: {rule_id}"},
                "defaultConfiguration": {
                    "level": _severity_to_sarif_level(finding.severity.value),
                },
            })

        if not finding.passed:
            evidence_parts = [
                dr.evidence for dr in finding.detector_results if dr.evidence
            ]
            results_list.append({
                "ruleId": rule_id,
                "ruleIndex": rule_index_map[rule_id],
                "level": _severity_to_sarif_level(finding.severity.value),
                "message": {
                    "text": finding.description or f"Failed probe: {rule_id}",
                },
                "properties": {
                    "category": finding.category.value,
                    "evidence": "; ".join(evidence_parts) if evidence_parts else "",
                },
            })

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ATLAS",
                        "semanticVersion": "0.1.0",
                        "informationUri": "https://github.com/atlas-security/atlas",
                        "rules": rules,
                    },
                },
                "results": results_list,
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "properties": {
                            "scanId": result.scan_id,
                            "model": result.model_name,
                            "profile": result.profile,
                            "securityScore": result.security_score.overall_score,
                        },
                    }
                ],
            }
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(sarif, f, indent=2, default=str)


def _severity_to_sarif_level(severity: str) -> str:
    """Map ATLAS severity to SARIF level."""
    mapping = {
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
        "info": "note",
    }
    return mapping.get(severity, "warning")


# ---------------------------------------------------------------------------
# JUnit report generation
# ---------------------------------------------------------------------------

def _generate_junit_report(result, output_path: Path) -> None:
    """Generate a JUnit XML report from scan results."""
    import xml.etree.ElementTree as ET

    testsuites = ET.Element("testsuites")
    testsuites.set("name", "ATLAS Security Scan")
    testsuites.set("tests", str(len(result.findings)))
    testsuites.set("time", f"{result.duration_ms / 1000:.3f}")

    total_failures = 0

    for probe_name, pr in result.probe_results.items():
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", probe_name)
        testsuite.set("tests", str(pr.total_attempts))
        testsuite.set("failures", str(pr.failed))
        testsuite.set("time", "0")

        total_failures += pr.failed

        for finding in pr.findings:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", f"{probe_name}:{finding.id[:8]}")
            testcase.set("classname", f"atlas.probes.{probe_name}")

            if not finding.passed:
                failure = ET.SubElement(testcase, "failure")
                failure.set("type", finding.severity.value)
                failure.set("message", finding.description or f"Failed: {probe_name}")

                evidence_parts = [
                    dr.evidence for dr in finding.detector_results if dr.evidence
                ]
                failure.text = "\n".join(evidence_parts) if evidence_parts else ""

    testsuites.set("failures", str(total_failures))

    tree = ET.ElementTree(testsuites)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(str(output_path), encoding="unicode", xml_declaration=True)


# ---------------------------------------------------------------------------
# CI-mode helpers
# ---------------------------------------------------------------------------

def _compute_overall_pass_rate(result) -> float:
    """Compute the weighted overall pass rate across all probes."""
    total_attempts = 0
    total_passed = 0
    for pr in result.probe_results.values():
        total_attempts += pr.total_attempts
        total_passed += pr.passed
    if total_attempts == 0:
        return 100.0
    return (total_passed / total_attempts) * 100.0


def _print_ci_summary(result, pass_rate: float, threshold: float) -> None:
    """Print a minimal, non-interactive summary suitable for CI logs."""
    status = "PASS" if pass_rate >= threshold else "FAIL"
    print(f"[ATLAS] Scan complete: {result.model_name}")
    print(f"[ATLAS] Security score: {result.security_score.overall_score:.1f}/100")
    print(f"[ATLAS] Overall pass rate: {pass_rate:.1f}% (threshold: {threshold:.1f}%)")
    print(f"[ATLAS] Risk level: {result.security_score.risk_level.value.upper()}")

    vuln = result.security_score.vulnerabilities_by_severity
    print(
        f"[ATLAS] Vulnerabilities: "
        f"{vuln.get('critical', 0)} critical, "
        f"{vuln.get('high', 0)} high, "
        f"{vuln.get('medium', 0)} medium, "
        f"{vuln.get('low', 0)} low"
    )

    for probe_name, pr in result.probe_results.items():
        marker = "PASS" if pr.pass_rate >= threshold else "FAIL"
        print(f"[ATLAS]   {marker} {probe_name}: {pr.pass_rate:.1f}% ({pr.passed}/{pr.total_attempts})")

    print(f"[ATLAS] Result: {status}")


# ---------------------------------------------------------------------------
# Progress-bar wrapper
# ---------------------------------------------------------------------------

async def _run_with_progress(
    runner,
    *,
    profile: str,
    probe_list: list[str] | None,
    detector_list: list[str] | None,
    checkpoint_enabled: bool,
    run_all_detectors: bool = False,
):
    """Run a scan while displaying Rich progress bars."""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    probe_tasks: dict[str, int] = {}  # probe_name -> task_id

    def on_progress(event: str, data: dict) -> None:
        if event == "probe_start":
            task_id = progress.add_task(data["probe"], total=data["total"])
            probe_tasks[data["probe"]] = task_id
        elif event == "attempt_done":
            task_id = probe_tasks.get(data["probe"])
            if task_id is not None:
                progress.advance(task_id)
        elif event == "probe_done":
            task_id = probe_tasks.get(data["probe"])
            if task_id is not None:
                rate = data["pass_rate"]
                color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
                progress.update(
                    task_id,
                    description=f"[{color}]{data['probe']} ({rate:.0f}% pass)",
                )
        elif event == "probe_error":
            task_id = probe_tasks.get(data["probe"])
            if task_id is not None:
                progress.update(task_id, description=f"[red]{data['probe']} (error)")

    with progress:
        return await runner.run(
            profile=profile,
            probe_names=probe_list,
            detector_names=detector_list,
            checkpoint_enabled=checkpoint_enabled,
            on_progress=on_progress,
            run_all_detectors=run_all_detectors,
        )


# ---------------------------------------------------------------------------
# scan run
# ---------------------------------------------------------------------------

@scan_app.command("run")
def scan_run(
    model: str = typer.Option(..., "--model", "-m", help="LLM model (e.g., openai/gpt-4o)"),
    profile: str = typer.Option("standard", "--profile", "-p", help="Scan profile (quick, standard, full)"),
    probes: Optional[str] = typer.Option(None, "--probes", help="Comma-separated probe names"),
    detectors: Optional[str] = typer.Option(None, "--detectors", help="Comma-separated detector names"),
    output: Path = typer.Option(Path("./results"), "--output", "-o", help="Output directory"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json, html, markdown)"),
    no_checkpoint: bool = typer.Option(False, "--no-checkpoint", help="Disable checkpoint/resume"),
    ci: bool = typer.Option(False, "--ci", help="CI mode: minimal output, exit codes (0=pass, 1=fail, 2=error)"),
    threshold: float = typer.Option(80.0, "--threshold", help="Minimum pass rate to pass in CI mode (0-100)"),
    all_detectors: bool = typer.Option(False, "--all-detectors", help="Run ALL detectors on every attempt (for experiment/analysis)"),
    attacker_model: Optional[str] = typer.Option(None, "--attacker-model", help="Attacker LLM for adaptive probes (default: same as target)"),
    sarif: Optional[Path] = typer.Option(None, "--sarif", help="Output path for SARIF report"),
    junit: Optional[Path] = typer.Option(None, "--junit", help="Output path for JUnit XML report"),
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
    if attacker_model:
        config.probe_settings.adaptive_attacker_model = attacker_model

    probe_list = probes.split(",") if probes else None
    detector_list = detectors.split(",") if detectors else None

    if not ci:
        console.print(Panel(
            f"[bold]ATLAS Security Scan[/bold]\n"
            f"Model: [cyan]{model}[/cyan]\n"
            f"Profile: [green]{profile}[/green]\n"
            f"Probes: {probe_list or 'from profile'}\n"
            f"Detectors: {detector_list or 'from profile'}",
            title="Scan Configuration",
        ))
    else:
        print(f"[ATLAS] Starting scan: model={model} profile={profile}")

    runner = ScanRunner(config)

    try:
        if ci:
            result = asyncio.run(runner.run(
                profile=profile,
                probe_names=probe_list,
                detector_names=detector_list,
                checkpoint_enabled=not no_checkpoint,
                run_all_detectors=all_detectors,
            ))
        else:
            result = asyncio.run(_run_with_progress(
                runner,
                profile=profile,
                probe_list=probe_list,
                detector_list=detector_list,
                checkpoint_enabled=not no_checkpoint,
                run_all_detectors=all_detectors,
            ))
    except KeyboardInterrupt:
        if ci:
            print("[ATLAS] Scan interrupted.")
            raise typer.Exit(2)
        console.print("\n[yellow]Scan interrupted. Checkpoint saved.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        if ci:
            print(f"[ATLAS] Scan error: {e}")
            raise typer.Exit(2)
        console.print(f"\n[red]Scan failed: {e}[/red]")
        raise typer.Exit(1)

    # --- Save primary JSON result ---
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / f"scan_{result.scan_id[:8]}.json"
    with open(result_path, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    # --- Generate SARIF report if requested ---
    if sarif:
        _generate_sarif_report(result, sarif)
        if not ci:
            console.print(f"SARIF report: [bold]{sarif}[/bold]")
        else:
            print(f"[ATLAS] SARIF report written to {sarif}")

    # --- Generate JUnit report if requested ---
    if junit:
        _generate_junit_report(result, junit)
        if not ci:
            console.print(f"JUnit report: [bold]{junit}[/bold]")
        else:
            print(f"[ATLAS] JUnit report written to {junit}")

    # --- Display / output summary ---
    if ci:
        pass_rate = _compute_overall_pass_rate(result)
        _print_ci_summary(result, pass_rate, threshold)

        if pass_rate >= threshold:
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)
    else:
        _display_scan_summary(result)
        console.print(f"\nResults saved to: [bold]{result_path}[/bold]")

        # Generate additional report format if requested
        if format != "json":
            from atlas.cli.report import _generate_report
            _generate_report(result, output, format)


# ---------------------------------------------------------------------------
# scan compare
# ---------------------------------------------------------------------------

@scan_app.command("compare")
def scan_compare(
    models: str = typer.Option(..., "--models", help="Comma-separated list of models to compare"),
    profile: str = typer.Option("standard", "--profile", "-p", help="Scan profile (quick, standard, full)"),
    probes: Optional[str] = typer.Option(None, "--probes", help="Comma-separated probe names"),
    detectors: Optional[str] = typer.Option(None, "--detectors", help="Comma-separated detector names"),
    output: Path = typer.Option(Path("./results"), "--output", "-o", help="Output directory for results"),
    no_checkpoint: bool = typer.Option(False, "--no-checkpoint", help="Disable checkpoint/resume"),
    ctx: typer.Context = typer.Option(None, hidden=True),
) -> None:
    """Run the same probes against multiple models and compare results side-by-side."""
    from atlas.config.loader import load_config
    from atlas.core.models import ComparisonResult, ModelScore
    from atlas.engine.runner import ScanRunner

    config_file = None
    if ctx and ctx.obj:
        config_file = ctx.obj.get("config_file")

    model_list = [m.strip() for m in models.split(",") if m.strip()]

    if len(model_list) < 2:
        console.print("[red]At least 2 models required for comparison. Separate with commas.[/red]")
        raise typer.Exit(1)

    probe_list = probes.split(",") if probes else None
    detector_list = detectors.split(",") if detectors else None

    console.print(Panel(
        f"[bold]ATLAS Comparative Scan[/bold]\n"
        f"Models: [cyan]{', '.join(model_list)}[/cyan]\n"
        f"Profile: [green]{profile}[/green]\n"
        f"Probes: {probe_list or 'from profile'}\n"
        f"Detectors: {detector_list or 'from profile'}",
        title="Comparison Configuration",
    ))

    comparison = ComparisonResult(models=model_list)
    start_time = time.time()

    for model_name in model_list:
        console.print(f"\n[bold cyan]>>> Scanning model: {model_name}[/bold cyan]")

        config = load_config(config_file)
        config.provider.model = model_name
        config.output.directory = str(output)

        runner = ScanRunner(config)

        try:
            result = asyncio.run(runner.run(
                profile=profile,
                probe_names=probe_list,
                detector_names=detector_list,
                checkpoint_enabled=not no_checkpoint,
            ))
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Scan of {model_name} interrupted.[/yellow]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[red]Scan of {model_name} failed: {e}[/red]")
            raise typer.Exit(1)

        comparison.scan_results[model_name] = result

        # Save individual result
        output.mkdir(parents=True, exist_ok=True)
        result_path = output / f"scan_{model_name.replace('/', '_')}_{result.scan_id[:8]}.json"
        with open(result_path, "w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    # Build leaderboard
    leaderboard: list[ModelScore] = []
    for model_name, scan_result in comparison.scan_results.items():
        total_findings = len(scan_result.findings)
        failed_findings = sum(1 for f in scan_result.findings if not f.passed)
        pass_rate = _compute_overall_pass_rate(scan_result)

        leaderboard.append(ModelScore(
            model_name=model_name,
            overall_score=scan_result.security_score.overall_score,
            category_scores=scan_result.security_score.category_scores,
            risk_level=scan_result.security_score.risk_level,
            pass_rate=round(pass_rate, 2),
            total_findings=total_findings,
            failed_findings=failed_findings,
        ))

    # Sort by overall score descending
    leaderboard.sort(key=lambda ms: ms.overall_score, reverse=True)
    comparison.leaderboard = leaderboard
    comparison.completed_at = datetime.now(UTC)
    comparison.duration_ms = (time.time() - start_time) * 1000

    # Display comparison table
    _display_comparison_table(comparison)

    # Save comparison result
    output.mkdir(parents=True, exist_ok=True)
    comparison_path = output / f"comparison_{comparison.comparison_id[:8]}.json"
    with open(comparison_path, "w") as f:
        json.dump(comparison.model_dump(mode="json"), f, indent=2, default=str)

    console.print(f"\nComparison saved to: [bold]{comparison_path}[/bold]")


def _display_comparison_table(comparison) -> None:
    """Display a side-by-side comparison of model scan results."""
    from atlas.core.models import ComparisonResult

    model_names = comparison.models

    # --- Leaderboard ---
    console.print()
    lb_table = Table(title="Model Leaderboard")
    lb_table.add_column("Rank", justify="center", style="bold")
    lb_table.add_column("Model", style="cyan")
    lb_table.add_column("Score", justify="right")
    lb_table.add_column("Pass Rate", justify="right")
    lb_table.add_column("Risk Level", justify="center")
    lb_table.add_column("Failed Findings", justify="right")

    for idx, ms in enumerate(comparison.leaderboard, start=1):
        score_val = ms.overall_score
        if score_val >= 80:
            score_color = "green"
        elif score_val >= 60:
            score_color = "yellow"
        elif score_val >= 40:
            score_color = "red"
        else:
            score_color = "bold red"

        risk_color = {
            "minimal": "green",
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }.get(ms.risk_level.value, "white")

        lb_table.add_row(
            str(idx),
            ms.model_name,
            f"[{score_color}]{score_val:.1f}[/{score_color}]",
            f"{ms.pass_rate:.1f}%",
            f"[{risk_color}]{ms.risk_level.value.upper()}[/{risk_color}]",
            str(ms.failed_findings),
        )

    console.print(lb_table)

    # --- Per-probe comparison ---
    all_probes: set[str] = set()
    for sr in comparison.scan_results.values():
        all_probes.update(sr.probe_results.keys())

    if all_probes:
        probe_table = Table(title="Per-Probe Pass Rate Comparison")
        probe_table.add_column("Probe", style="bold")
        for m in model_names:
            probe_table.add_column(m, justify="center")

        for probe_name in sorted(all_probes):
            row_values: list[str] = []
            for m in model_names:
                sr = comparison.scan_results.get(m)
                if sr and probe_name in sr.probe_results:
                    rate = sr.probe_results[probe_name].pass_rate
                    rate_color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
                    row_values.append(f"[{rate_color}]{rate:.1f}%[/{rate_color}]")
                else:
                    row_values.append("[dim]N/A[/dim]")
            probe_table.add_row(probe_name, *row_values)

        console.print(probe_table)

    console.print(f"\nComparison completed in {comparison.duration_ms / 1000:.1f}s")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

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

    # Detector verdict breakdown for failed findings
    failed_findings = [f for pr in result.probe_results.values() for f in pr.findings if not f.passed]
    if failed_findings:
        det_table = Table(title="Detector Verdicts (failed findings)")
        det_table.add_column("Finding", style="cyan")
        det_table.add_column("Detector", style="bold")
        det_table.add_column("Verdict", justify="center")
        det_table.add_column("Confidence", justify="right")
        det_table.add_column("Weight", justify="right")

        for finding in failed_findings:
            finding_label = f"{finding.attempt.probe_name}:{finding.id[:8]}"
            pass_w = sum(r.confidence for r in finding.detector_results if r.passed)
            fail_w = sum(r.confidence for r in finding.detector_results if not r.passed)
            for i, dr in enumerate(finding.detector_results):
                verdict_color = "green" if dr.passed else "red"
                verdict_text = f"[{verdict_color}]{'pass' if dr.passed else 'fail'}[/{verdict_color}]"
                weight_text = f"[{verdict_color}]{dr.confidence:.2f} {'pass' if dr.passed else 'fail'}[/{verdict_color}]"
                det_table.add_row(
                    finding_label if i == 0 else "",
                    dr.detector_name,
                    verdict_text,
                    f"{dr.confidence:.2f}",
                    weight_text,
                )
            # Summary row
            result_color = "green" if pass_w >= fail_w else "red"
            det_table.add_row(
                "",
                "[dim]total[/dim]",
                "",
                "",
                f"[{result_color}]pass={pass_w:.2f} fail={fail_w:.2f}[/{result_color}]",
            )

        console.print(det_table)

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


# ---------------------------------------------------------------------------
# Existing list commands
# ---------------------------------------------------------------------------

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
