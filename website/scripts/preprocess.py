"""Pre-process experiment data into lightweight summaries for the frontend.

Reads from:  ../docs/experiment/ (raw experiment data, not deployed)
Produces:
  public/data/summary.json  — aggregated stats (~1.2 MB instead of ~39 MB)
  public/data/findings/     — individual finding files loaded on-demand (~20 KB each)
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
EXPERIMENT_DIR = REPO_ROOT / "docs" / "experiment"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data"
FINDINGS_DIR = OUTPUT_DIR / "findings"
FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Find experiment directories
experiment_dirs = sorted([d for d in EXPERIMENT_DIR.iterdir() if d.is_dir()])
if not experiment_dirs:
    print("ERROR: No experiment directories found in docs/experiment/", file=sys.stderr)
    sys.exit(1)

# Use the latest experiment
exp_dir = experiment_dirs[-1]
meta_path = exp_dir / "experiment_meta.json"
if not meta_path.exists():
    print(f"ERROR: No experiment_meta.json in {exp_dir}", file=sys.stderr)
    sys.exit(1)

meta = json.loads(meta_path.read_text())
print(f"Processing experiment: {exp_dir.name}")

model_summaries = []
probe_summaries: dict[str, dict] = {}
all_findings_index: list[dict] = []
compliance_data: list[dict] = []

# Walk experiment directory structure: model_dir/probe_dir/scan_*.json
for model_dir in sorted(exp_dir.iterdir()):
    if not model_dir.is_dir():
        continue
    for probe_dir in sorted(model_dir.iterdir()):
        if not probe_dir.is_dir():
            continue
        for scan_path in probe_dir.glob("scan_*.json"):
            scan = json.loads(scan_path.read_text())
            model = scan["model_name"]
            model_short = model.split("/")[-1]

            for probe_name, probe_result in scan.get("probe_results", {}).items():
                if probe_name not in probe_summaries:
                    probe_summaries[probe_name] = {
                        "probe_name": probe_name,
                        "total_attempts": 0,
                        "passed": 0,
                        "failed": 0,
                        "models": {},
                    }
                ps = probe_summaries[probe_name]
                ps["total_attempts"] += probe_result["total_attempts"]
                ps["passed"] += probe_result["passed"]
                ps["failed"] += probe_result["failed"]
                ps["models"][model_short] = {
                    "pass_rate": probe_result["pass_rate"],
                    "passed": probe_result["passed"],
                    "failed": probe_result["failed"],
                    "total_attempts": probe_result["total_attempts"],
                }

                for finding in probe_result.get("findings", []):
                    attempt = finding["attempt"]
                    fmeta = attempt.get("metadata", {})
                    fid = finding["id"]

                    # Write full finding to separate file
                    (FINDINGS_DIR / f"{fid}.json").write_text(json.dumps(finding, default=str))

                    # Lightweight index entry
                    all_findings_index.append({
                        "id": fid,
                        "model": model,
                        "model_short": model_short,
                        "probe": attempt.get("probe_name", probe_name),
                        "passed": finding["passed"],
                        "severity": finding.get("severity", ""),
                        "prompt_preview": attempt.get("prompt", "")[:120],
                        "condition": str(fmeta.get("condition", "")),
                        "adaptivity": str(fmeta.get("adaptivity", "")),
                        "interaction_mode": str(fmeta.get("interaction_mode", "")),
                        "num_messages": len(attempt.get("messages", [])),
                        "num_target_calls": attempt.get("num_target_calls", 0),
                        "num_attacker_calls": attempt.get("num_attacker_calls", 0),
                        "cost_usd": attempt.get("cost_usd", 0),
                        "latency_ms": attempt.get("latency_ms", 0),
                        "target_tokens": attempt.get("target_tokens_in", 0) + attempt.get("target_tokens_out", 0),
                        "attacker_tokens": attempt.get("attacker_tokens_in", 0) + attempt.get("attacker_tokens_out", 0),
                        "detector_summary": [
                            {"name": d["detector_name"], "passed": d["passed"], "score": d.get("score", 0)}
                            for d in finding.get("detector_results", [])
                        ],
                    })

            model_summaries.append({
                "model": model,
                "model_short": model_short,
                "scan_id": scan["scan_id"],
                "probe": probe_dir.name,
                "started_at": scan.get("started_at"),
                "completed_at": scan.get("completed_at"),
                "duration_ms": scan.get("duration_ms", 0),
                "total_cost_usd": scan.get("total_cost_usd", 0),
                "total_target_tokens": scan.get("total_target_tokens", 0),
                "total_attacker_tokens": scan.get("total_attacker_tokens", 0),
                "security_score": scan.get("security_score", {}),
                "compliance_assessment": scan.get("compliance_assessment", {}),
                "recommendations": scan.get("recommendations", []),
                "probe_results_summary": {
                    name: {
                        "probe_name": pr["probe_name"],
                        "category": pr.get("category", ""),
                        "total_attempts": pr["total_attempts"],
                        "passed": pr["passed"],
                        "failed": pr["failed"],
                        "pass_rate": pr["pass_rate"],
                    }
                    for name, pr in scan.get("probe_results", {}).items()
                },
            })

            for article in scan.get("compliance_assessment", {}).get("article_details", []):
                compliance_data.append({
                    "model": model,
                    "model_short": model_short,
                    **article,
                })

summary = {
    "experiment": {
        "id": exp_dir.name,
        "timestamp": meta["timestamp"],
        "models": meta["models"],
        "conditions": meta["conditions"],
    },
    "scans": model_summaries,
    "probes": list(probe_summaries.values()),
    "findings_index": all_findings_index,
    "compliance": compliance_data,
}

summary_path = OUTPUT_DIR / "summary.json"
summary_path.write_text(json.dumps(summary, indent=2, default=str))

summary_size = summary_path.stat().st_size
findings_count = len(all_findings_index)
findings_total = sum(f.stat().st_size for f in FINDINGS_DIR.glob("*.json"))

print(f"summary.json: {summary_size / 1024:.1f} KB")
print(f"findings: {findings_count} files, {findings_total / 1024:.1f} KB total")
print(f"Initial page load: ~{summary_size / 1024:.0f} KB (was ~39 MB)")
