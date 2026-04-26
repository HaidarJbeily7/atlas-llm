"""PostgreSQL storage for ATLAS experiments, scans, findings, annotations, and review state.

Uses SQLAlchemy ORM with session-based access.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .models import (
    Annotation,
    Experiment,
    Finding,
    ReviewVote,
    Scan,
    Session as SessionModel,
    User,
)

VALID_STATUSES = {
    "pending",
    "confirmed_vulnerability",
    "false_positive",
    "needs_investigation",
    "wont_fix",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dt_iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


# ---- experiments ---------------------------------------------------------

def upsert_experiment(
    session: Session,
    exp_id: str,
    timestamp: str,
    models: list[str],
    conditions: list[str],
    finding_count: int,
) -> dict:
    now = _utcnow()
    stmt = pg_insert(Experiment).values(
        id=exp_id,
        timestamp=timestamp,
        models_json=json.dumps(models),
        conditions_json=json.dumps(conditions),
        finding_count=finding_count,
        created_at=now,
        updated_at=now,
    ).on_conflict_do_update(
        index_elements=["id"],
        set_={
            "timestamp": timestamp,
            "models_json": json.dumps(models),
            "conditions_json": json.dumps(conditions),
            "finding_count": finding_count,
            "updated_at": now,
        },
    )
    session.execute(stmt)
    session.flush()
    row = session.get(Experiment, exp_id)
    return _experiment_to_dict(row)


def _experiment_to_dict(row: Experiment) -> dict:
    return {
        "id": row.id,
        "timestamp": row.timestamp,
        "models_json": row.models_json,
        "conditions_json": row.conditions_json,
        "finding_count": row.finding_count,
        "created_at": _dt_iso(row.created_at),
        "updated_at": _dt_iso(row.updated_at),
    }


def get_experiment(session: Session, exp_id: str) -> dict | None:
    row = session.get(Experiment, exp_id)
    if row is None:
        return None
    d = _experiment_to_dict(row)
    d["models"] = json.loads(d.pop("models_json"))
    d["conditions"] = json.loads(d.pop("conditions_json"))
    return d


def get_latest_experiment_id(session: Session) -> str | None:
    stmt = select(Experiment.id).order_by(
        Experiment.timestamp.desc(), Experiment.updated_at.desc()
    ).limit(1)
    row = session.execute(stmt).scalar_one_or_none()
    return row


def list_experiments(session: Session) -> list[dict]:
    stmt = select(Experiment).order_by(
        Experiment.timestamp.desc(), Experiment.updated_at.desc()
    )
    rows = session.execute(stmt).scalars().all()
    out: list[dict] = []
    for r in rows:
        d = _experiment_to_dict(r)
        d["models"] = json.loads(d.pop("models_json"))
        d["conditions"] = json.loads(d.pop("conditions_json"))
        out.append(d)
    return out


def delete_experiment(session: Session, exp_id: str) -> bool:
    row = session.get(Experiment, exp_id)
    if row is None:
        return False
    session.delete(row)
    session.flush()
    return True


# ---- scans ---------------------------------------------------------------

def bulk_upsert_scans(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [
        {
            "scan_id": r["scan_id"],
            "experiment_id": r["experiment_id"],
            "model": r["model"],
            "model_short": r["model_short"],
            "probe": r["probe"],
            "started_at": r.get("started_at", ""),
            "completed_at": r.get("completed_at", ""),
            "duration_ms": r.get("duration_ms", 0),
            "total_cost_usd": r.get("total_cost_usd", 0),
            "total_target_tokens": r.get("total_target_tokens", 0),
            "total_attacker_tokens": r.get("total_attacker_tokens", 0),
            "security_score_json": json.dumps(r.get("security_score", {})),
            "compliance_assessment_json": json.dumps(r.get("compliance_assessment", {})),
            "recommendations_json": json.dumps(r.get("recommendations", [])),
            "probe_results_summary_json": json.dumps(r.get("probe_results_summary", {})),
        }
        for r in rows
    ]
    stmt = pg_insert(Scan).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["scan_id"],
        set_={col: stmt.excluded[col] for col in [
            "experiment_id", "model", "model_short", "probe",
            "started_at", "completed_at", "duration_ms",
            "total_cost_usd", "total_target_tokens", "total_attacker_tokens",
            "security_score_json", "compliance_assessment_json",
            "recommendations_json", "probe_results_summary_json",
        ]},
    )
    session.execute(stmt)
    session.flush()
    return len(rows)


def list_scans(session: Session, experiment_id: str) -> list[dict]:
    stmt = select(Scan).where(
        Scan.experiment_id == experiment_id
    ).order_by(Scan.started_at)
    rows = session.execute(stmt).scalars().all()
    out: list[dict] = []
    for r in rows:
        d = {
            "scan_id": r.scan_id,
            "experiment_id": r.experiment_id,
            "model": r.model,
            "model_short": r.model_short,
            "probe": r.probe,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "duration_ms": r.duration_ms,
            "total_cost_usd": r.total_cost_usd,
            "total_target_tokens": r.total_target_tokens,
            "total_attacker_tokens": r.total_attacker_tokens,
            "security_score": json.loads(r.security_score_json),
            "compliance_assessment": json.loads(r.compliance_assessment_json),
            "recommendations": json.loads(r.recommendations_json),
            "probe_results_summary": json.loads(r.probe_results_summary_json),
        }
        out.append(d)
    return out


def delete_scans_for_experiment(session: Session, experiment_id: str) -> int:
    stmt = delete(Scan).where(Scan.experiment_id == experiment_id)
    result = session.execute(stmt)
    return result.rowcount


# ---- findings ------------------------------------------------------------

_FINDING_INDEX_FIELDS = [
    "id", "experiment_id", "model", "model_short", "probe", "passed", "severity",
    "prompt_preview", "condition", "adaptivity", "interaction_mode",
    "num_messages", "num_target_calls", "num_attacker_calls",
    "cost_usd", "latency_ms", "target_tokens", "attacker_tokens",
    "detector_summary_json",
]


def _finding_index_dict(r: Finding) -> dict:
    d: dict = {}
    for f in _FINDING_INDEX_FIELDS:
        val = getattr(r, f)
        if f == "detector_summary_json":
            d["detector_summary"] = json.loads(val)
        elif isinstance(val, bool):
            d[f] = val
        else:
            d[f] = val
    return d


def bulk_upsert_findings(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    now = _utcnow()
    values = [
        {
            "id": r["id"],
            "experiment_id": r["experiment_id"],
            "model": r.get("model", ""),
            "model_short": r.get("model_short", ""),
            "probe": r.get("probe", ""),
            "passed": bool(r.get("passed")),
            "severity": r.get("severity", ""),
            "prompt_preview": r.get("prompt_preview", ""),
            "condition": r.get("condition", ""),
            "adaptivity": r.get("adaptivity", ""),
            "interaction_mode": r.get("interaction_mode", ""),
            "num_messages": r.get("num_messages", 0),
            "num_target_calls": r.get("num_target_calls", 0),
            "num_attacker_calls": r.get("num_attacker_calls", 0),
            "cost_usd": r.get("cost_usd", 0),
            "latency_ms": r.get("latency_ms", 0),
            "target_tokens": r.get("target_tokens", 0),
            "attacker_tokens": r.get("attacker_tokens", 0),
            "detector_summary_json": json.dumps(r.get("detector_summary", [])),
            "detail_json": r["detail_json"],
            "created_at": now,
        }
        for r in rows
    ]
    stmt = pg_insert(Finding).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={col: stmt.excluded[col] for col in [
            "experiment_id", "model", "model_short", "probe", "passed",
            "severity", "prompt_preview", "condition", "adaptivity",
            "interaction_mode", "num_messages", "num_target_calls",
            "num_attacker_calls", "cost_usd", "latency_ms",
            "target_tokens", "attacker_tokens",
            "detector_summary_json", "detail_json",
        ]},
    )
    session.execute(stmt)
    session.flush()
    return len(rows)


def get_finding(session: Session, finding_id: str) -> dict | None:
    row = session.get(Finding, finding_id)
    if row is None:
        return None
    d = _finding_index_dict(row)
    d["detail_json"] = row.detail_json
    d["created_at"] = _dt_iso(row.created_at)
    d["experiment_id"] = row.experiment_id
    return d


def findings_index(session: Session, experiment_id: str) -> list[dict]:
    stmt = select(Finding).where(
        Finding.experiment_id == experiment_id
    ).order_by(Finding.created_at)
    rows = session.execute(stmt).scalars().all()
    return [_finding_index_dict(r) for r in rows]


def list_findings_for_experiment(
    session: Session,
    experiment_id: str,
    *,
    model: str | None = None,
    probe: str | None = None,
    passed: bool | None = None,
) -> list[dict]:
    stmt = select(Finding).where(Finding.experiment_id == experiment_id)
    if model is not None:
        stmt = stmt.where(Finding.model == model)
    if probe is not None:
        stmt = stmt.where(Finding.probe == probe)
    if passed is not None:
        stmt = stmt.where(Finding.passed == passed)
    stmt = stmt.order_by(Finding.created_at.asc())
    rows = session.execute(stmt).scalars().all()
    return [_finding_index_dict(r) for r in rows]


def delete_findings_for_experiment(session: Session, experiment_id: str) -> int:
    stmt = delete(Finding).where(Finding.experiment_id == experiment_id)
    result = session.execute(stmt)
    return result.rowcount


# ---- annotations ---------------------------------------------------------

def _annotation_to_dict(r: Annotation) -> dict:
    return {
        "id": r.id,
        "finding_id": r.finding_id,
        "label": r.label,
        "note": r.note,
        "author": r.author,
        "created_at": _dt_iso(r.created_at),
        "updated_at": _dt_iso(r.updated_at),
    }


def list_annotations(session: Session, finding_id: str) -> list[dict]:
    stmt = select(Annotation).where(
        Annotation.finding_id == finding_id
    ).order_by(Annotation.created_at.asc())
    rows = session.execute(stmt).scalars().all()
    return [_annotation_to_dict(r) for r in rows]


def create_annotation(
    session: Session, finding_id: str, label: str, note: str, author: str
) -> dict:
    ann = Annotation(
        finding_id=finding_id,
        label=label,
        note=note,
        author=author,
    )
    session.add(ann)
    session.flush()
    session.refresh(ann)
    return _annotation_to_dict(ann)


def update_annotation(
    session: Session,
    ann_id: int,
    label: str | None,
    note: str | None,
    author: str | None,
) -> dict | None:
    ann = session.get(Annotation, ann_id)
    if ann is None:
        return None
    if label is not None:
        ann.label = label
    if note is not None:
        ann.note = note
    if author is not None:
        ann.author = author
    ann.updated_at = _utcnow()
    session.flush()
    session.refresh(ann)
    return _annotation_to_dict(ann)


def delete_annotation(session: Session, ann_id: int) -> bool:
    ann = session.get(Annotation, ann_id)
    if ann is None:
        return False
    session.delete(ann)
    session.flush()
    return True


def count_annotations_by_finding(session: Session) -> dict[str, int]:
    stmt = select(
        Annotation.finding_id,
        func.count().label("n"),
    ).group_by(Annotation.finding_id)
    rows = session.execute(stmt).all()
    return {r.finding_id: r.n for r in rows}


def stats(session: Session) -> dict:
    ann_count = session.execute(
        select(func.count()).select_from(Annotation)
    ).scalar_one()

    label_rows = session.execute(
        select(Annotation.label, func.count().label("n"))
        .where(Annotation.label != "")
        .group_by(Annotation.label)
    ).all()

    vote_rows = session.execute(
        select(ReviewVote.status, func.count().label("n"))
        .group_by(ReviewVote.status)
    ).all()

    user_count = session.execute(
        select(func.count()).select_from(User)
    ).scalar_one()

    findings_voted = session.execute(
        select(func.count(func.distinct(ReviewVote.finding_id)))
    ).scalar_one()

    return {
        "annotation_count": ann_count,
        "annotations_by_label": {r.label: r.n for r in label_rows},
        "votes_by_status": {r.status: r.n for r in vote_rows},
        "user_count": user_count,
        "findings_with_votes": findings_voted,
    }


# ---- users + sessions ---------------------------------------------------

def _user_to_dict(r: User) -> dict:
    return {
        "id": r.id,
        "username": r.username,
        "password_hash": r.password_hash,
        "created_at": _dt_iso(r.created_at),
    }


def create_user(session: Session, username: str, password_hash: str) -> dict:
    user = User(username=username, password_hash=password_hash)
    session.add(user)
    session.flush()
    session.refresh(user)
    return _user_to_dict(user)


def get_user_by_username(session: Session, username: str) -> dict | None:
    stmt = select(User).where(User.username == username)
    row = session.execute(stmt).scalar_one_or_none()
    return _user_to_dict(row) if row else None


def get_user(session: Session, user_id: int) -> dict | None:
    row = session.get(User, user_id)
    return _user_to_dict(row) if row else None


def create_session(session: Session, user_id: int, token: str, expires_at: str) -> None:
    sess = SessionModel(
        token=token,
        user_id=user_id,
        expires_at=datetime.fromisoformat(expires_at),
    )
    session.add(sess)
    session.flush()


def get_user_by_token(session: Session, token: str) -> dict | None:
    now = _utcnow()
    stmt = (
        select(User)
        .join(SessionModel, SessionModel.user_id == User.id)
        .where(SessionModel.token == token)
        .where(SessionModel.expires_at > now)
    )
    row = session.execute(stmt).scalar_one_or_none()
    return _user_to_dict(row) if row else None


def delete_session(session: Session, token: str) -> bool:
    stmt = delete(SessionModel).where(SessionModel.token == token)
    result = session.execute(stmt)
    return result.rowcount > 0


def purge_expired_sessions(session: Session) -> int:
    stmt = delete(SessionModel).where(SessionModel.expires_at <= _utcnow())
    result = session.execute(stmt)
    return result.rowcount


# ---- review votes + settlement ------------------------------------------

SETTLEMENT_OPEN = "open"
SETTLEMENT_PARTIAL = "partial"
SETTLEMENT_SETTLED = "settled"
SETTLEMENT_DISPUTED = "disputed"


def _vote_to_dict(r: ReviewVote, username: str | None = None) -> dict:
    d = {
        "id": r.id,
        "finding_id": r.finding_id,
        "user_id": r.user_id,
        "username": username or "",
        "status": r.status,
        "rationale": r.rationale,
        "created_at": _dt_iso(r.created_at),
        "updated_at": _dt_iso(r.updated_at),
    }
    return d


def cast_vote(
    session: Session,
    finding_id: str,
    user_id: int,
    status: str,
    rationale: str,
) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}")
    now = _utcnow()
    stmt = pg_insert(ReviewVote).values(
        finding_id=finding_id,
        user_id=user_id,
        status=status,
        rationale=rationale,
        created_at=now,
        updated_at=now,
    ).on_conflict_do_update(
        constraint="uq_review_votes_finding_user",
        set_={
            "status": status,
            "rationale": rationale,
            "updated_at": now,
        },
    )
    session.execute(stmt)
    session.flush()
    vote_stmt = select(ReviewVote).where(
        ReviewVote.finding_id == finding_id,
        ReviewVote.user_id == user_id,
    )
    row = session.execute(vote_stmt).scalar_one()
    return _vote_to_dict(row)


def remove_vote(session: Session, finding_id: str, user_id: int) -> bool:
    stmt = delete(ReviewVote).where(
        ReviewVote.finding_id == finding_id,
        ReviewVote.user_id == user_id,
    )
    result = session.execute(stmt)
    return result.rowcount > 0


def list_votes_for_finding(session: Session, finding_id: str) -> list[dict]:
    stmt = (
        select(ReviewVote, User.username)
        .join(User, User.id == ReviewVote.user_id)
        .where(ReviewVote.finding_id == finding_id)
        .order_by(ReviewVote.created_at.asc())
    )
    rows = session.execute(stmt).all()
    return [_vote_to_dict(r.ReviewVote, r.username) for r in rows]


def compute_settlement(votes: list[dict]) -> tuple[str, str | None]:
    if not votes:
        return SETTLEMENT_OPEN, None
    users_by_status: dict[str, set[int]] = {}
    for v in votes:
        users_by_status.setdefault(v["status"], set()).add(v["user_id"])
    distinct_users = set().union(*users_by_status.values())
    if len(distinct_users) < 2:
        return SETTLEMENT_PARTIAL, votes[0]["status"]
    for status, users in users_by_status.items():
        if len(users) >= 2:
            return SETTLEMENT_SETTLED, status
    return SETTLEMENT_DISPUTED, None


def review_summary_for_finding(session: Session, finding_id: str) -> dict:
    votes = list_votes_for_finding(session, finding_id)
    settlement, status = compute_settlement(votes)
    return {
        "finding_id": finding_id,
        "settlement": settlement,
        "status": status,
        "vote_count": len(votes),
        "distinct_voter_count": len({v["user_id"] for v in votes}),
        "votes": votes,
    }


def all_review_summaries(session: Session) -> list[dict]:
    stmt = (
        select(ReviewVote, User.username)
        .join(User, User.id == ReviewVote.user_id)
    )
    rows = session.execute(stmt).all()
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        vote_dict = _vote_to_dict(r.ReviewVote, r.username)
        grouped.setdefault(r.ReviewVote.finding_id, []).append(vote_dict)
    out: list[dict] = []
    for fid, votes in grouped.items():
        settlement, status = compute_settlement(votes)
        out.append({
            "finding_id": fid,
            "settlement": settlement,
            "status": status,
            "vote_count": len(votes),
            "distinct_voter_count": len({v["user_id"] for v in votes}),
        })
    return out


def review_stats_for_experiment(session: Session, experiment_id: str) -> dict:
    """Compute review progress and reviewed-only stats for an experiment.

    Returns counts of reviewed/unreviewed findings, breakdown by status,
    and pass/fail rates computed only from reviewed findings.
    """
    # Get all findings for this experiment
    findings = findings_index(session, experiment_id)
    if not findings:
        return _empty_review_stats()

    # Get all votes, grouped by finding
    vote_stmt = (
        select(ReviewVote, User.username)
        .join(User, User.id == ReviewVote.user_id)
    )
    vote_rows = session.execute(vote_stmt).all()
    votes_by_finding: dict[str, list[dict]] = {}
    for r in vote_rows:
        vote_dict = _vote_to_dict(r.ReviewVote, r.username)
        votes_by_finding.setdefault(r.ReviewVote.finding_id, []).append(vote_dict)

    # Build a set of finding IDs in this experiment for fast lookup
    exp_finding_ids = {f["id"] for f in findings}

    needs_review = 0
    reviewed = 0
    confirmed = 0
    false_positive = 0
    investigating = 0
    wont_fix = 0
    disputed = 0
    reviewed_pass = 0
    reviewed_fail = 0

    for f in findings:
        fid = f["id"]
        votes = votes_by_finding.get(fid, [])
        # Only consider votes for findings in this experiment
        if fid not in exp_finding_ids:
            continue

        settlement, status = compute_settlement(votes)

        if settlement == SETTLEMENT_OPEN:
            needs_review += 1
        else:
            reviewed += 1
            if settlement == SETTLEMENT_DISPUTED:
                disputed += 1
            elif status == "confirmed_vulnerability":
                confirmed += 1
            elif status == "false_positive":
                false_positive += 1
            elif status == "needs_investigation":
                investigating += 1
            elif status == "wont_fix":
                wont_fix += 1

            if f["passed"]:
                reviewed_pass += 1
            else:
                reviewed_fail += 1

    total = len(findings)
    reviewed_total = reviewed_pass + reviewed_fail
    return {
        "total": total,
        "needs_review": needs_review,
        "reviewed": reviewed,
        "confirmed": confirmed,
        "false_positive": false_positive,
        "investigating": investigating,
        "wont_fix": wont_fix,
        "disputed": disputed,
        "reviewed_pass_rate": round((reviewed_pass / reviewed_total) * 100, 1)
        if reviewed_total > 0
        else None,
        "reviewed_fail_count": reviewed_fail,
        "reviewed_pass_count": reviewed_pass,
    }


def delete_data_for_model(session: Session, model_substr: str) -> dict:
    """Delete all scans, findings (and their annotations/votes), for a model.

    Also updates each affected experiment's models_json and finding_count.
    Returns a summary of what was deleted.
    """
    # 1. Find affected findings and delete their annotations + votes first
    affected_findings = session.execute(
        select(Finding.id, Finding.experiment_id).where(
            Finding.model.ilike(f"%{model_substr}%")
        )
    ).all()
    finding_ids = [r.id for r in affected_findings]
    affected_experiment_ids = list({r.experiment_id for r in affected_findings})

    annotations_deleted = 0
    votes_deleted = 0
    if finding_ids:
        annotations_deleted = session.execute(
            delete(Annotation).where(Annotation.finding_id.in_(finding_ids))
        ).rowcount
        votes_deleted = session.execute(
            delete(ReviewVote).where(ReviewVote.finding_id.in_(finding_ids))
        ).rowcount

    # 2. Collect experiment IDs from scans before deleting
    scan_exp_ids = [
        r[0] for r in session.execute(
            select(func.distinct(Scan.experiment_id)).where(
                Scan.model.ilike(f"%{model_substr}%")
            )
        ).all()
    ]
    all_exp_ids = list(set(affected_experiment_ids + scan_exp_ids))

    # 3. Delete findings
    findings_deleted = session.execute(
        delete(Finding).where(Finding.model.ilike(f"%{model_substr}%"))
    ).rowcount

    # 4. Delete scans
    scans_deleted = session.execute(
        delete(Scan).where(Scan.model.ilike(f"%{model_substr}%"))
    ).rowcount

    # 5. Update affected experiments (models_json + finding_count)

    for exp_id in all_exp_ids:
        remaining_models = [
            r[0] for r in session.execute(
                select(func.distinct(Scan.model)).where(Scan.experiment_id == exp_id)
            ).all()
        ]
        remaining_finding_count = session.execute(
            select(func.count()).select_from(Finding).where(
                Finding.experiment_id == exp_id
            )
        ).scalar_one()

        session.execute(
            update(Experiment).where(Experiment.id == exp_id).values(
                models_json=json.dumps(remaining_models),
                finding_count=remaining_finding_count,
                updated_at=_utcnow(),
            )
        )

    session.flush()
    return {
        "model_filter": model_substr,
        "findings_deleted": findings_deleted,
        "scans_deleted": scans_deleted,
        "annotations_deleted": annotations_deleted,
        "votes_deleted": votes_deleted,
        "experiments_updated": len(all_exp_ids),
    }


def _empty_review_stats() -> dict:
    return {
        "total": 0,
        "needs_review": 0,
        "reviewed": 0,
        "confirmed": 0,
        "false_positive": 0,
        "investigating": 0,
        "wont_fix": 0,
        "disputed": 0,
        "reviewed_pass_rate": None,
        "reviewed_fail_count": 0,
        "reviewed_pass_count": 0,
    }
