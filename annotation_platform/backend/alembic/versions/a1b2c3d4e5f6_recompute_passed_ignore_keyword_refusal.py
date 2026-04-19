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


def downgrade() -> None:
    # Recompute using ALL detectors (original logic)
    conn = op.get_bind()

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
