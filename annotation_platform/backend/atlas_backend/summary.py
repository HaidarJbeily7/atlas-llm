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

    # Load review verdicts: finding_id -> settled status (or None)
    reviews = db.all_review_summaries(session)
    verdict_map: dict[str, str | None] = {}  # finding_id -> "confirmed_vulnerability" | "false_positive" | ...
    for r in reviews:
        if r["settlement"] not in ("open",):
            verdict_map[r["finding_id"]] = r.get("status")

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

    # Detector stats aggregation (overall)
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

    # --- RQ1: Condition stats (ASR & cost by condition) ---
    # "false_positive" = human says the judge was WRONG (regardless of pass/fail).
    # "confirmed_vulnerability" = human says the judge was CORRECT.
    # Adjusted stats exclude all false-positive findings entirely (unreliable data).
    cond_agg: dict[str, dict] = {}
    for f in findings:
        probe = f.get("probe", "unknown")
        if probe not in cond_agg:
            cond_agg[probe] = {
                "condition": probe,
                "total": 0, "passed": 0, "failed": 0,
                "adj_total": 0, "adj_passed": 0, "adj_failed": 0,
                "false_positives": 0, "reviewed": 0,
                "total_cost": 0.0, "target_tokens": 0, "attacker_tokens": 0,
            }
        ca = cond_agg[probe]
        ca["total"] += 1
        passed = f.get("passed")
        if passed:
            ca["passed"] += 1
        else:
            ca["failed"] += 1
        ca["total_cost"] += f.get("cost_usd", 0)
        ca["target_tokens"] += f.get("target_tokens", 0)
        ca["attacker_tokens"] += f.get("attacker_tokens", 0)
        verdict = verdict_map.get(f["id"])
        if verdict is not None:
            ca["reviewed"] += 1
        if verdict == "false_positive":
            # Judge was wrong — exclude from adjusted stats
            ca["false_positives"] += 1
        else:
            # Judge was correct (confirmed) or unreviewed (trusted)
            ca["adj_total"] += 1
            if passed:
                ca["adj_passed"] += 1
            else:
                ca["adj_failed"] += 1
    condition_stats = []
    for ca in cond_agg.values():
        total_tok = ca["target_tokens"] + ca["attacker_tokens"]
        attacker_cost = ca["total_cost"] * ca["attacker_tokens"] / max(1, total_tok)
        condition_stats.append({
            "condition": ca["condition"],
            "total": ca["total"],
            "passed": ca["passed"],
            "failed": ca["failed"],
            "asr": round(ca["failed"] / max(1, ca["total"]) * 100, 2),
            # Adjusted: FP findings excluded entirely (judge was wrong)
            "adj_total": ca["adj_total"],
            "adj_failed": ca["adj_failed"],
            "adj_asr": round(ca["adj_failed"] / max(1, ca["adj_total"]) * 100, 2),
            "false_positives": ca["false_positives"],
            "reviewed": ca["reviewed"],
            # Costs
            "total_cost": round(ca["total_cost"], 8),
            "target_cost": round(ca["total_cost"] - attacker_cost, 8),
            "attacker_cost": round(attacker_cost, 8),
            "cost_per_attack": round(ca["total_cost"] / max(1, ca["adj_failed"]), 8),
            "target_tokens": ca["target_tokens"],
            "attacker_tokens": ca["attacker_tokens"],
        })

    # --- RQ2: Failure-type distribution (which detectors flag failures, by condition) ---
    # Only counts confirmed vulnerabilities (excludes false positives)
    failure_types: dict[str, dict[str, int]] = {}
    failure_types_all: dict[str, dict[str, int]] = {}
    for f in findings:
        if f.get("passed"):
            continue  # only look at failed findings
        probe = f.get("probe", "unknown")
        verdict = verdict_map.get(f["id"])
        # All failures (raw)
        if probe not in failure_types_all:
            failure_types_all[probe] = {}
        for ds in f.get("detector_summary", []):
            if not ds["passed"]:
                name = ds["name"]
                failure_types_all[probe][name] = failure_types_all[probe].get(name, 0) + 1
        # Confirmed only (skip false positives)
        if verdict == "false_positive":
            continue
        if probe not in failure_types:
            failure_types[probe] = {}
        for ds in f.get("detector_summary", []):
            if not ds["passed"]:
                name = ds["name"]
                failure_types[probe][name] = failure_types[probe].get(name, 0) + 1
    failure_type_distribution = [
        {
            "condition": cond,
            "detector_failures": failure_types.get(cond, {}),
            "detector_failures_all": failure_types_all.get(cond, {}),
        }
        for cond in set(list(failure_types.keys()) + list(failure_types_all.keys()))
    ]

    # --- RQ3: Detector sensitivity by condition ---
    # "false_positive" = human says judge was WRONG on this finding (any direction).
    # "confirmed_vulnerability" = human says judge was CORRECT (confirmed verdict).
    # We track how often each detector's findings are overturned by human review.
    det_cond_agg: dict[str, dict[str, dict]] = {}  # detector -> condition -> stats
    for f in findings:
        probe = f.get("probe", "unknown")
        verdict = verdict_map.get(f["id"])
        for ds in f.get("detector_summary", []):
            name = ds["name"]
            if name not in det_cond_agg:
                det_cond_agg[name] = {}
            if probe not in det_cond_agg[name]:
                det_cond_agg[name][probe] = {
                    "total": 0, "passed": 0, "failed": 0, "score_sum": 0.0,
                    "reviewed": 0,          # findings with any human verdict
                    "confirmed": 0,         # human says judge was correct
                    "judge_errors": 0,      # human says judge was wrong (false_positive)
                }
            dc = det_cond_agg[name][probe]
            dc["total"] += 1
            if ds["passed"]:
                dc["passed"] += 1
            else:
                dc["failed"] += 1
            dc["score_sum"] += ds.get("score", 0)
            # Cross-reference with human review (applies to ALL findings, not just fails)
            if verdict is not None:
                dc["reviewed"] += 1
                if verdict == "confirmed_vulnerability":
                    dc["confirmed"] += 1
                elif verdict == "false_positive":
                    dc["judge_errors"] += 1
    detector_by_condition = []
    for det_name, conds in det_cond_agg.items():
        by_cond = {}
        for cond, dc in conds.items():
            reviewed = dc["reviewed"]
            by_cond[cond] = {
                "total": dc["total"],
                "passed": dc["passed"],
                "failed": dc["failed"],
                "fail_rate": round(dc["failed"] / max(1, dc["total"]) * 100, 2),
                "avg_score": round(dc["score_sum"] / max(1, dc["total"]), 4),
                # Human review: judge accuracy across all reviewed findings
                "reviewed": reviewed,
                "confirmed": dc["confirmed"],       # judge was correct
                "judge_errors": dc["judge_errors"],  # judge was wrong
                "accuracy": round(dc["confirmed"] / max(1, reviewed) * 100, 2),
                "error_rate": round(dc["judge_errors"] / max(1, reviewed) * 100, 2),
            }
        detector_by_condition.append({
            "detector": det_name,
            "by_condition": by_cond,
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
        "detector_stats": list(detector_agg.values()),
        "condition_stats": condition_stats,
        "failure_type_distribution": failure_type_distribution,
        "detector_by_condition": detector_by_condition,
    }
