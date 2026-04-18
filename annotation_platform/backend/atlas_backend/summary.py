"""Compute the experiment summary on-the-fly from DB tables, with caching."""

from __future__ import annotations

import threading

from sqlalchemy.orm import Session

from . import db

_cache_lock = threading.Lock()
_cache: dict[str, dict] = {}


def invalidate(experiment_id: str | None = None) -> None:
    with _cache_lock:
        if experiment_id is None:
            _cache.clear()
        else:
            _cache.pop(experiment_id, None)


def get_summary(session: Session, experiment_id: str) -> dict | None:
    with _cache_lock:
        cached = _cache.get(experiment_id)
    if cached is not None:
        return cached

    result = _compute(session, experiment_id)
    if result is None:
        return None

    with _cache_lock:
        _cache[experiment_id] = result
    return result


def _compute(session: Session, experiment_id: str) -> dict | None:
    exp = db.get_experiment(session, experiment_id)
    if exp is None:
        return None

    scans = db.list_scans(session, experiment_id)
    findings = db.findings_index(session, experiment_id)

    scan_summaries: list[dict] = []
    for s in scans:
        scan_summaries.append({
            "model": s["model"],
            "model_short": s["model_short"],
            "scan_id": s["scan_id"],
            "probe": s["probe"],
            "started_at": s["started_at"],
            "completed_at": s["completed_at"],
            "duration_ms": s["duration_ms"],
            "total_cost_usd": s["total_cost_usd"],
            "total_target_tokens": s["total_target_tokens"],
            "total_attacker_tokens": s["total_attacker_tokens"],
            "security_score": s["security_score"],
            "compliance_assessment": s["compliance_assessment"],
            "recommendations": s["recommendations"],
            "probe_results_summary": s["probe_results_summary"],
        })

    probe_agg: dict[str, dict] = {}
    for s in scans:
        model_short = s["model_short"]
        for probe_name, pr in s["probe_results_summary"].items():
            if probe_name not in probe_agg:
                probe_agg[probe_name] = {
                    "probe_name": probe_name,
                    "total_attempts": 0,
                    "passed": 0,
                    "failed": 0,
                    "models": {},
                }
            pa = probe_agg[probe_name]
            pa["total_attempts"] += pr.get("total_attempts", 0)
            pa["passed"] += pr.get("passed", 0)
            pa["failed"] += pr.get("failed", 0)
            pa["models"][model_short] = {
                "pass_rate": pr.get("pass_rate", 0),
                "passed": pr.get("passed", 0),
                "failed": pr.get("failed", 0),
                "total_attempts": pr.get("total_attempts", 0),
            }

    compliance: list[dict] = []
    for s in scans:
        ca = s.get("compliance_assessment") or {}
        for article in ca.get("article_details", []):
            compliance.append({
                "model": s["model"],
                "model_short": s["model_short"],
                **article,
            })

    return {
        "experiment": {
            "id": exp["id"],
            "timestamp": exp["timestamp"],
            "models": exp["models"],
            "conditions": exp["conditions"],
        },
        "scans": scan_summaries,
        "probes": list(probe_agg.values()),
        "findings_index": findings,
        "compliance": compliance,
    }
