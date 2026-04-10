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
    "openai/gpt-4o"
    "openai/gpt-4o-mini"
)

# The four experimental conditions (probes)
CONDITIONS=(
    "jailbreak"               # static single-turn
    "scripted_multi_turn"     # static multi-turn
    "adaptive_single_turn"    # adaptive single-turn
    "adaptive_multi_turn"     # adaptive multi-turn
)

RESULTS_DIR="./results/experiment"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EXPERIMENT_DIR="${RESULTS_DIR}/${TIMESTAMP}"
ATLAS=".venv/bin/atlas"
DRY_RUN=false
MODELS=()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --models)
            IFS=',' read -ra MODELS <<< "$2"
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
            echo "  --models      Comma-separated LiteLLM model strings (default: gpt-4o, gpt-4o-mini)"
            echo "  --results-dir Base output directory (default: ./results/experiment)"
            echo "  --dry-run     Print commands without executing"
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
echo "  Timestamp:  ${TIMESTAMP}"
echo "  Models:     ${MODELS[*]}"
echo "  Conditions: ${CONDITIONS[*]}"
echo "  Output:     ${EXPERIMENT_DIR}"
echo "  All detectors: yes"
echo "=============================================="
echo ""

mkdir -p "${EXPERIMENT_DIR}"

# Save experiment metadata
cat > "${EXPERIMENT_DIR}/experiment_meta.json" <<METAEOF
{
  "timestamp": "${TIMESTAMP}",
  "models": $(printf '%s\n' "${MODELS[@]}" | jq -R . | jq -s .),
  "conditions": $(printf '%s\n' "${CONDITIONS[@]}" | jq -R . | jq -s .),
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

        CMD=(
            "$ATLAS" scan run
            --model "$model"
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
