# ATLAS

Automated Testing for LLM Application Security.

## Installation

```bash
pip install atlas-llm
```

## Configuration

1. Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

2. Edit `.env` with your provider keys:

```dotenv
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Keys referenced in `atlas.yaml` as `${ENV_VAR}` are resolved automatically from `.env`.

## Running Scans

### Basic scan

```bash
atlas scan run --model openai/gpt-4o
```

### Choose a profile

Profiles control which probes and detectors are used:

| Profile      | Description                                  |
|--------------|----------------------------------------------|
| `quick`      | Smoke test — jailbreak + prompt injection     |
| `standard`   | Core vulnerability categories (default)       |
| `full`       | All probes with full compliance mapping       |
| `multi-turn` | Multi-turn and adaptive attack probes         |
| `ci`         | Fast, CI/CD-optimized subset                  |

```bash
atlas scan run --model openai/gpt-4o --profile full
```

### Select specific probes or detectors

```bash
atlas scan run --model openai/gpt-4o --probes prompt_injection,extraction --detectors keyword,refusal
```

### Output options

```bash
# Custom output directory and format
atlas scan run --model openai/gpt-4o --output ./my-results --format html

# Generate SARIF report (for GitHub Code Scanning, etc.)
atlas scan run --model openai/gpt-4o --sarif results/report.sarif

# Generate JUnit XML report
atlas scan run --model openai/gpt-4o --junit results/report.xml
```

### CI mode

Exit code `0` on pass, `1` on fail, `2` on error. Minimal, machine-readable output.

```bash
atlas scan run --model openai/gpt-4o --ci --threshold 90
```

### Compare models

Run the same probes against multiple models side-by-side:

```bash
atlas scan compare --models openai/gpt-4o,anthropic/claude-sonnet-4-20250514 --profile standard
```

### List available probes and detectors

```bash
atlas scan list-probes
atlas scan list-detectors
```

## Other Commands

```bash
atlas config show          # Show current configuration
atlas report generate      # Generate reports from past scans
atlas history list         # View scan history
atlas interactive          # Start an interactive REPL session
```

## Global Options

```bash
atlas --verbose ...        # Debug-level logging
atlas --quiet ...          # Errors only
atlas --config my.yaml ... # Custom config file
```
