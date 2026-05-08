#!/usr/bin/env bash
#
# run_experiment.sh — Run the full 2x2 factorial experiment.
#
# Usage:
#   ./scripts/run_experiment.sh                      # All models, all conditions
#   ./scripts/run_experiment.sh --models "openai/gpt-4o"  # Single model
#   ./scripts/run_experiment.sh --dry-run             # Show what would run
#
# Prerequisites:
#   - OPENAI_API_KEY (or relevant provider keys) set in environment
#   - Python venv with atlas installed: .venv/bin/atlas
#
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Target models to evaluate (override with --models "model1,model2")
DEFAULT_MODELS=(
    "openrouter/openai/gpt-4o-mini"
    "openrouter/openai/gpt-4o"
    "openrouter/anthropic/claude-sonnet-4"
    "openrouter/google/gemini-2.5-flash"
    "openrouter/meta-llama/llama-3.3-70b-instruct"
    "openrouter/deepseek/deepseek-chat-v3-0324"
    "openrouter/qwen/qwen-2.5-72b-instruct"
    "openrouter/mistralai/mistral-large-2411"
)

# Attacker model for adaptive probes (stronger than targets, per PAIR/TAP literature)
ATTACKER_MODEL="openrouter/deepseek/deepseek-r1-0528"

# The six experimental conditions (probes)
CONDITIONS=(
    "jailbreak"                 # static single-turn (DAN/DUDE/STAN templates)
    "scripted_multi_turn"       # static multi-turn
    "adaptive_single_query_st"  # adaptive single-query single-turn (PAIR 1 iter, no refinement)
    "adaptive_single_turn"      # adaptive multi-query single-turn (PAIR up to 5 iterations)
    "adaptive_multi_turn"       # adaptive multi-turn
)

RESULTS_DIR="./results/experiment"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPERIMENT_DIR="${RESULTS_DIR}/${TIMESTAMP}"
RESUME_DIR=""
ATLAS=".venv/bin/atlas"
DRY_RUN=false
MODELS=()
ATTACKER_OVERRIDE=""
CONDITIONS_OVERRIDE=()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --models)
            IFS=',' read -ra MODELS <<< "$2"
            shift 2
            ;;
        --attacker-model)
            ATTACKER_OVERRIDE="$2"
            shift 2
            ;;
        --conditions)
            IFS=',' read -ra CONDITIONS_OVERRIDE <<< "$2"
            shift 2
            ;;
        --resume)
            RESUME_DIR="$2"
            shift 2
            ;;
        --results-dir)
            EXPERIMENT_DIR="$2/${TIMESTAMP}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--models model1,model2] [--results-dir DIR] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --models         Comma-separated LiteLLM model strings"
            echo "  --conditions     Comma-separated condition names (default: all)"
            echo "  --attacker-model Attacker LLM for adaptive probes (default: deepseek-r1)"
            echo "  --resume DIR     Resume a previous experiment run (skip completed scans)"
            echo "  --results-dir    Base output directory (default: ./results/experiment)"
            echo "  --dry-run        Print commands without executing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Use defaults if no models specified
if [[ ${#MODELS[@]} -eq 0 ]]; then
    MODELS=("${DEFAULT_MODELS[@]}")
fi

# Override conditions if specified
if [[ ${#CONDITIONS_OVERRIDE[@]} -gt 0 ]]; then
    CONDITIONS=("${CONDITIONS_OVERRIDE[@]}")
fi

# Resume mode: reuse existing experiment directory
if [[ -n "$RESUME_DIR" ]]; then
    if [[ ! -d "$RESUME_DIR" ]]; then
        echo "ERROR: Resume directory not found: $RESUME_DIR" >&2
        exit 1
    fi
    EXPERIMENT_DIR="$RESUME_DIR"
    echo "RESUMING experiment in: ${EXPERIMENT_DIR}"
fi

# Resolve attacker model
if [[ -z "$ATTACKER_OVERRIDE" ]]; then
    ATTACKER_OVERRIDE="$ATTACKER_MODEL"
fi

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

if [[ ! -f "$ATLAS" ]]; then
    echo "ERROR: Atlas CLI not found at $ATLAS" >&2
    echo "  Run: pip install -e . (inside .venv)" >&2
    exit 1
fi

echo "=============================================="
echo "  ATLAS 2x2 Factorial Experiment"
echo "=============================================="
echo "  Timestamp:      ${TIMESTAMP}"
echo "  Models:         ${MODELS[*]}"
echo "  Attacker:       ${ATTACKER_OVERRIDE}"
echo "  Conditions:     ${CONDITIONS[*]}"
echo "  Output:         ${EXPERIMENT_DIR}"
echo "  All detectors:  yes"
echo "=============================================="
echo ""

mkdir -p "${EXPERIMENT_DIR}"

# Save experiment metadata
cat > "${EXPERIMENT_DIR}/experiment_meta.json" <<METAEOF
{
  "timestamp": "${TIMESTAMP}",
  "models": $(printf '%s\n' "${MODELS[@]}" | jq -R . | jq -s .),
  "conditions": $(printf '%s\n' "${CONDITIONS[@]}" | jq -R . | jq -s .),
  "attacker_model": "${ATTACKER_OVERRIDE}",
  "all_detectors": true
}
METAEOF

# ---------------------------------------------------------------------------
# Run scans
# ---------------------------------------------------------------------------

TOTAL_RUNS=$(( ${#MODELS[@]} * ${#CONDITIONS[@]} ))
RUN_NUM=0
FAILED=0

for model in "${MODELS[@]}"; do
    model_slug=$(echo "$model" | tr '/' '_' | tr '.' '_')
    model_dir="${EXPERIMENT_DIR}/${model_slug}"
    mkdir -p "${model_dir}"

    echo ""
    echo ">>> Model: ${model}"
    echo "-------------------------------------------"

    for condition in "${CONDITIONS[@]}"; do
        RUN_NUM=$((RUN_NUM + 1))
        run_dir="${model_dir}/${condition}"
        mkdir -p "${run_dir}"

        echo "[${RUN_NUM}/${TOTAL_RUNS}] ${model} / ${condition}"

        # Resume: skip if scan result already exists
        if ls "${run_dir}"/scan_*.json 1>/dev/null 2>&1; then
            echo "  SKIP (already completed)"
            continue
        fi

        CMD=(
            "$ATLAS" scan run
            --model "$model"
            --attacker-model "$ATTACKER_OVERRIDE"
            --profile experiment
            --probes "$condition"
            --detectors keyword,refusal
            --all-detectors
            --output "$run_dir"
            --format json
            --ci
            --no-checkpoint
        )

        if $DRY_RUN; then
            echo "  [dry-run] ${CMD[*]}"
        else
            "${CMD[@]}" > "${run_dir}/stdout.log" 2>&1
            exit_code=$?
            if [[ $exit_code -eq 0 ]]; then
                echo "  DONE (results in ${run_dir})"
            elif [[ $exit_code -eq 1 ]]; then
                # exit 1 = threshold not met (expected for experiments)
                echo "  DONE (below threshold, results in ${run_dir})"
            else
                # exit 2+ = actual error
                echo "  FAILED (exit=$exit_code, see ${run_dir}/stdout.log)" >&2
                FAILED=$((FAILED + 1))
            fi
        fi
    done
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "=============================================="
echo "  Experiment Complete"
echo "=============================================="
echo "  Total runs: ${TOTAL_RUNS}"
echo "  Failed:     ${FAILED}"
echo "  Results:    ${EXPERIMENT_DIR}"
echo "=============================================="

if [[ $FAILED -gt 0 ]]; then
    echo ""
    echo "WARNING: ${FAILED} run(s) failed. Check stdout.log in each run directory."
    exit 1
fi
