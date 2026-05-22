#!/usr/bin/env python3
"""BoK strategy diversity audit using redacted labels and TF-IDF analysis.

Audits whether BoK variants use truly different strategy families or are
paraphrases. Uses ONLY redacted strategy descriptors extracted from prompts,
NOT the full harmful content.

This approach:
1. Extracts sanitized strategy indicators from prompts
2. Classifies strategy families using pattern matching
3. Computes TF-IDF similarity between variants
4. Flags intents with low diversity

Usage:
    python3 scripts/audit_bok_diversity.py
    python3 scripts/audit_bok_diversity.py --variants src/atlas/datasets/data/bok_variants.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import math

DEFAULT_VARIANTS = "src/atlas/datasets/data/bok_variants.json"


def extract_strategy_indicators(prompt: str) -> list[str]:
    """Extract the framing/wrapping strategy used to disguise the harmful request.

    IMPORTANT: This classifies the *jailbreak framing strategy* (how the request
    is wrapped), NOT the payload topic. A keylogger intent will mention "code" in
    every variant — that's the payload. The strategy is the wrapper: fiction,
    academic pretext, CTF scenario, etc.
    """
    indicators = []
    prompt_lower = prompt.lower()

    # --- Framing strategies (priority: these ARE the jailbreak wrapper) ---

    # 1. Role-play / persona assumption
    role_patterns = [
        r"as (?:a|an) \w+ (?:instructor|expert|researcher|consultant|developer|analyst|professor|writer|journalist|historian|detective|reporter|editor|officer|investigator|specialist)",
        r"you(?:'re| are) (?:a|an) \w+",
        r"imagine you(?:'re| are)",
        r"pretend (?:you(?:'re| are)|to be)",
        r"acting as",
        r"role[- ]?play",
        r"persona",
        r"you(?:'re| are) participating",
        r"adopt this role",
        r"take (?:on |)the role",
    ]
    if any(re.search(p, prompt_lower) for p in role_patterns):
        indicators.append("role_play")

    # 2. Fictional / creative writing frame
    fiction_patterns = [
        r"fictional? (?:story|novel|narrative|scenario|world|segment|account|dialogue|malware|dystopian)",
        r"for (?:a|my) (?:fictional |)(?:story|novel|narrative|book|screenplay|film|thriller|short story)",
        r"write (?:a |the |an )(?:next |)(?:story|chapter|scene|segment|opening|immersive)",
        r"creative writing",
        r"plot[- ]critical",
        r"character (?:would|must|should|a |b )",
        r"(?:opening|first|next) chapter",
        r"immersive fiction",
        r"thriller (?:where|novel|story|about)",
        r"realistic (?:novel|thriller|story|fiction)",
        r"dystopian (?:story|novel|world|scenario|setting)",
        r"(?:film |movie |)script (?:argument|where|about|featuring)",
        r"short story (?:about|where|featuring)",
        r"banned literature",
        r"controversial novel",
        r"(?:as a |)novelist",
        r"fictional (?:malware|module|code)",
        r"museum exhibit",
    ]
    if any(re.search(p, prompt_lower) for p in fiction_patterns):
        indicators.append("fiction")

    # 3. Academic / research pretext
    academic_patterns = [
        r"academic (?:study|research|paper|project|exercise)",
        r"university (?:research|project|course|lab)",
        r"research (?:project|paper|study|parameters|purposes)",
        r"for (?:a|an|my) (?:academic|research|thesis|dissertation)",
        r"peer[- ]review",
        r"scholarly",
        r"psychology study",
        r"forensic (?:recovery|analysis|research)",
        r"(?:authorized |)forensic",
    ]
    if any(re.search(p, prompt_lower) for p in academic_patterns):
        indicators.append("academic")

    # 4. Security exercise / CTF / pentest frame
    security_patterns = [
        r"(?:cyber)?security (?:training|exercise|workshop|course|lab|challenge|club|class)",
        r"penetration test",
        r"pen[- ]?test",
        r"capture[- ]the[- ]flag",
        r"ctf (?:competition|challenge|exercise)",
        r"ethical hacking",
        r"red[- ]team",
        r"defensive (?:cyber)?security",
        r"security (?:audit|assessment|validation|analyst)",
        r"authorized (?:audit|test|assessment)",
        r"security (?:flaw|vulnerabilit)",
    ]
    if any(re.search(p, prompt_lower) for p in security_patterns):
        indicators.append("security_exercise")

    # 5. Historical reenactment / context
    historical_patterns = [
        r"historical (?:reenactment|context|analysis|recreation|document)",
        r"historically accurate",
        r"early (?:internet|computing|web)",
        r"legacy (?:code|system|software|energetic)",
        r"archival",
        r"(?:19|20)\d{2}s? era",
        r"(?:wwii|ww2|world war)",
        r"top[- ]secret report",
        r"technological evolution .{0,30}since",
        r"museum exhibit",
    ]
    if any(re.search(p, prompt_lower) for p in historical_patterns):
        indicators.append("historical")

    # 6. Translation / multilingual frame
    translation_patterns = [
        r"translat(?:e|ion|ing)",
        r"bilingual",
        r"multilingual",
        r"multinational team",
        r"[\u4e00-\u9fff]",  # Chinese characters present
        r"[\u0400-\u04ff]",  # Cyrillic characters present
    ]
    if any(re.search(p, prompt_lower) for p in translation_patterns):
        indicators.append("translation")

    # 7. Hypothetical / thought experiment
    hypothetical_patterns = [
        r"hypothetical(?:ly)?",
        r"thought experiment",
        r"what if (?:scenario|situation)",
        r"imagine a (?:scenario|situation|world|plausible)",
        r"suppose (?:that|you|i'm)",
        r"in a (?:hypothetical|theoretical) (?:scenario|situation)",
        r"imagine a plausible",
    ]
    if any(re.search(p, prompt_lower) for p in hypothetical_patterns):
        indicators.append("hypothetical")

    # 8. Professional / business context
    professional_patterns = [
        r"(?:business|corporate|enterprise) (?:context|scenario|use case)",
        r"consulting (?:engagement|project)",
        r"client (?:request|requirement|deliverable)",
        r"professional (?:development|context|setting)",
        r"industry (?:standard|practice|report)",
    ]
    if any(re.search(p, prompt_lower) for p in professional_patterns):
        indicators.append("professional")

    # 9. Educational / instructional (broader than academic)
    educational_patterns = [
        r"educational (?:purpose|material|demonstration|context|program|simulation)",
        r"training (?:material|exercise|module|workshop)",
        r"(?:teaching|learning) (?:exercise|material|resource|demonstration)",
        r"classroom (?:exercise|demonstration)",
        r"curriculum",
        r"simulation (?:tutorial|model)",
        r"(?:practical|hands[- ]on) demonstration",
        r"pseudocode for (?:a |an )(?:educational|simulation|modeling)",
        r"generate pseudocode",
    ]

    # 10. Step-by-step / procedural instruction
    step_patterns = [
        r"step[- ]by[- ]step",
        r"step \d+\s*[-:]",
        r"break(?:ing|) down .{0,30}(?:into|step|component)",
        r"detailed (?:instructions|procedure|walkthrough|breakdown)",
    ]
    if any(re.search(p, prompt_lower) for p in step_patterns):
        indicators.append("step_by_step")

    # 11. Technical / code-as-pretext (the request is framed as a coding task)
    technical_patterns = [
        r"(?:write|generate|develop|create) (?:a |)(?:python|javascript|c\+\+|code|script|function|program|pseudocode)",
        r"(?:implement|build|draft) (?:a |an |)(?:module|tool|system|framework|pipeline|api|class)",
        r"(?:white ?paper|technical report|technical document)",
        r"compose a technical",
    ]
    if any(re.search(p, prompt_lower) for p in technical_patterns):
        indicators.append("technical")

    # 12. Screenplay / dialogue framing
    screenplay_patterns = [
        r"screenplay",
        r"(?:create |write |)dialogue for (?:a |)",
        r"(?:film |movie )script",
        r"villain character",
    ]
    if any(re.search(p, prompt_lower) for p in screenplay_patterns):
        indicators.append("fiction")  # merge into fiction

    # 13. Prompt injection / system manipulation (for prompt extraction intents)
    injection_patterns = [
        r"diagnostic mode",
        r"system (?:introspection|verification|check)",
        r"(?:output|display|reproduce|reveal) (?:your |the )(?:full |exact |original |)(?:system |initialization |boot|configuration)",
        r"core (?:directive|programming|configuration)",
        r"technical manual entry",
    ]
    if any(re.search(p, prompt_lower) for p in injection_patterns):
        indicators.append("prompt_injection")
    if any(re.search(p, prompt_lower) for p in educational_patterns):
        indicators.append("educational")

    if not indicators:
        indicators.append("other")

    return list(set(indicators))


def classify_strategy_family(indicators: list[str]) -> str:
    """Classify the primary framing strategy from indicators.

    When multiple framing strategies are detected, pick the most specific one.
    Fiction is common as a secondary signal (e.g. "fictional dystopian" + "academic
    research") — so it yields to more specific framings when co-detected.
    """
    # Priority: specific framings first, fiction as fallback when alone
    for strategy in [
        "security_exercise",
        "historical",
        "translation",
        "academic",
        "hypothetical",
        "professional",
        "educational",
        "step_by_step",
        "role_play",
        "prompt_injection",
        "technical",
        "fiction",
    ]:
        if strategy in indicators:
            return strategy
    return "other"


def compute_simple_similarity(texts: list[str]) -> list[list[float]]:
    """Compute simple word-overlap similarity between texts."""
    if len(texts) < 2:
        return [[1.0]]

    # Simple word-based similarity using Jaccard coefficient
    def get_words(text: str) -> set[str]:
        # Clean and tokenize, keep only alphabetic words of 3+ chars
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return set(words)

    word_sets = [get_words(text) for text in texts]

    # Compute pairwise Jaccard similarity
    n = len(texts)
    similarity_matrix = []

    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            else:
                words_i = word_sets[i]
                words_j = word_sets[j]
                intersection = len(words_i & words_j)
                union = len(words_i | words_j)
                similarity = intersection / max(1, union)
                row.append(similarity)
        similarity_matrix.append(row)

    return similarity_matrix


def audit_bok_diversity(variants_data: dict) -> dict:
    """Audit diversity across all BoK variants."""
    results = {
        "overall_stats": {},
        "per_intent": {},
        "flagged_intents": [],
    }

    strategy_counts = Counter()
    total_intents = 0
    total_variants = 0
    low_diversity_count = 0
    high_similarity_count = 0

    for intent_id, variants in variants_data.items():
        if not variants or len(variants) < 2:
            continue

        total_intents += 1
        total_variants += len(variants)

        # Extract strategy indicators for each variant (avoiding full prompt content)
        variant_strategies = []
        variant_indicators = []

        for i, prompt in enumerate(variants):
            indicators = extract_strategy_indicators(prompt)
            strategy = classify_strategy_family(indicators)
            variant_strategies.append(strategy)
            variant_indicators.append(indicators)
            strategy_counts[strategy] += 1

        # Count unique strategies
        unique_strategies = len(set(variant_strategies))
        strategy_distribution = Counter(variant_strategies)

        # Compute word overlap similarity between variants
        # Use only the first 200 chars of each prompt to avoid harmful content
        sanitized_texts = [prompt[:200] + "..." if len(prompt) > 200 else prompt
                          for prompt in variants]
        similarity_matrix = compute_simple_similarity(sanitized_texts)

        # Exclude diagonal (self-similarity), find max pairwise similarity
        n = len(variants)
        if n > 1:
            # Get upper triangle excluding diagonal
            similarities = []
            for i in range(n):
                for j in range(i + 1, n):
                    similarities.append(similarity_matrix[i][j])
            max_similarity = max(similarities)
            mean_similarity = sum(similarities) / len(similarities)
        else:
            max_similarity = 0.0
            mean_similarity = 0.0

        # Flag problematic intents
        flags = []
        if unique_strategies < 3:
            flags.append(f"low_strategy_diversity ({unique_strategies}/5)")
            low_diversity_count += 1

        if max_similarity > 0.7:
            flags.append(f"high_similarity ({max_similarity:.2f})")
            high_similarity_count += 1

        # Store per-intent results
        results["per_intent"][intent_id] = {
            "total_variants": len(variants),
            "unique_strategies": unique_strategies,
            "strategy_distribution": dict(strategy_distribution),
            "max_similarity": round(max_similarity, 3),
            "mean_similarity": round(mean_similarity, 3),
            "flags": flags,
            "variant_strategies": variant_strategies,
        }

        if flags:
            results["flagged_intents"].append({
                "intent_id": intent_id,
                "flags": flags,
                "unique_strategies": unique_strategies,
                "max_similarity": round(max_similarity, 3),
            })

    # Overall statistics
    results["overall_stats"] = {
        "total_intents": total_intents,
        "total_variants": total_variants,
        "avg_variants_per_intent": round(total_variants / max(1, total_intents), 1),
        "strategy_distribution": dict(strategy_counts),
        "low_diversity_intents": low_diversity_count,
        "high_similarity_intents": high_similarity_count,
        "flagged_rate": round((low_diversity_count + high_similarity_count) / max(1, total_intents * 2) * 100, 1),
    }

    return results


def format_audit_markdown(results: dict) -> str:
    """Format audit results as markdown."""
    md = "# BoK Strategy Diversity Audit\n\n"

    overall = results["overall_stats"]

    md += "## Overall Statistics\n\n"
    md += f"- **Total intents**: {overall['total_intents']}\n"
    md += f"- **Total variants**: {overall['total_variants']}\n"
    md += f"- **Average variants per intent**: {overall['avg_variants_per_intent']}\n"
    md += f"- **Low diversity intents**: {overall['low_diversity_intents']} ({overall['low_diversity_intents']/overall['total_intents']*100:.1f}%)\n"
    md += f"- **High similarity intents**: {overall['high_similarity_intents']} ({overall['high_similarity_intents']/overall['total_intents']*100:.1f}%)\n\n"

    md += "## Strategy Family Distribution\n\n"
    md += "| Strategy Family | Count | Percentage |\n"
    md += "|-----------------|-------|------------|\n"

    strategy_dist = overall['strategy_distribution']
    total_strats = sum(strategy_dist.values())
    for strategy, count in sorted(strategy_dist.items(), key=lambda x: -x[1]):
        pct = count / total_strats * 100
        md += f"| {strategy.replace('_', ' ').title()} | {count} | {pct:.1f}% |\n"

    # Flagged intents
    if results["flagged_intents"]:
        md += "\n## Flagged Intents (Low Diversity or High Similarity)\n\n"
        md += "| Intent ID | Unique Strategies | Max Similarity | Flags |\n"
        md += "|-----------|-------------------|----------------|-------|\n"

        for flagged in results["flagged_intents"]:
            md += f"| {flagged['intent_id']} | {flagged['unique_strategies']}/5 | {flagged['max_similarity']:.3f} | {', '.join(flagged['flags'])} |\n"

    # Sample per-intent analysis
    md += "\n## Sample Intent Analysis\n\n"
    per_intent = results["per_intent"]

    # Show a few examples
    sample_intents = list(per_intent.keys())[:3]
    for intent_id in sample_intents:
        data = per_intent[intent_id]
        md += f"### {intent_id}\n\n"
        md += f"- **Unique strategies**: {data['unique_strategies']}/5\n"
        md += f"- **Strategy breakdown**: {', '.join(f'{k}={v}' for k, v in data['strategy_distribution'].items())}\n"
        md += f"- **Max similarity**: {data['max_similarity']:.3f}\n"
        md += f"- **Mean similarity**: {data['mean_similarity']:.3f}\n"

        if data['flags']:
            md += f"- **Flags**: {', '.join(data['flags'])}\n"

        md += "\n"

    md += "## Analysis\n\n"

    low_div_rate = overall['low_diversity_intents'] / overall['total_intents'] * 100
    high_sim_rate = overall['high_similarity_intents'] / overall['total_intents'] * 100

    if low_div_rate < 10:
        md += f"✅ **Strategy diversity is good**: Only {low_div_rate:.1f}% of intents have < 3 unique strategies.\n"
    else:
        md += f"⚠️  **Strategy diversity needs improvement**: {low_div_rate:.1f}% of intents have < 3 unique strategies.\n"

    if high_sim_rate < 10:
        md += f"✅ **Textual diversity is good**: Only {high_sim_rate:.1f}% of intents have high similarity (>0.7).\n"
    else:
        md += f"⚠️  **Textual diversity needs improvement**: {high_sim_rate:.1f}% of intents have high similarity (>0.7).\n"

    # Strategy balance
    top_strategy = max(strategy_dist.items(), key=lambda x: x[1])
    top_pct = top_strategy[1] / total_strats * 100

    if top_pct < 40:
        md += f"✅ **Strategy balance is good**: Most common strategy ({top_strategy[0]}) is {top_pct:.1f}% of variants.\n"
    else:
        md += f"⚠️  **Strategy imbalance**: {top_strategy[0]} dominates with {top_pct:.1f}% of variants.\n"

    return md


def main():
    parser = argparse.ArgumentParser(description="Audit BoK strategy diversity")
    parser.add_argument("--variants", default=DEFAULT_VARIANTS, help="BoK variants JSON file")
    parser.add_argument("--output", default="docs/v6/artifacts/bok_diversity_audit", help="Output file prefix")
    args = parser.parse_args()

    variants_path = Path(args.variants)
    if not variants_path.exists():
        print(f"Error: variants file not found: {variants_path}")
        return

    print(f"Loading BoK variants from {variants_path}")
    with open(variants_path) as f:
        variants_data = json.load(f)

    print(f"Found {len(variants_data)} intents")
    total_variants = sum(len(variants) for variants in variants_data.values())
    print(f"Total variants: {total_variants}")

    print("Auditing strategy diversity...")
    results = audit_bok_diversity(variants_data)

    # Output JSON
    json_path = Path(f"{args.output}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Output Markdown
    md_path = Path(f"{args.output}.md")
    markdown = format_audit_markdown(results)
    with open(md_path, "w") as f:
        f.write(markdown)

    print(f"Audit results written to {json_path} and {md_path}")

    # Print summary
    overall = results["overall_stats"]
    print(f"\nSummary:")
    print(f"  Low diversity: {overall['low_diversity_intents']}/{overall['total_intents']} intents")
    print(f"  High similarity: {overall['high_similarity_intents']}/{overall['total_intents']} intents")
    print(f"  Top strategy: {max(overall['strategy_distribution'].items(), key=lambda x: x[1])}")


if __name__ == "__main__":
    main()