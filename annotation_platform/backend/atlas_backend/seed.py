"""Seed the backend DB directly from raw experiment directories."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from . import db


# ---- Progress tracking ---------------------------------------------------

class ProgressCallback(Protocol):
    def __call__(self, stage: str, current: int, total: int, detail: str = "") -> None: ...


def _noop_progress(stage: str, current: int, total: int, detail: str = "") -> None:
    pass


def cli_progress(stage: str, current: int, total: int, detail: str = "") -> None:
    """Print progress to stderr with a carriage-return overwrite."""
    pct = (current / total * 100) if total else 0
    suffix = f"  {detail}" if detail else ""
    print(f"\r  [{stage}] {current}/{total} ({pct:.0f}%){suffix}", end="", flush=True, file=sys.stderr)
    if current >= total:
        print(file=sys.stderr)  # newline when done


@dataclass
class SeedResult:
    experiment_id: str
    timestamp: str
    scans_seeded: int
    findings_seeded: int
    warnings: list[str] = field(default_factory=list)
    source_dir: str = ""

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "timestamp": self.timestamp,
            "scans_seeded": self.scans_seeded,
            "findings_seeded": self.findings_seeded,
            "warnings": self.warnings,
            "source_dir": self.source_dir,
        }


def _short_model(model: str) -> str:
    return model.split("/")[-1]


def _discover_scan_files(exp_dir: Path) -> list[tuple[Path, Path, Path]]:
    """Return list of (model_dir, probe_dir, scan_path) tuples."""
    scan_files: list[tuple[Path, Path, Path]] = []
    for model_dir in sorted(exp_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        for probe_dir in sorted(model_dir.iterdir()):
            if not probe_dir.is_dir():
                continue
            for scan_path in sorted(probe_dir.glob("scan_*.json")):
                scan_files.append((model_dir, probe_dir, scan_path))
    return scan_files


def seed_experiment(
    session: Session,
    exp_dir: Path,
    progress: ProgressCallback = _noop_progress,
) -> SeedResult:
    """Seed one experiment from its raw directory."""
    exp_dir = exp_dir.resolve()
    meta_path = exp_dir / "experiment_meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"No experiment_meta.json in {exp_dir}")

    meta = json.loads(meta_path.read_text())
    exp_id = exp_dir.name
    timestamp = str(meta.get("timestamp", exp_id))

    # Phase 1: discover scan files
    progress("discovering", 0, 1, exp_id)
    scan_files = _discover_scan_files(exp_dir)
    total_scans = len(scan_files)
    progress("discovering", 1, 1, f"{total_scans} scan files found")

    # Phase 2: parse scan files
    scan_rows: list[dict] = []
    finding_rows: list[dict] = []
    warnings: list[str] = []

    for i, (model_dir, probe_dir, scan_path) in enumerate(scan_files, 1):
        progress("parsing", i, total_scans, scan_path.name)

        try:
            scan = json.loads(scan_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            warnings.append(f"skip {scan_path.name}: {e}")
            continue

        model = scan.get("model_name", "")
        model_short = _short_model(model)

        probe_results_summary: dict[str, dict] = {}
        for probe_name, pr in scan.get("probe_results", {}).items():
            probe_results_summary[probe_name] = {
                "probe_name": pr.get("probe_name", probe_name),
                "category": pr.get("category", ""),
                "total_attempts": pr.get("total_attempts", 0),
                "passed": pr.get("passed", 0),
                "failed": pr.get("failed", 0),
                "pass_rate": pr.get("pass_rate", 0),
            }

            for finding in pr.get("findings", []):
                fid = finding.get("id")
                if not fid:
                    continue
                attempt = finding.get("attempt", {})
                fmeta = attempt.get("metadata", {})

                detector_summary = [
                    {
                        "name": d.get("detector_name", ""),
                        "passed": d.get("passed", False),
                        "score": d.get("score", 0),
                    }
                    for d in finding.get("detector_results", [])
                ]

                finding_rows.append({
                    "id": fid,
                    "experiment_id": exp_id,
                    "model": model,
                    "model_short": model_short,
                    "probe": attempt.get("probe_name", probe_name),
                    "passed": bool(finding.get("passed")),
                    "severity": finding.get("severity", ""),
                    "prompt_preview": str(attempt.get("prompt", ""))[:120],
                    "condition": str(fmeta.get("condition", "")),
                    "adaptivity": str(fmeta.get("adaptivity", "")),
                    "interaction_mode": str(fmeta.get("interaction_mode", "")),
                    "num_messages": len(attempt.get("messages", [])),
                    "num_target_calls": attempt.get("num_target_calls", 0),
                    "num_attacker_calls": attempt.get("num_attacker_calls", 0),
                    "cost_usd": attempt.get("cost_usd", 0),
                    "latency_ms": attempt.get("latency_ms", 0),
                    "target_tokens": (
                        attempt.get("target_tokens_in", 0)
                        + attempt.get("target_tokens_out", 0)
                    ),
                    "attacker_tokens": (
                        attempt.get("attacker_tokens_in", 0)
                        + attempt.get("attacker_tokens_out", 0)
                    ),
                    "detector_summary": detector_summary,
                    "detail_json": json.dumps(finding, default=str),
                })

        scan_rows.append({
            "scan_id": scan.get("scan_id", scan_path.stem),
            "experiment_id": exp_id,
            "model": model,
            "model_short": model_short,
            "probe": probe_dir.name,
            "started_at": scan.get("started_at", ""),
            "completed_at": scan.get("completed_at", ""),
            "duration_ms": scan.get("duration_ms", 0),
            "total_cost_usd": scan.get("total_cost_usd", 0),
            "total_target_tokens": scan.get("total_target_tokens", 0),
            "total_attacker_tokens": scan.get("total_attacker_tokens", 0),
            "security_score": scan.get("security_score", {}),
            "compliance_assessment": scan.get("compliance_assessment", {}),
            "recommendations": scan.get("recommendations", []),
            "probe_results_summary": probe_results_summary,
        })

    # Phase 3: write to DB
    progress("db:experiment", 0, 1, exp_id)
    db.upsert_experiment(
        session,
        exp_id=exp_id,
        timestamp=timestamp,
        models=list(meta.get("models", [])),
        conditions=list(meta.get("conditions", [])),
        finding_count=len(finding_rows),
    )
    progress("db:experiment", 1, 1, exp_id)

    total_scans_to_write = len(scan_rows)
    progress("db:scans", 0, total_scans_to_write)
    db.bulk_upsert_scans(session, scan_rows)
    progress("db:scans", total_scans_to_write, total_scans_to_write)

    total_findings = len(finding_rows)
    progress("db:findings", 0, total_findings)
    db.bulk_upsert_findings(session, finding_rows)
    progress("db:findings", total_findings, total_findings)

    return SeedResult(
        experiment_id=exp_id,
        timestamp=timestamp,
        scans_seeded=len(scan_rows),
        findings_seeded=len(finding_rows),
        warnings=warnings,
        source_dir=str(exp_dir),
    )


def _find_experiment_dirs(root: Path) -> list[Path]:
    candidates: list[Path] = []
    if (root / "experiment_meta.json").is_file():
        candidates.append(root)
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "experiment_meta.json").is_file():
            candidates.append(child)
    return candidates


def seed_from_directory(
    session: Session,
    path: Path,
    *,
    recursive: bool = False,
    progress: ProgressCallback = _noop_progress,
) -> list[SeedResult]:
    path = path.resolve()
    if not path.is_dir():
        raise NotADirectoryError(str(path))

    if recursive:
        targets = _find_experiment_dirs(path)
    else:
        targets = [path]

    if not targets:
        raise FileNotFoundError(
            f"No experiment directories (with experiment_meta.json) found under {path}"
        )

    results: list[SeedResult] = []
    for i, t in enumerate(targets, 1):
        progress("experiments", i, len(targets), t.name)
        try:
            results.append(seed_experiment(session, t, progress=progress))
        except Exception as e:
            print(f"warning: skipping {t.name}: {e}", file=sys.stderr)
    return results
