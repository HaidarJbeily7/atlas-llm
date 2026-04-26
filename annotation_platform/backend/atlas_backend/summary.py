"""Compute the experiment summary on-the-fly from DB tables, with a 3-minute TTL cache."""

from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from . import db

_CACHE_TTL_SECONDS = 180  # 3 minutes

_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}  # experiment_id -> (timestamp, data)


def invalidate(experiment_id: str | None = None) -> None:
    with _cache_lock:
        if experiment_id is None:
            _cache.clear()
        else:
            _cache.pop(experiment_id, None)


def get_summary(session: Session, experiment_id: str) -> dict | None:
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(experiment_id)
    if entry is not None:
        cached_at, data = entry
        if now - cached_at < _CACHE_TTL_SECONDS:
            return data
        # Expired — remove it
        with _cache_lock:
            _cache.pop(experiment_id, None)

    result = _compute(session, experiment_id)
    if result is None:
        return None

    with _cache_lock:
        _cache[experiment_id] = (now, result)
    return result


def _compute(session: Session, experiment_id: str) -> dict | None:
    exp = db.get_experiment(session, experiment_id)
    if exp is None:
        return None

    scans = db.list_scans(session, experiment_id)
    findings = db.findings_index(session, experiment_id)

    scan_summaries: list[dict] = []
    for s in scans:
        total_tokens = s["total_target_tokens"] + s["total_attacker_tokens"]
        attacker_cost = s["total_cost_usd"] * s["total_attacker_tokens"] / max(1, total_tokens)
        target_cost = s["total_cost_usd"] - attacker_cost
        scan_summaries.append({
            "model": s["model"],
            "model_short": s["model_short"],
            "scan_id": s["scan_id"],
            "probe": s["probe"],
            "started_at": s["started_at"],
            "completed_at": s["completed_at"],
            "duration_ms": s["duration_ms"],
            "total_cost_usd": s["total_cost_usd"],
            "total_target_cost_usd": target_cost,
            "total_attacker_cost_usd": attacker_cost,
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

    # Detector stats aggregation
    detector_agg: dict[str, dict] = {}
    for f in findings:
        for ds in f.get("detector_summary", []):
            name = ds["name"]
            if name not in detector_agg:
                detector_agg[name] = {"name": name, "total": 0, "passed": 0, "failed": 0, "score_sum": 0.0}
            da = detector_agg[name]
            da["total"] += 1
            if ds["passed"]:
                da["passed"] += 1
            else:
                da["failed"] += 1
            da["score_sum"] += ds.get("score", 0)
    for da in detector_agg.values():
        da["avg_score"] = round(da["score_sum"] / max(1, da["total"]), 4)
        del da["score_sum"]

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
        "detector_stats": list(detector_agg.values()),
    }
