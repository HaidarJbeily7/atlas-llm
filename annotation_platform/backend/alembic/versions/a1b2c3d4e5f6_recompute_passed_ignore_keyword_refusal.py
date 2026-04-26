"""recompute passed ignoring keyword and refusal detectors

Revision ID: a1b2c3d4e5f6
Revises: e85d9b08cde7
Create Date: 2026-04-20 12:00:00.000000

"""
from typing import Sequence, Union

import json

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e85d9b08cde7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IGNORED_DETECTORS = {"keyword", "refusal"}


def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: Recompute finding-level passed, ignoring keyword & refusal
    rows = conn.execute(
        sa.text("SELECT id, detector_summary_json, passed FROM findings")
    ).fetchall()

    updated = 0
    for row in rows:
        finding_id, detector_json, old_passed = row
        detectors = json.loads(detector_json) if detector_json else []

        scoring = [d for d in detectors if d.get("name", "") not in _IGNORED_DETECTORS]
        new_passed = all(d.get("passed", False) for d in scoring) if scoring else True

        if new_passed != old_passed:
            conn.execute(
                sa.text("UPDATE findings SET passed = :passed WHERE id = :id"),
                {"passed": new_passed, "id": finding_id},
            )
            updated += 1

    print(f"  -> Updated {updated}/{len(rows)} findings")

    # Step 2: Recompute scan-level probe_results_summary from updated findings
    scans = conn.execute(
        sa.text("SELECT scan_id, model, experiment_id, probe_results_summary_json FROM scans")
    ).fetchall()

    scan_updated = 0
    for scan_id, model, experiment_id, prs_json in scans:
        prs = json.loads(prs_json) if prs_json else {}
        changed = False

        for probe_name, data in prs.items():
            row = conn.execute(
                sa.text("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed,
                           SUM(CASE WHEN NOT passed THEN 1 ELSE 0 END) as failed
                    FROM findings
                    WHERE experiment_id = :exp_id AND probe = :probe AND model = :model
                """),
                {"exp_id": experiment_id, "probe": probe_name, "model": model},
            ).fetchone()

            if row and row[0] > 0:
                total, new_passed, new_failed = row
                if data.get("passed") != new_passed or data.get("failed") != new_failed:
                    data["passed"] = new_passed
                    data["failed"] = new_failed
                    data["total_attempts"] = total
                    data["pass_rate"] = round(new_passed / total * 100, 2) if total else 0
                    changed = True

        if changed:
            conn.execute(
                sa.text("UPDATE scans SET probe_results_summary_json = :prs WHERE scan_id = :sid"),
                {"prs": json.dumps(prs), "sid": scan_id},
            )
            scan_updated += 1

    print(f"  -> Updated {scan_updated}/{len(scans)} scan summaries")


def downgrade() -> None:
    conn = op.get_bind()

    # Step 1: Recompute findings using ALL detectors (original logic)
    rows = conn.execute(
        sa.text("SELECT id, detector_summary_json FROM findings")
    ).fetchall()

    for row in rows:
        finding_id, detector_json = row
        detectors = json.loads(detector_json) if detector_json else []
        original_passed = all(d.get("passed", False) for d in detectors) if detectors else True

        conn.execute(
            sa.text("UPDATE findings SET passed = :passed WHERE id = :id"),
            {"passed": original_passed, "id": finding_id},
        )

    # Step 2: Recompute scan-level stats from reverted findings
    scans = conn.execute(
        sa.text("SELECT scan_id, model, experiment_id, probe_results_summary_json FROM scans")
    ).fetchall()

    for scan_id, model, experiment_id, prs_json in scans:
        prs = json.loads(prs_json) if prs_json else {}

        for probe_name, data in prs.items():
            row = conn.execute(
                sa.text("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed,
                           SUM(CASE WHEN NOT passed THEN 1 ELSE 0 END) as failed
                    FROM findings
                    WHERE experiment_id = :exp_id AND probe = :probe AND model = :model
                """),
                {"exp_id": experiment_id, "probe": probe_name, "model": model},
            ).fetchone()

            if row and row[0] > 0:
                total, new_passed, new_failed = row
                data["passed"] = new_passed
                data["failed"] = new_failed
                data["total_attempts"] = total
                data["pass_rate"] = round(new_passed / total * 100, 2) if total else 0

        conn.execute(
            sa.text("UPDATE scans SET probe_results_summary_json = :prs WHERE scan_id = :sid"),
            {"prs": json.dumps(prs), "sid": scan_id},
        )
