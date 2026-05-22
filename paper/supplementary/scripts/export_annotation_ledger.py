#!/usr/bin/env python3
"""Export the final annotation ledger for all findings from the ATLAS DB backup.

Parses the PostgreSQL COPY dump and produces a CSV with full annotation
provenance for every finding in experiment 20260505_003630.

Columns:
  finding_id, model, intent_id, condition, raw_detector_label,
  annotator_1_label, annotator_1_author, annotator_2_label, annotator_2_author,
  adjudication_status, final_human_label, severity, disagreement_flag,
  provider_filtered

Usage:
    python scripts/export_annotation_ledger.py
    python scripts/export_annotation_ledger.py --backup backups/atlas_db_20260511_165938.sql.gz
    python scripts/export_annotation_ledger.py --output docs/v6/artifacts/annotation_ledger.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

EXPERIMENT_ID = "20260505_003630"
DEFAULT_BACKUP = "backups/atlas_db_20260514_123855.sql.gz"
DEFAULT_OUTPUT = "docs/v6/artifacts/annotation_ledger.csv"


def _pg_unescape(s: str) -> str:
    """Unescape PostgreSQL COPY text format (\\n -> newline, \\t -> tab, \\\\ -> backslash)."""
    result: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                result.append("\n")
                i += 2
            elif nxt == "t":
                result.append("\t")
                i += 2
            elif nxt == "\\":
                result.append("\\")
                i += 2
            else:
                result.append(s[i])
                i += 1
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


def _parse_copy_block(lines_iter, header_line: str) -> tuple[list[str], list[list[str]]]:
    """Parse a COPY ... FROM stdin block, returning column names and rows."""
    # Extract column names from: COPY public.tablename (col1, col2, ...) FROM stdin;
    paren_start = header_line.index("(")
    paren_end = header_line.index(")")
    cols = [c.strip().strip('"') for c in header_line[paren_start + 1 : paren_end].split(",")]

    rows: list[list[str]] = []
    for line in lines_iter:
        if line.startswith("\\."):
            break
        rows.append(line.rstrip("\n").split("\t"))
    return cols, rows


def _parse_dump(dump_path: Path) -> dict:
    """Parse all relevant tables from the dump."""
    tables: dict[str, tuple[list[str], list[list[str]]]] = {}
    target_tables = {"findings", "annotations", "review_votes", "users"}

    opener = gzip.open if dump_path.suffix == ".gz" else open
    with opener(dump_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("COPY public."):
                table_name = line.split("(")[0].replace("COPY public.", "").strip()
                if table_name in target_tables:
                    cols, rows = _parse_copy_block(f, line)
                    tables[table_name] = (cols, rows)

    return tables


def _majority_vote(detector_summary: list[dict]) -> str:
    """Compute majority vote from detector_summary: 'unsafe' if majority say failed."""
    if not detector_summary:
        return "unknown"
    fail_count = sum(1 for d in detector_summary if not d.get("passed", True))
    return "unsafe" if fail_count > len(detector_summary) / 2 else "safe"


def _extract_intent_id(detail_json_str: str) -> str:
    """Extract intent_id from the detail_json field.

    The raw value comes from PostgreSQL COPY format and must be unescaped
    before JSON parsing (\\n -> newline, etc.).
    """
    try:
        unescaped = _pg_unescape(detail_json_str)
        detail = json.loads(unescaped)
        # Try nested attempt.metadata.intent_id
        if isinstance(detail, dict):
            attempt = detail.get("attempt", detail)
            metadata = attempt.get("metadata", {})
            return metadata.get("intent_id", "")
    except (json.JSONDecodeError, TypeError):
        pass
    return ""


def main():
    parser = argparse.ArgumentParser(description="Export ATLAS annotation ledger")
    parser.add_argument("--backup", default=DEFAULT_BACKUP, help="Path to .sql.gz backup")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path")
    parser.add_argument("--experiment", default=EXPERIMENT_ID, help="Experiment ID to filter")
    args = parser.parse_args()

    dump_path = Path(args.backup)
    if not dump_path.exists():
        print(f"Error: backup not found at {dump_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing dump: {dump_path}")
    tables = _parse_dump(dump_path)

    # --- Build user map: user_id -> username ---
    user_cols, user_rows = tables["users"]
    uid_idx = user_cols.index("id")
    uname_idx = user_cols.index("username")
    user_map = {row[uid_idx]: row[uname_idx] for row in user_rows}

    # --- Build findings map (filtered by experiment) ---
    f_cols, f_rows = tables["findings"]
    fi = {c: i for i, c in enumerate(f_cols)}

    findings: dict[str, dict] = {}
    for row in f_rows:
        if row[fi["experiment_id"]] != args.experiment:
            continue

        fid = row[fi["id"]]
        detail_json_str = row[fi["detail_json"]]
        intent_id = _extract_intent_id(detail_json_str)

        # Parse detector_summary_json
        try:
            detector_summary = json.loads(row[fi["detector_summary_json"]])
        except (json.JSONDecodeError, TypeError):
            detector_summary = []

        num_target_calls = int(row[fi["num_target_calls"]])
        target_tokens = int(row[fi["target_tokens"]])

        # Detect provider-filtered: zero target calls + zero tokens
        provider_filtered = num_target_calls == 0 and target_tokens == 0

        # Skip un-aggregated BoK variants (keep only the aggregated finding)
        # Aggregated BoK findings have bok_aggregated=true in metadata
        probe = row[fi["probe"]]
        if probe == "best_of_k_st":
            try:
                detail = json.loads(detail_json_str)
                attempt = detail.get("attempt", detail)
                metadata = attempt.get("metadata", {})
                if not metadata.get("bok_aggregated", False):
                    continue  # skip raw variant, keep only aggregated
            except (json.JSONDecodeError, TypeError):
                pass

        findings[fid] = {
            "finding_id": fid,
            "model": row[fi["model_short"]],
            "intent_id": intent_id,
            "condition": probe,
            "raw_detector_label": "safe" if row[fi["passed"]] == "t" else "unsafe",
            "severity": row[fi["severity"]],
            "passed_raw": row[fi["passed"]] == "t",
            "provider_filtered": provider_filtered,
        }

    print(f"Findings for {args.experiment}: {len(findings)}")

    # --- Build review_votes map: finding_id -> list of (status, username) ---
    # Review votes are the primary human annotation source for this experiment.
    # Each vote is one annotator's label for a finding.
    rv_cols, rv_rows = tables["review_votes"]
    ri = {c: i for i, c in enumerate(rv_cols)}
    reviews_by_finding: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in rv_rows:
        fid = row[ri["finding_id"]]
        if fid in findings:
            user_id = row[ri["user_id"]]
            username = user_map.get(user_id, f"user_{user_id}")
            reviews_by_finding[fid].append((row[ri["status"]], username))

    # --- Assemble ledger rows ---
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "finding_id", "model", "intent_id", "condition",
        "raw_detector_label",
        "annotator_1_label", "annotator_1_author",
        "annotator_2_label", "annotator_2_author",
        "adjudication_status", "final_human_label",
        "severity", "disagreement_flag", "provider_filtered",
    ]

    rows_out = []
    for fid, f in sorted(findings.items(), key=lambda x: (x[1]["condition"], x[1]["model"], x[1]["intent_id"])):
        reviews = reviews_by_finding.get(fid, [])

        # Annotator labels from review_votes (up to 2 reviewers)
        ann1_label = reviews[0][0] if len(reviews) > 0 else ""
        ann1_author = reviews[0][1] if len(reviews) > 0 else ""
        ann2_label = reviews[1][0] if len(reviews) > 1 else ""
        ann2_author = reviews[1][1] if len(reviews) > 1 else ""

        # Adjudication status
        if len(reviews) >= 2:
            if reviews[0][0] == reviews[1][0]:
                adj_status = "agreed"
            else:
                adj_status = "adjudicated"
        elif len(reviews) == 1:
            adj_status = "single_review"
        else:
            adj_status = ""

        # Final human label: last reviewer's verdict is authoritative.
        if reviews:
            final_label = reviews[-1][0]
        else:
            final_label = "safe" if f["passed_raw"] else "unsafe"

        # Disagreement flag
        disagreement = False
        if ann1_label and ann2_label:
            disagreement = ann1_label != ann2_label

        rows_out.append({
            "finding_id": fid,
            "model": f["model"],
            "intent_id": f["intent_id"],
            "condition": f["condition"],
            "raw_detector_label": f["raw_detector_label"],
            "annotator_1_label": ann1_label,
            "annotator_1_author": ann1_author,
            "annotator_2_label": ann2_label,
            "annotator_2_author": ann2_author,
            "adjudication_status": adj_status,
            "final_human_label": final_label,
            "severity": f["severity"],
            "disagreement_flag": disagreement,
            "provider_filtered": f["provider_filtered"],
        })

    with open(output_path, "w", newline="") as csvf:
        writer = csv.DictWriter(csvf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Exported {len(rows_out)} rows to {output_path}")

    # Summary stats
    n_disagreements = sum(1 for r in rows_out if r["disagreement_flag"])
    n_provider_filtered = sum(1 for r in rows_out if r["provider_filtered"])
    from collections import Counter
    label_counts = Counter(r["final_human_label"] for r in rows_out)
    print(f"  Labels: {dict(label_counts)}")
    print(f"  Disagreements: {n_disagreements} ({n_disagreements/max(1,len(rows_out))*100:.1f}%)")
    print(f"  Provider-filtered: {n_provider_filtered}")


if __name__ == "__main__":
    main()
