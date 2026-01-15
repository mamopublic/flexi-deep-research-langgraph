# Evaluation Examples: LangGraph Research Agent

This directory contains representative examples from the flexi-deep-research-langgraph evaluation framework, demonstrating rigorous comparative analysis of agent architectures.

## Overview

The evaluation framework tests LangGraph-based research agents across three dimensions:
- **Clarity**: Coherence and structure of generated reports
- **Citation Quality**: Proper attribution and knowledge base integration  
- **Reasoning Depth**: Analytical rigor and synthesis quality

### Evaluation Modes

1. **Quick Evaluation**: Fast testing with 3 focused questions (~5 min)
2. **Comprehensive Evaluation**: In-depth analysis with 5 complex questions (~15 min)
3. **Comparative Evaluation**: Head-to-head architecture comparison

## Preliminary Finding: Well-Grounded Role Definitions Outperform Free-Form Selection

**Research Question**: Does a custom "free-form" agent architecture outperform structured role-based patterns?

**Hypothesis**: Greater agent autonomy in role selection would improve research quality and reduce costs.

**Result**: **Negative** - The experimental architecture showed:
- ❌ **20% lower pass rate** (80% vs 100%)
- ❌ **89% higher costs** ($0.69 vs $0.36)
- ❌ **One critical regression** (Django migration question)

**Significance**: This preliminary result (n=5) suggests that:
1. **Well-grounded role definitions** (Researcher, Analyst, Supervisor) - which are standard across deep research agents, not LangGraph-specific - provide better structure than free-form role selection
2. **Increased autonomy ≠ increased quality** - established roles act as guardrails against shortcuts
3. **Evaluation methodology works** - successfully detects performance regressions
4. **Further research needed** - larger datasets required to confirm this pattern holds across diverse research scenarios

## Example Structure

```
examples/
├── README.md                                    # This file
├── comparative_evaluation/                     # Architecture comparison
│   ├── comparison_report.md                    # Summary metrics and analysis
│   ├── baseline/                               # Strict architecture (default)
│   │   ├── summary.json                        # Aggregate statistics
│   │   └── zustand_evaluation/                 # Success case example
│   │       ├── report.md                       # Generated research report
│   │       └── trace.json                      # Full execution trace
│   └── experimental/                           # Custom architecture (experimental)
│       ├── summary.json                        # Aggregate statistics
│       └── django_migration/                   # Failure case (instructive!)
│           ├── report.md                       # Low-quality output
│           └── trace.json                      # Execution trace showing regression
└── quick_evaluation/                           # Rapid testing mode
    ├── summary.json                            # Quick eval statistics
    └── javascript_closures/                    # Example research output
        ├── report.md                           # Generated technical report
        └── trace.json                          # Execution observability
```

## Comparative Evaluation Deep Dive

### Baseline (Strict Architecture)
- **Pass Rate**: 100% (5/5 questions)
- **Average Clarity**: 4.80/5
- **Average Reasoning**: 4.20/5
- **Total Cost**: $0.36

**Architecture Characteristics:**
- Pre-defined role sequencing
- Mandatory knowledge base consultation
- Strict citation requirements
- Deterministic execution flow

### Experimental (Custom Architecture)  
- **Pass Rate**: 80% (4/5 questions)
- **Average Clarity**: 4.00/5
- **Average Reasoning**: 4.00/5
- **Total Cost**: $0.69 (+89%)

**Architecture Characteristics:**
- Free-form role selection
- Optional KB usage
- Flexible citation patterns
- Non-deterministic execution

### The Instructive Failure

**Question**: "Design a migration strategy for a monolithic Django application to a Rust-based microservices architecture..."

- **Baseline**: ✅ Comprehensive analysis (Clarity: 5, Reasoning: 5)
- **Experimental**: ❌ Superficial response (Clarity: 1, Reasoning: 1)

**Why This Matters**: The failure case reveals that **autonomy without guardrails** leads to shortcuts - the agent skipped deep analysis in favor of generic recommendations.

## Research Implications

### 1. Framework Design
**Finding**: Opinionated frameworks (like LangGraph's strict patterns) can outperform "flexible" alternatives.

**Application**: When building agentic systems, default to structured workflows unless specific use cases demand flexibility.

### 2. Evaluation Rigor
**Finding**: Small dataset (n=5) sufficient to detect major regressions.

**Application**: Rapid iteration possible with focused eval sets; scale up for edge case discovery.

### 3. Cost vs. Quality Tradeoff
**Finding**: Higher costs did NOT correlate with better output.

**Application**: Autonomy → more LLM calls → higher cost, but not necessarily better reasoning.

## Next Steps

Based on these findings, future work will:
1. **Expand evaluation dataset** (n=5 → n=20+) to investigate edge cases
2. **Analyze failure modes** - why did the experimental architecture regress?
3. **Hybrid architecture** - selective autonomy in specific workflow stages
4. **Cost optimization** - reduce baseline costs while maintaining quality

## File Format Reference

### `summary.json`
```json
{
  "total_questions": 5,
  "passed": 4,
  "failed": 1,
  "avg_clarity": 4.00,
  "avg_citation": 2.60,
  "avg_reasoning": 4.00,
  "total_cost": 0.6889
}
```

### `trace.json`
Complete LangGraph execution trace including:
- Node-by-node state transitions
- LLM calls with prompts and responses
- Knowledge base queries and results
- Tool invocations and outputs
- Token usage and cost breakdown

### `report.md`
The final research output generated by the agent, structured as:
- Executive summary
- Key findings
- Detailed analysis
- Citations and references

## Reproducing Evaluations

To run the comparative evaluation:

```bash
cd flexi-deep-research-langgraph

# Quick evaluation (3 questions, ~5 min)
python -m tests.eval.run_eval quick

# Comprehensive evaluation (5 questions, ~15 min)
python -m tests.eval.run_eval comprehensive

# Comparative evaluation (baseline vs experimental, ~30 min)
python -m tests.eval.run_comparative
```

Results will be saved to `eval_results/{mode}/{timestamp_model}/`.

## Key Takeaway

**Negative results are valuable results.** This evaluation demonstrates that the experimental architecture is *not* superior to the baseline - a finding that:

1. **Validates the evaluation methodology** (can detect regressions)
2. **Informs future architectural decisions** (default to structured patterns)
3. **Demonstrates scientific honesty** (reporting null results transparently)
4. **Guides resource allocation** (focus optimization on baseline, not experimental)

This is the hallmark of rigorous research engineering: letting data drive decisions, even when it contradicts initial hypotheses.

---

**Last Updated**: January 2026  
**Evaluation Framework Version**: 1.0  
**LangGraph Version**: 0.2.62
