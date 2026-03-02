# Comparative Research Evaluation Report (Open Source)
Generated on: 2026-01-14 00:58:31
Model Regime: **Open Source**
Run Directory: `eval_results/comparative/20260113_215647_open/`

## Summary Metrics
| Metric | Baseline (Strict) | Experimental (Custom) | Delta |
| :--- | :--- | :--- | :--- |
| Pass Rate | 100.0% | 80.0% | -20.0% |
| Avg Clarity | 4.80/5 | 4.00/5 | -0.80 |
| Avg Citation | 2.60/5 | 2.60/5 | +0.00 |
| Avg Reasoning | 4.20/5 | 4.00/5 | -0.20 |
| Total Cost | $0.3640 | $0.6889 | +89.3% |

## Per-Question Breakdown
*Notation: (C: Clarity, R: Reasoning, T: Citation)*
| Question | Baseline | Experimental | Result |
| :--- | :---: | :---: | :--- |
| Evaluate the 'Zustand' state management library for adoption, strictly comparing its patterns against the 'Google Engineering Practices' knowledge base regarding code complexity and readability. Use external search for Zustand and internal KB for standards. | ✅ (C:5, R:4, T:3) | ✅ (C:4, R:4, T:3) | Cost delta: $-0.0164 |
| Conduct a performance and developer experience comparison of Node.js vs Deno vs Bun for building high-concurrency WebSocket servers in 2025. Focus on benchmarks, ecosystem maturity, and compatibility. | ✅ (C:4, R:3, T:1) | ✅ (C:5, R:5, T:1) | Cost delta: $-0.0892 |
| Provide a deep technical explanation of how closures and lexical scope interact in JavaScript (referencing 'You Don't Know JS' KB) vs how Python handles closures (referencing 'late binding' issues). Highlight the practical pitfalls in both. | ✅ (C:5, R:5, T:4) | ✅ (C:5, R:5, T:4) | Cost delta: $+0.2048 |
| What is the consensus on 'React Server Components' (RSC) as of late 2024? Synthesize the primary criticisms from the community and the counter-arguments from the React team. | ✅ (C:5, R:4, T:2) | ✅ (C:5, R:5, T:4) | Cost delta: $+0.2163 |
| Design a migration strategy for a monolithic Django application to a Rust-based microservices architecture using Actix-web. Outline the risks, necessary team upskilling, and architectural changes required. | ✅ (C:5, R:5, T:3) | ❌ (C:1, R:1, T:1) | 🔴 Experimental Regressed |

## Analysis
- **Reliability Warning**: Custom roles introduced regressions.
- **Efficiency**: Experimental mode was 89.3% more expensive.

## Failure Analysis: Django Migration Regression

The Django migration question (experimental ❌, Clarity: 1) was a **compound failure** traced from `experimental/django_migration/trace.json`:

**Layer 1 — Supervisor routing lock-in** (primary cause): The supervisor (Llama 3.3 70B, strategic tier) dispatched `NEXT: migration_planner` for 11+ consecutive iterations after the agent had already produced a complete response. The custom role key `migration_planner` is outside Llama's trained vocabulary for standard agent names, so the model lacked reliable completion-detection priors for it. This consumed 22 of 25 iteration budget without advancing to `summarizer`.

**Layer 2 — Synthesis-tier hallucination**: When finally routed to `summarizer` (Gemini Flash), the model emitted fake Python-syntax code blocks — `print(search_hacker_news(...))` — with hallucinated JSON "output" beneath them. These are not valid tool calls; `_extract_markdown_tool_calls()` parses JSON blocks, not Python. No real tools ran. The summarizer finding was raw fake-code.

**Layer 3 — Budget exhaustion**: `task_completion = 0.0` (no `writer` finding, no `END` decision). The judge correctly scored the raw fake-code output as Clarity: 1.

**Implication**: The failure is not generic "too much flexibility." It is specifically the interaction between *custom role naming* and a *weaker strategic model*. A stronger supervisor (e.g., Claude Sonnet) may not exhibit the same routing lock-in — this is a testable hypothesis for future runs.
