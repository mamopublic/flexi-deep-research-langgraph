# Flexi: Deep Research Agent System

A flexible, agentic deep research system built with LangGraph, supporting parallel research, hybrid knowledge base retrieval, and dynamic multi-agent orchestration.

## Architecture & Agents

The system uses a dynamic team of specialized agents, orchestrated by LangGraph. Among them:

- **The Architect**: The strategic planner. It analyzes the user query and designs a custom graph topology (e.g., "We need 3 parallel researchers for this comparison").
- **The Researchers**: Specialized data gatherers. Can search the external web (DuckDuckGo) or internal knowledge bases (ChromaDB) in parallel.
- **The Analyst**: The conflict resolver. Its system prompt instructs it to synthesize contradictory findings (e.g., "Source A vs Source B") into a coherent narrative.
- **The Supervisor**: The router. Manages the control flow, ensuring the research stays on track and terminates when complete.

## Evaluation Harness

A unified evaluation engine (`src/flexi/evals/runner.py`) ensures reliability across different configurations.

- **Unified Engine**: Single runner for both quick sanity checks and comprehensive stress tests.
- **Architectural Flexibility**: capable of testing "flexible" architectures (Architect designs the team) vs "rigid" ones (fixed graph).
- **Robustness**: Includes automatic tool validation (did it use the KB?) and resilient report extraction.

### Evaluation Examples

See **[examples/](examples/)** for a curated selection of evaluation results demonstrating:

- **Comparative analysis**: Baseline vs. Experimental architecture performance
- **Quality metrics**: Clarity, citation quality, and reasoning depth scores
- **Cost analysis**: Token usage and API cost breakdowns
- **Instructive failures**: Null results showing when flexibility underperforms structure

**Preliminary Finding**: The comparative evaluation revealed that the experimental "flexible" architecture underperformed the baseline (80% vs 100% pass rate, +89% cost). This suggests that **well-grounded default role definitions** (Researcher, Analyst, Supervisor) - which are standard across deep research agents - provide better structure than free-form role selection. Further investigation with larger datasets is needed to confirm this pattern across diverse research scenarios.

## Quick Start

### 1. Installation

```bash
uv pip install -e .
# Or with pip
pip install -e .
```

### 2. Environment Setup

Create a `.env` file:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```

(Optional) For local models:
```bash
USE_OPENSOURCE_MODELS=true
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Running Evaluations

**Quick Sanity Check (Tier 1)**:
```bash
python src/flexi/evals/quick_eval.py
```
*Runs 3 simple questions to verify system stability.*

**Comprehensive Stress Test (Tier 2)**:
```bash
python src/flexi/evals/comprehensive_eval.py
```
*Runs 5 complex scenarios (Parallelism, Hybrid Search, Conflict Resolution).*

**Comparative Study**:
```bash
python src/flexi/evals/run_comparison.py --suite [quick|comprehensive]
```
*Runs A/B tests between Baseline (Strict Roles) and Experimental (Flexible Roles) regimes, generating a detailed `comparison_report.md` with quality and cost deltas.*

## Rationale & Research Goals

This project serves as a testbed for investigating **flexible agentic architectures**.
1.  **Open vs. Default Roles**: Comparing the efficacy of "rigid" pre-defined agent roles against dynamically generated ones.
2.  **The Meta-Architect Pattern**: Introducing a strategic "Architect" layer that reasons about the *process* of research before execution begins.
3.  **General-Purpose Research**: Building a versatile deep research engine capable of tackling diverse domains (technical, policy, market analysis) without code changes.

## Technical Evolution

Key engineering turning points during development:

1.  **Open Source Model Integration**: Calibrating prompts and temperature to ensure smaller models (e.g., Llama 3) could reliably follow complex LangGraph protocols.
2.  **Context Hygiene**: Implementing strict "Episodic Memory" filtering to prevent token bloat and "Agent Amnesia" in long-running research loops.
3.  **Parallel Execution**: Moving from linear chains to dynamic `Map-Reduce` topologies using LangGraph's `Send` API to parallelize sub-topic research.
4.  **Resilient Search**: Implementing a "Poor Man's Fallback" router that degrades gracefully from high-quality APIs (Serper) to free alternatives (DuckDuckGo) based on availability.
5.  **Tool Unification**: Rounding out the system with a standardized Tool Registry that seamlessly integrates MCP servers (Weather) and Vector Stores (ChromaDB).

## Project Structure

- `src/flexi/agents/`: Core agent logic (Architect, Graph Builder).
- `src/flexi/evals/`: Unified evaluation engine (`runner.py`) and test sets.
- `src/flexi/core/`: Knowledge base (`chroma_client.py`) and Tool registry (`tools.py`).

---
*Built in collaboration with Google DeepMind's Antigravity.*
