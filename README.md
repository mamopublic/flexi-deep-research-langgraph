# Flexi Deep Research LangGraph

A flexible, agentic deep research system built with LangGraph.

## Overview
This system uses an "Architect" agent to dynamically design a team of research agents based on a user's query. It supports dynamic role creation, tool delegation, and multiple LLM providers (Anthropic, OpenRouter).

## Structure
- `src/`: Source code
  - `config/`: Configuration and prompts
  - `core/`: Core utilities (LLM, State, Tools)
  - `agents/`: Agent implementations
- `tests/`: Project tests
- `docs/`: Documentation
- `perplexity/`: Initial prototype (kept for reference)

## Development
1. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
2. Create `.env` file (see `.env.example`).
3. Run tests:
   ```bash
   pytest
   ```
