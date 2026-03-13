"""SQLite-based storage for ATLAS scan history."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from atlas.core.models import ScanResult


class HistoryStorage:
    """Persistent storage for scan results using SQLite.

    Stores scan results as JSON with indexed columns for efficient
    querying by scan ID, model name, timestamp, and overall score.
    """

    def __init__(self, db_path: str = ".atlas/history.db") -> None:
        """Initialize the history storage.

        Args:
            db_path: Path to the SQLite database file. Parent directories
                     are created automatically if they don't exist.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create the database tables and indices if they don't exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    scan_id        TEXT PRIMARY KEY,
                    model_name     TEXT NOT NULL,
                    provider       TEXT NOT NULL DEFAULT '',
                    profile        TEXT NOT NULL DEFAULT '',
                    timestamp      TEXT NOT NULL,
                    duration_ms    REAL NOT NULL DEFAULT 0.0,
                    overall_score  REAL NOT NULL DEFAULT 0.0,
                    risk_level     TEXT NOT NULL DEFAULT '',
                    total_probes   INTEGER NOT NULL DEFAULT 0,
                    total_findings INTEGER NOT NULL DEFAULT 0,
                    result_json    TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scans_model ON scans (model_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans (timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scans_score ON scans (overall_score)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Create a database connection that is properly closed after use."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_scan(self, result: ScanResult) -> None:
        """Save a scan result to the database.

        Args:
            result: The completed scan result to persist.
        """
        timestamp = (
            result.started_at.isoformat()
            if result.started_at
            else datetime.utcnow().isoformat()
        )
        result_json = result.model_dump_json()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scans
                    (scan_id, model_name, provider, profile, timestamp,
                     duration_ms, overall_score, risk_level,
                     total_probes, total_findings, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.scan_id,
                    result.model_name,
                    result.provider,
                    result.profile,
                    timestamp,
                    result.duration_ms,
                    result.security_score.overall_score,
                    result.security_score.risk_level.value
                    if result.security_score.risk_level
                    else "",
                    len(result.probe_results),
                    len(result.findings),
                    result_json,
                ),
            )

    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Retrieve a scan result by its ID.

        Args:
            scan_id: The unique scan identifier.

        Returns:
            A dictionary with scan metadata and the full result,
            or ``None`` if no scan matches.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def list_scans(
        self,
        model: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List recent scan results, optionally filtered by model name.

        Args:
            model: If provided, only return scans for this model.
            limit: Maximum number of results to return (default 50).

        Returns:
            A list of scan summary dictionaries ordered by timestamp
            descending (most recent first).
        """
        query = (
            "SELECT scan_id, model_name, provider, profile, timestamp, "
            "duration_ms, overall_score, risk_level, total_probes, total_findings "
            "FROM scans"
        )
        params: list[Any] = []

        if model is not None:
            query += " WHERE model_name = ?"
            params.append(model)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_trends(
        self,
        model: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get score trends over time for a specific model.

        Args:
            model: The model name to retrieve trends for.
            limit: Maximum number of data points to return.

        Returns:
            A list of dictionaries with ``scan_id``, ``timestamp``,
            ``overall_score``, ``risk_level``, and ``total_findings``
            ordered chronologically (oldest first).
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT scan_id, timestamp, overall_score, risk_level,
                       total_findings, total_probes
                FROM scans
                WHERE model_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (model, limit),
            ).fetchall()

        # Return in chronological order (oldest first) for trend display
        return [dict(row) for row in reversed(rows)]

    def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan result by its ID.

        Args:
            scan_id: The unique scan identifier to delete.

        Returns:
            ``True`` if a scan was deleted, ``False`` if no matching scan was found.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM scans WHERE scan_id = ?", (scan_id,)
            )
            return cursor.rowcount > 0

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """Convert a database row to a dictionary, parsing the result JSON."""
        data = dict(row)
        raw_json = data.pop("result_json", None)
        if raw_json:
            data["result"] = json.loads(raw_json)
        return data
