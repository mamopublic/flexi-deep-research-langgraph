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
│           ├── report.md                       # Failure artifact (intentionally preserved)
│           └── trace.json                      # Execution trace — source of mechanistic post-mortem
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

### The Instructive Failure: Mechanistic Post-Mortem

**Question**: "Design a migration strategy for a monolithic Django application to a Rust-based microservices architecture..."

- **Baseline**: ✅ Comprehensive analysis (Clarity: 5, Reasoning: 5)
- **Experimental**: ❌ Raw hallucinated tool-code output (Clarity: 1, Reasoning: 1)

**What Actually Happened** (mined from `experimental/django_migration/trace.json`):

This was a **three-layer compound failure**, not a simple "too much autonomy" story:

1. **Supervisor routing lock-in (primary cause)**: After `migration_planner` (Qwen3-32b) produced a comprehensive answer on its first invocation, the supervisor (Llama 3.3 70B) kept emitting `NEXT: migration_planner` for **11+ consecutive iterations**. The model could not recognize the agent had completed its task, so it never advanced to `summarizer`. This consumed 22 of the 25 iteration budget.

2. **Synthesis-tier model hallucinated non-executable tool calls**: When finally routed to `summarizer` (Gemini Flash), the model emitted fake Python-syntax code blocks — `print(search_hacker_news("..."))` — with completely hallucinated "output" JSON beneath them. These are *not* real tool calls: `_extract_markdown_tool_calls()` only handles JSON blocks, not Python code syntax. No real tools ran. `findings["summarizer"]` = raw fake-code, which the judge correctly scored Clarity: 1.

3. **Iteration budget exhausted**: With 25/25 iterations consumed by the loop, `task_completion = 0.0` (neither `supervisor_decision == "END"` nor a `writer` finding existed). The preserved `report.md` in this directory is the raw hallucinated summarizer output — intentionally kept as a failure artifact.

**The root mechanism**: Custom role naming (`migration_planner`, `django_assessor`, `rust_architect`) broke the shared vocabulary between the supervisor LLM and the routing layer. With standard role names, the Llama supervisor has reliable, trained priors for "this agent is done → advance." With improvised keys, those priors break down, producing loop-lock. This is likely a general failure mode of routing through dynamically-named agents with a weaker strategic model.

**The preserved `report.md` in this directory** is the raw hallucinated summarizer output — kept as a concrete failure artifact, not a broken file.

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
1. **Expand evaluation dataset** (n=5 → n=20+) to investigate edge cases, particularly questions requiring multi-step reasoning where custom roles may behave differently
2. **Hybrid architecture** - selective autonomy in specific workflow stages (e.g., allow custom role naming only for the researcher tier where the supervisor vocabulary problem is less severe)
3. **Cost optimization** - reduce baseline costs while maintaining quality through smarter context pruning
4. **Investigate the routing lock-in failure mode** more rigorously: does it appear with stronger strategic models (Claude Sonnet), or is it specific to Llama 70B?

## Limitations & Current Evaluation Gaps

*These are known gaps, tracked for future improvement:*

### LLM-as-Judge Grounding
The current `ReportJudge` (`src/flexi/evals/judges.py`) evaluates reports against a 4-criterion rubric (clarity, citation, reasoning, hallucination) using a single LLM call with no external grounding. This means:
- **Citation scores are self-reported**: the judge cannot verify whether cited sources actually say what the report claims
- **Hallucination detection is model-dependent**: the judge uses the same class of model that generated the report

**Planned upgrade** (not yet implemented): An **LLM-as-judge with search tool access** — the judge would actively retrieve the cited URLs and verify factual claims against the actual content before scoring. This would anchor citation and hallucination scores to external evidence rather than model priors, and is a stronger eval design for any production deployment of a research agent.

### Metric Coverage
- `calculate_tool_efficiency` is currently a heuristic based on iteration count, not actual tool diversity. An agent that needed 4 high-quality, non-redundant searches would be penalized equally to one stuck in a redundant loop.
- No inter-rater reliability measurement for the judge (i.e., score variance across judge re-runs on the same report is not tracked).

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
