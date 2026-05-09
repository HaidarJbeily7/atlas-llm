#!/usr/bin/env python3
"""Backfill zero-cost findings in experiment scan files.

Three target models routed through OpenRouter are missing from both
litellm's pricing database and the static PRICING fallback table in
``atlas.core.token_tracking``.  As a result every finding for these
models in static/scripted conditions (and the *target* portion of
adaptive conditions) was logged with ``cost_usd: 0.0``.

Affected models and their OpenRouter per-token pricing:

  mistralai/mistral-large-2411     $0.002 / 1K in,  $0.006 / 1K out
  meta-llama/llama-3.3-70b-instruct  $0.00023 / 1K in, $0.0004 / 1K out
  qwen/qwen-2.5-72b-instruct      $0.00035 / 1K in, $0.0004 / 1K out

This script:
  1. Scans all ``scan_*.json`` files under the given experiment directory.
  2. For every finding whose ``cost_usd`` is 0.0 *and* whose target tokens
     are > 0, recomputes the cost from the token counts and writes it back.
  3. Prints a summary of changes per file.

Usage:
    python scripts/backfill_costs.py docs/experiment/20260505_003630
    python scripts/backfill_costs.py docs/experiment/20260505_003630 --dry-run
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# OpenRouter pricing: model_id substring -> (input $/1K, output $/1K)
# These are the models missing from litellm's cost map.
# Prices sourced from OpenRouter pricing page (as of 2026-05).
PRICING: dict[str, tuple[float, float]] = {
    "mistralai/mistral-large-2411": (0.002, 0.006),
    "meta-llama/llama-3.3-70b-instruct": (0.00023, 0.0004),
    "qwen/qwen-2.5-72b-instruct": (0.00035, 0.0004),
}


def compute_cost(model_id: str, tokens_in: int, tokens_out: int) -> float | None:
    """Return USD cost or None if model is not in our pricing table."""
    for key, (in_price, out_price) in PRICING.items():
        if key in model_id:
            return (tokens_in * in_price / 1000) + (tokens_out * out_price / 1000)
    return None


def backfill_file(path: str, dry_run: bool = False) -> tuple[int, int]:
    """Backfill zero-cost findings in a single scan JSON file.

    Returns (total_findings, patched_count).
    """
    with open(path) as f:
        data = json.load(f)

    patched = 0
    total = 0

    for probe_data in data.get("probe_results", {}).values():
        for finding in probe_data.get("findings", []):
            attempt = finding.get("attempt", {})
            total += 1

            target_in = attempt.get("target_tokens_in", 0)
            target_out = attempt.get("target_tokens_out", 0)
            model_id = attempt.get("response_metadata", {}).get("model_id", "")

            if target_in + target_out == 0:
                continue

            target_cost = compute_cost(model_id, target_in, target_out)
            if target_cost is None:
                continue

            # For adaptive conditions the logged cost already includes
            # attacker cost but is missing the target portion.  For
            # static/scripted conditions the cost is simply 0.0.
            old_cost = attempt.get("cost_usd", 0.0)
            new_cost = round(old_cost + target_cost, 8)
            if new_cost == old_cost:
                continue

            attempt["cost_usd"] = new_cost
            patched += 1

    # Recompute scan-level total_cost_usd from findings
    if patched > 0:
        data["total_cost_usd"] = round(
            sum(
                f["attempt"].get("cost_usd", 0.0)
                for pd in data.get("probe_results", {}).values()
                for f in pd.get("findings", [])
            ),
            8,
        )
        if not dry_run:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")

    return total, patched


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill zero-cost findings in experiment scan files.")
    parser.add_argument("experiment_dir", help="Path to experiment directory (e.g. docs/experiment/20260505_003630)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")
    args = parser.parse_args()

    if not os.path.isdir(args.experiment_dir):
        print(f"Error: {args.experiment_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    scan_files = sorted(glob.glob(os.path.join(args.experiment_dir, "**", "scan_*.json"), recursive=True))
    if not scan_files:
        print(f"No scan_*.json files found under {args.experiment_dir}", file=sys.stderr)
        sys.exit(1)

    total_patched = 0
    total_findings = 0

    print(f"{'File':<80s} {'Findings':>8s} {'Patched':>8s}")
    print("-" * 100)

    for path in scan_files:
        rel = os.path.relpath(path, args.experiment_dir)
        findings, patched = backfill_file(path, dry_run=args.dry_run)
        total_findings += findings
        total_patched += patched
        if patched > 0:
            print(f"{rel:<80s} {findings:>8d} {patched:>8d}")

    print("-" * 100)
    mode = " (DRY RUN)" if args.dry_run else ""
    print(f"Total: {total_patched}/{total_findings} findings patched{mode}")


if __name__ == "__main__":
    main()
